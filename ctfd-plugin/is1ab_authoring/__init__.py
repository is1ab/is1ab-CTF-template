"""is1ab_authoring — dev CTFd 出題外掛。

把一台**共用 dev CTFd** 變成出題開發中樞。CTFd 與 Flask web-interface 共用同一套
schema，匯出走同一個轉換器（scripts/ctfd_convert.py，容器內在 /repo/scripts）。

涵蓋（對照 docs/dev-ctfd-authoring-spec.md）：
- 合一出題表單：原生欄位（name/category/value/flag/tags/hints）+ 結構化詳細欄位（存成 blob YAML）
- @authed_only + 最小擁有權（owner/協作者）ACL
- Ⓓ：durable 亂碼 uid（綁定）+ 可讀 slug repo_path（目錄）
- Phase 4（Ⓐ）：【匯出 YAML】只**產** public.yml/private.yml 供出題者複製/下載到自己的 clone，
  plugin 不 push/commit
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from datetime import datetime

import yaml
from flask import (
    Blueprint,
    Response,
    abort,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

from CTFd.models import Challenges, Flags, Hints, Tags, Users, db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_user_page_menu_bar,
)
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin

# 分類 / 難度 / 狀態的受控詞彙（配額與指派共用，避免自由文字對帳誤差，見審查 B4）
CATEGORIES = ["web", "pwn", "reverse", "crypto", "forensic", "misc", "osint", "general"]
DIFFICULTIES = ["baby", "easy", "middle", "hard", "impossible"]
ASSIGN_STATUSES = ["unassigned", "assigned", "in_progress", "in_review", "done"]
# 題目「開發進度」的單一真相（Ⓑ）。與工單 status / CTFd state / ready_for_release 是不同概念。
DEV_STATUSES = ["planning", "developing", "testing", "completed", "deployed"]
STALE_DAYS = 7   # developing/testing 超過幾天沒動 → 視為停滯（該催）
# 進度顯示：dev_status → (中文標籤, bootstrap badge 色)
DEV_STATUS_LABEL = {
    "planning":   ("規劃",   "secondary"),
    "developing": ("出題中", "info"),
    "testing":    ("驗題中", "warning"),
    "completed":  ("完成",   "success"),
    "deployed":   ("已部署", "primary"),
}
# canonical（見 docs/challenge-schema.md）：交付方式 + 連線方式 + flag 三軸
DEPLOY_TYPES = ["", "attachment", "container", "none"]
CONNECTION_TYPES = ["", "nc", "http", "https"]
FLAG_LOADS = ["static", "dynamic"]
FLAG_SCOPES = ["shared", "per_team"]
FLAG_MATCHES = ["exact", "regex"]

# 富欄位改用結構化表單（不再手刻 YAML）。底層仍存成 blob YAML。
_META_TEXT = ["author"]                          # 單行（owners/assignee 砍：author 為單一來源）
_META_TEXTAREA = ["internal_notes"]              # 多行字串（flag_description/solution_steps 砍→writeup/）
_META_LINES = ["files"]                           # 一行一項→list（learning_*/references 砍→writeup/）
_META_BOOL = ["ready_for_release", "source_code_provided"]
# difficulty/deploy_type/flag_load/flag_scope=select；deploy_info{}、dynamic_flag{}、testing{}
# 特殊處理；其餘未知鍵→隱藏 passthrough 保留（含匯入舊題的 deploy_secrets/solution_steps 等）
_META_KNOWN = set(_META_TEXT + _META_TEXTAREA + _META_LINES + _META_BOOL + [
    "difficulty", "deploy_type", "flag_load", "flag_scope",
    "deploy_info", "dynamic_flag", "testing",
])
# 表單上的額外字串欄位（巢狀攤平的子欄位 + passthrough）
# deploy_secrets 不在此：密鑰不進表單/DB，屬 .env（若匯入題目有它，會落到 passthrough 保留）
_META_STR_EXTRA = ["deploy_connection", "deploy_port", "deploy_url",
                   "deploy_nc_port", "deploy_timeout", "deploy_memory", "deploy_cpu",
                   "dyn_template", "dyn_salt", "test_by", "test_status", "passthrough"]
_META_BOOL_ALL = _META_BOOL + ["deploy_requires_build"]
_META_STR_ALL = _META_TEXT + _META_TEXTAREA + _META_LINES + _META_STR_EXTRA

# dev 出題站用不到的導覽連結（比賽/參賽者相關）；用 CSS 藏掉，route 仍在但不出現在選單。
# 要藏更多就往這裡加 href（exact match，例如加 "/users"、"/admin/statistics"）。
NAV_HIDE = [
    "/admin/scoreboard", "/scoreboard",        # 計分板
    "/admin/submissions",                       # 參賽者提交紀錄
    "/admin/notifications", "/notifications",   # 廣播 / 參賽者通知
    "/users",                                   # 參賽者名單 → 改用 plugin 團隊頁
    "/admin/statistics",                        # 比賽統計（dev 站用不到）
]

PLUGIN_NAME = "is1ab_authoring"

# 重用 repo 的純函式轉換器（compose 把 repo 掛在 /repo）
_CONV_PATH = "/repo/scripts"
if _CONV_PATH not in sys.path:
    sys.path.insert(0, _CONV_PATH)
try:
    import ctfd_convert
except Exception:  # pragma: no cover - 沒掛 repo 時 plugin 仍能載入
    ctfd_convert = None


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

class ChallengeMetadata(db.Model):
    __tablename__ = "is1ab_challenge_metadata"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # F1
    collaborators = db.Column(db.Text, default="")       # Phase 6：可共同編輯的 user id（逗號分隔）
    dev_status = db.Column(db.String(32), default="developing")  # Ⓑ 開發進度單一真相 → public.yml.status
    dev_status_at = db.Column(db.DateTime, nullable=True)  # 最後異動時間（停滯偵測用）
    uid = db.Column(db.String(16), nullable=True)        # Ⓓ 隱形亂碼綁定鍵
    repo_path = db.Column(db.String(255), nullable=True)  # Ⓓ 可讀目錄 <cat>/<slug>
    blob = db.Column("metadata_yaml", db.Text, default="")

    def __init__(self, challenge_id, owner_id=None, uid=None, repo_path=None, blob="",
                 collaborators="", dev_status="developing"):
        self.challenge_id = challenge_id
        self.owner_id = owner_id
        self.collaborators = collaborators
        self.dev_status = dev_status
        self.dev_status_at = datetime.utcnow()
        self.uid = uid
        self.repo_path = repo_path
        self.blob = blob


# --------------------------------------------------------------------------- #
# PM 分配與指派 model（spec §9.6）
# --------------------------------------------------------------------------- #

class ChallengeQuota(db.Model):
    """各 category×difficulty 的目標題數。"""

    __tablename__ = "is1ab_quota"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(32), nullable=False)
    difficulty = db.Column(db.String(32), nullable=False)
    target = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint("category", "difficulty", name="uq_quota_cat_diff"),)


class Assignment(db.Model):
    """出題工單：PM 指派誰出什麼、誰驗；題目建立後回填 challenge_id。"""

    __tablename__ = "is1ab_assignment"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default="")
    category = db.Column(db.String(32), default="")
    difficulty = db.Column(db.String(32), default="")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_ids = db.Column(db.Text, default="")     # 逗號分隔的 user id
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=True)
    status = db.Column(db.String(32), default="unassigned")


class ChallengeComment(db.Model):
    """題目留言：任何登入者皆可留言（審題 / 討論 / 回饋）。"""

    __tablename__ = "is1ab_comment"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s or "challenge"


def _new_uid():
    return uuid.uuid4().hex[:8]


def _get_meta(challenge_id):
    return ChallengeMetadata.query.filter_by(challenge_id=challenge_id).first()


def _collaborator_ids(meta):
    return [x for x in (meta.collaborators or "").split(",") if x] if meta else []


def _can_edit(meta):
    """admin、owner、或 collaborator 可編輯。"""
    if is_admin():
        return True
    user = get_current_user()
    if not user or not meta:
        return False
    return meta.owner_id == user.id or str(user.id) in _collaborator_ids(meta)


def _can_manage_acl(meta):
    """只有 admin 或 owner 能改協作者清單（避免協作者互相提權）。"""
    if is_admin():
        return True
    user = get_current_user()
    return bool(user and meta and meta.owner_id == user.id)


def _sync_flag(challenge_id, content, flag_match):
    """建 CTFd flag。flag_match（exact/regex）或直接的 CTFd type 皆可：只有 regex→regex，其餘→static。"""
    ctfd_type = "regex" if str(flag_match).lower() == "regex" else "static"
    Flags.query.filter_by(challenge_id=challenge_id).delete()
    if content:
        db.session.add(Flags(challenge_id=challenge_id, type=ctfd_type, content=content))
    db.session.commit()


def _sync_tags(challenge_id, tags_csv):
    Tags.query.filter_by(challenge_id=challenge_id).delete()
    for value in [t.strip() for t in (tags_csv or "").split(",") if t.strip()]:
        db.session.add(Tags(challenge_id=challenge_id, value=value))
    db.session.commit()


def _sync_hints(challenge_id, hints_text):
    Hints.query.filter_by(challenge_id=challenge_id).delete()
    for line in (hints_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            cost_str, content = line.split("|", 1)
            try:
                cost = int(cost_str.strip())
            except ValueError:
                cost = 0
        else:
            cost, content = 0, line
        content = content.strip()
        if content:
            db.session.add(Hints(challenge_id=challenge_id, content=content, cost=cost))
    db.session.commit()


def _read_native(challenge_id):
    flag = Flags.query.filter_by(challenge_id=challenge_id).first()
    tags = Tags.query.filter_by(challenge_id=challenge_id).all()
    hints = Hints.query.filter_by(challenge_id=challenge_id).order_by(Hints.cost).all()
    return {
        "flag": flag.content if flag else "",
        # canonical flag_match：CTFd regex flag → regex，否則 exact
        "flag_match": "regex" if (flag and flag.type == "regex") else "exact",
        "tags": ", ".join(t.value for t in tags),
        "hints": "\n".join(f"{h.cost}|{h.content}" for h in hints),
    }


def _int_or(s):
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return str(s).strip()


def _blob_to_fields(blob_str):
    """把 blob YAML 拆成結構化表單欄位值（全欄位，無使用者可見 YAML）。"""
    try:
        d = yaml.safe_load(blob_str) or {}
    except yaml.YAMLError:
        d = {}
    if not isinstance(d, dict):
        d = {}
    mf = {}
    for k in _META_TEXT + _META_TEXTAREA:
        mf[k] = "" if d.get(k) is None else str(d.get(k))
    mf["difficulty"] = str(d.get("difficulty", "") or "")
    # deploy_type：新欄位優先，相容舊 challenge_type
    dt = str(d.get("deploy_type", "") or "")
    if not dt and d.get("challenge_type"):
        ct = str(d.get("challenge_type"))
        dt = "container" if ("container" in ct or ct == "nc_challenge") else "attachment"
    mf["deploy_type"] = dt
    # flag 三軸（load/scope 存 blob；match 由 CTFd flag 決定，見 _read_native）
    mf["flag_load"] = str(d.get("flag_load", "") or "static")
    mf["flag_scope"] = str(d.get("flag_scope", "") or "shared")
    for k in _META_BOOL:
        mf[k] = bool(d.get(k))
    for k in _META_LINES:
        v = d.get(k) or []
        if isinstance(v, list):
            mf[k] = "\n".join(
                str(x.get("description") or x) if isinstance(x, dict) else str(x)
                for x in v)
        else:
            mf[k] = str(v)
    # deploy_info（攤平；connection_type = nc/http/https）
    di = d.get("deploy_info") if isinstance(d.get("deploy_info"), dict) else {}
    res = di.get("resources") if isinstance(di.get("resources"), dict) else {}
    mf["deploy_connection"] = str(di.get("connection_type", "") or "")
    for fk, dk, src in [("deploy_port", "port", di), ("deploy_url", "url", di),
                        ("deploy_nc_port", "nc_port", di), ("deploy_timeout", "timeout", di),
                        ("deploy_memory", "memory", res), ("deploy_cpu", "cpu", res)]:
        mf[fk] = str(src.get(dk, "") or "")
    mf["deploy_requires_build"] = bool(di.get("requires_build"))
    # testing（攤平）
    tst = d.get("testing") if isinstance(d.get("testing"), dict) else {}
    mf["test_by"] = str(tst.get("tested_by", "") or "")
    mf["test_status"] = str(tst.get("test_status", "") or "")
    # dynamic_flag（攤平）
    dyn = d.get("dynamic_flag") if isinstance(d.get("dynamic_flag"), dict) else {}
    mf["dyn_template"] = str(dyn.get("template", "") or "")
    mf["dyn_salt"] = str(dyn.get("salt", "") or "")
    # 未覆蓋的鍵（deploy_secrets / test_cases / verified_solutions…）→ 隱藏保留
    passthrough = {k: v for k, v in d.items() if k not in _META_KNOWN}
    mf["passthrough"] = yaml.safe_dump(passthrough, allow_unicode=True) if passthrough else ""
    return mf


def _fields_to_blob(mf):
    """把結構化欄位值組回 blob YAML。回傳 (blob_str, None)。"""
    d = {}
    for k in _META_TEXT + _META_TEXTAREA:
        if mf.get(k):
            d[k] = mf[k]
    if mf.get("difficulty"):
        d["difficulty"] = mf["difficulty"]
    if mf.get("deploy_type"):
        d["deploy_type"] = mf["deploy_type"]
    # flag 三軸的 load/scope 存 blob（match 走 CTFd flag type）
    if mf.get("flag_load"):
        d["flag_load"] = mf["flag_load"]
    if mf.get("flag_scope"):
        d["flag_scope"] = mf["flag_scope"]
    for k in _META_BOOL:
        d[k] = bool(mf.get(k))
    for k in _META_LINES:
        items = [x.strip() for x in (mf.get(k) or "").splitlines() if x.strip()]
        if items:
            d[k] = items
    di = {}
    if mf.get("deploy_connection"):
        di["connection_type"] = mf["deploy_connection"]
    if mf.get("deploy_port"):
        di["port"] = _int_or(mf["deploy_port"])
    if mf.get("deploy_url"):
        di["url"] = mf["deploy_url"]
    if mf.get("deploy_requires_build"):
        di["requires_build"] = True
    if mf.get("deploy_nc_port"):
        di["nc_port"] = _int_or(mf["deploy_nc_port"])
    if mf.get("deploy_timeout"):
        di["timeout"] = _int_or(mf["deploy_timeout"])
    res = {}
    if mf.get("deploy_memory"):
        res["memory"] = mf["deploy_memory"]
    if mf.get("deploy_cpu"):
        res["cpu"] = mf["deploy_cpu"]
    if res:
        di["resources"] = res
    if di:
        d["deploy_info"] = di
    tst = {}
    if mf.get("test_by"):
        tst["tested_by"] = mf["test_by"]
    if mf.get("test_status"):
        tst["test_status"] = mf["test_status"]
    if tst:
        d["testing"] = tst
    if mf.get("dyn_template") or mf.get("dyn_salt"):
        d["dynamic_flag"] = {"template": mf.get("dyn_template", ""), "salt": mf.get("dyn_salt", "")}
    try:
        pt = yaml.safe_load(mf.get("passthrough") or "") or {}
    except yaml.YAMLError:
        pt = {}
    if isinstance(pt, dict):
        d.update(pt)
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True), None


def _build_export(challenge_id):
    """產出 (public_yaml, private_yaml, repo_path, error)。Ⓐ：只產檔、不碰 git。"""
    if ctfd_convert is None:
        return None, None, None, "轉換器未載入（/repo/scripts 未掛載？）"
    chal = Challenges.query.filter_by(id=challenge_id).first()
    meta = _get_meta(challenge_id)
    try:
        blob_data = yaml.safe_load(meta.blob) if (meta and meta.blob) else {}
        if not isinstance(blob_data, dict):
            blob_data = {}
    except yaml.YAMLError as e:
        return None, None, None, f"blob YAML 錯誤：{e}"

    challenge = {"name": chal.name, "category": chal.category,
                 "description": chal.description, "value": chal.value}
    flags = [{"content": f.content, "type": f.type}
             for f in Flags.query.filter_by(challenge_id=challenge_id)]
    hints = [{"content": h.content, "cost": h.cost}
             for h in Hints.query.filter_by(challenge_id=challenge_id).order_by(Hints.cost)]
    tags = [{"value": t.value} for t in Tags.query.filter_by(challenge_id=challenge_id)]

    public, private = ctfd_convert.ctfd_to_challenge(
        challenge, flags=flags, hints=hints, tags=tags, metadata=blob_data)

    uid = meta.uid if meta else ""
    public = {"id": uid, **public}  # durable 綁定鍵放最前面
    public["status"] = (meta.dev_status if meta else "developing")  # Ⓑ 單一真相 → status
    dump = lambda d: yaml.safe_dump(d, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)
    pub_yaml = dump(public)
    priv_yaml = dump(private) if private else ""
    repo_path = (meta.repo_path if meta else "") or f"{_slugify(chal.category)}/{_slugify(chal.name)}"
    return pub_yaml, priv_yaml, repo_path, None


def _challenge_difficulty(challenge_id):
    """從題目的 metadata blob 讀 difficulty（配額對帳用）。"""
    meta = _get_meta(challenge_id)
    if not meta or not meta.blob:
        return ""
    try:
        data = yaml.safe_load(meta.blob) or {}
    except yaml.YAMLError:
        return ""
    return str(data.get("difficulty", "")).strip() if isinstance(data, dict) else ""


def _quota_data():
    """回傳 {category: {difficulty: (target, actual)}}。"""
    targets = {(q.category, q.difficulty): q.target for q in ChallengeQuota.query.all()}
    actual = {}
    for c in Challenges.query.all():
        key = (c.category or "", _challenge_difficulty(c.id))
        actual[key] = actual.get(key, 0) + 1
    data = {}
    for cat in CATEGORIES:
        data[cat] = {d: (targets.get((cat, d), 0), actual.get((cat, d), 0)) for d in DIFFICULTIES}
    return data


def _users_map():
    return {u.id: u.name for u in Users.query.all()}


def _dashboard_matrix():
    """回傳 {category: {difficulty: {'slots': [...], 'target': N}}}。

    每格拆成 target 個 slot（配額幾題就幾個位）。每個 slot：
      - 已有題目 → 題目連結（+ 出題者小字）
      - 只有指派、還沒建題 → 出題者名稱（未建）
      - 都沒有（配額還沒補滿）→ 缺
    """
    targets = {(q.category, q.difficulty): q.target for q in ChallengeQuota.query.all()}
    umap = _users_map()
    chal_by_id = {c.id: c for c in Challenges.query.all()}
    metas = ChallengeMetadata.query.all()
    owner_by_cid = {m.challenge_id: m.owner_id for m in metas}
    status_by_cid = {m.challenge_id: m.dev_status for m in metas}

    def _blob_test(m):
        try:
            b = yaml.safe_load(m.blob) if m.blob else {}
            t = (b or {}).get("testing") if isinstance(b, dict) else {}
            return (t or {}).get("test_status") if isinstance(t, dict) else None
        except Exception:
            return None
    test_by_cid = {m.challenge_id: _blob_test(m) for m in metas}

    chal_cell = {cat: {d: [] for d in DIFFICULTIES} for cat in CATEGORIES}
    uncategorized = []   # C1：落在固定格外的題（自由填分類/空難度）→ 收容，不讓它從追蹤消失
    for c in Challenges.query.order_by(Challenges.id).all():
        cat, diff = (c.category or ""), _challenge_difficulty(c.id)
        if cat in chal_cell and diff in chal_cell[cat]:
            chal_cell[cat][diff].append(c)
        else:
            uncategorized.append({"cid": c.id, "cname": c.name,
                                  "category": cat or "（空）", "difficulty": diff or "（空）",
                                  "author": umap.get(owner_by_cid.get(c.id)),
                                  "status": status_by_cid.get(c.id)})

    asg_cell = {cat: {d: [] for d in DIFFICULTIES} for cat in CATEGORIES}
    for a in Assignment.query.all():
        if a.category in asg_cell and a.difficulty in asg_cell[a.category]:
            asg_cell[a.category][a.difficulty].append(a)

    data = {}
    for cat in CATEGORIES:
        data[cat] = {}
        for d in DIFFICULTIES:
            target = targets.get((cat, d), 0)
            slots, linked = [], set()
            for a in asg_cell[cat][d]:                      # 先放指派（出題者 + 驗題者）
                chal = chal_by_id.get(a.challenge_id) if a.challenge_id else None
                if chal is None and a.author_id:            # 自動關聯：同格、同出題者、未被關聯的題 → 消除幽靈格
                    chal = next((c for c in chal_cell[cat][d]
                                 if c.id not in linked and owner_by_cid.get(c.id) == a.author_id), None)
                if chal:
                    linked.add(chal.id)
                # 出題者：優先指派者，其次題目擁有者
                author = umap.get(a.author_id) or (umap.get(owner_by_cid.get(chal.id)) if chal else None)
                slots.append({"author": author, "author_id": a.author_id,
                              "reviewers": [umap.get(int(x)) for x in (a.reviewer_ids or "").split(",") if x],
                              "cid": chal.id if chal else None,
                              "cname": chal.name if chal else None,
                              "status": status_by_cid.get(chal.id) if chal else None,
                              "review": test_by_cid.get(chal.id) if chal else None})
            for c in chal_cell[cat][d]:                     # 再放沒對應指派的題（顯示擁有者 + 進度）
                if c.id not in linked:
                    slots.append({"author": umap.get(owner_by_cid.get(c.id)), "author_id": None,
                                  "reviewers": [], "cid": c.id, "cname": c.name,
                                  "status": status_by_cid.get(c.id),
                                  "review": test_by_cid.get(c.id)})
            while len(slots) < target:                      # 補滿到配額數 → 缺
                slots.append({"author": None, "author_id": None, "reviewers": [],
                              "cid": None, "cname": None, "status": None})
            data[cat][d] = {"slots": slots, "target": target}

    # KPI 彙總（E1）：跨格加總，讓 PM 一眼看「還差多少、完成幾成」
    built = completed = missing = 0
    for cat in CATEGORIES:
        for d in DIFFICULTIES:
            cell = data[cat][d]
            cell_built = sum(1 for s in cell["slots"] if s["cid"])
            built += cell_built
            completed += sum(1 for s in cell["slots"]
                             if s["status"] in ("completed", "deployed"))
            missing += max(0, cell["target"] - cell_built)
    # 停滯偵測（E2）：developing/testing 超過 STALE_DAYS 天沒動 → 該催了
    now = datetime.utcnow()
    stalled = []
    for m in metas:
        if m.dev_status in ("developing", "testing") and m.dev_status_at:
            age = (now - m.dev_status_at).days
            if age >= STALE_DAYS:
                ch = chal_by_id.get(m.challenge_id)
                if ch:
                    stalled.append({"cid": ch.id, "cname": ch.name, "days": age,
                                    "author": umap.get(m.owner_id), "status": m.dev_status})
    stalled.sort(key=lambda x: -x["days"])

    total_target = sum(targets.values())
    denom = max(total_target, built)   # 配額未設滿時，用已建題數當分母，避免完成率爆表
    summary = {"target": total_target, "built": built, "completed": completed,
               "missing": missing, "uncat": len(uncategorized), "stalled": len(stalled),
               "rate": (round(completed * 100 / denom) if denom else 0)}
    return {"grid": data, "summary": summary, "uncategorized": uncategorized, "stalled": stalled}


def _open_prs():
    """在途 PR（gh api）。需 env GITHUB_REPO(owner/repo) + GITHUB_TOKEN；否則優雅降級。"""
    repo = os.environ.get("GITHUB_REPO", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        return None, "未設定 GITHUB_REPO / GITHUB_TOKEN（設定後這裡會顯示尚未 merge 的在途 PR）"
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=50"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "is1ab-authoring",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        prs = [{"number": p["number"], "title": p["title"],
                "user": (p.get("user") or {}).get("login", "?"),
                "branch": (p.get("head") or {}).get("ref", "?"),
                "url": p["html_url"]} for p in data]
        return prs, None
    except Exception as e:  # pragma: no cover - 依賴外部 GitHub
        return None, f"取 PR 失敗：{e}"


def _team_overview():
    """每個 user 的負載：出的題 / 協作 / 被指派出題 / 被指派驗題。取代參賽者 /users。"""
    chal_names = {c.id: c.name for c in Challenges.query.all()}
    metas = ChallengeMetadata.query.all()
    assignments = Assignment.query.all()
    rows = []
    for u in Users.query.all():
        owned = [chal_names.get(m.challenge_id) for m in metas if m.owner_id == u.id]
        collab = [chal_names.get(m.challenge_id) for m in metas if str(u.id) in _collaborator_ids(m)]
        rows.append({
            "user": u,
            "owned": [n for n in owned if n],
            "collab": [n for n in collab if n],
            "as_author": [a for a in assignments if a.author_id == u.id],
            "as_review": [a for a in assignments if str(u.id) in (a.reviewer_ids or "").split(",")],
        })
    return rows


def _my_stuff(user_id):
    """回傳 (我的題目 unified, 指派給我驗題)。

    unified 把「我出/協作的題」與「指派我出但還沒建的題」合成一張表：
      - 已建：題名 + 分類/難度/進度 + 角色（出題/協作）
      - 指派待出：題目留空，只有分類/難度（方便閱讀）
    """
    mine, owned_catdiff = [], set()
    for m in ChallengeMetadata.query.all():
        if m.owner_id == user_id or str(user_id) in _collaborator_ids(m):
            chal = Challenges.query.filter_by(id=m.challenge_id).first()
            if chal:
                diff = _challenge_difficulty(chal.id)
                is_owner = (m.owner_id == user_id)
                mine.append({"id": chal.id, "name": chal.name,
                             "category": chal.category, "difficulty": diff,
                             "dev_status": m.dev_status,
                             "role": ("出題" if is_owner else "協作"), "built": True})
                if is_owner:
                    owned_catdiff.add((chal.category, diff))
    # 指派我出、還沒建題、且我在該 分類×難度 還沒有題 → 併進來（題目留空）
    for a in Assignment.query.filter_by(author_id=user_id).all():
        if a.challenge_id or (a.category, a.difficulty) in owned_catdiff:
            continue
        mine.append({"id": None, "name": None, "category": a.category,
                     "difficulty": a.difficulty, "dev_status": None,
                     "role": "指派待出", "built": False})
    to_review = [a for a in Assignment.query.all()
                 if str(user_id) in (a.reviewer_ids or "").split(",")]
    return mine, to_review


# --------------------------------------------------------------------------- #
# Views（@authed_only + 擁有權）
# --------------------------------------------------------------------------- #

bp = Blueprint(PLUGIN_NAME, __name__)

_LIST_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div>
  <h1>is1ab 出題</h1>
  <a class="btn btn-success" href="{{ url_for('is1ab_authoring.challenge_new') }}">＋ 新增題目</a>
  <a class="btn btn-outline-secondary" href="{{ url_for('is1ab_authoring.challenge_import') }}">匯入 YAML</a>
</div></div>
<div class="container">
  <table class="table table-striped">
    <thead><tr><th>ID</th><th>題目</th><th>分類</th><th>難度</th><th>分數</th><th>進度</th><th>出題者</th><th>驗題者</th><th></th></tr></thead>
    <tbody>
    {% for c in rows %}
      <tr>
        <td>{{ c.id }}</td><td>{{ c.name }}</td><td>{{ c.category }}</td><td>{{ c.difficulty }}</td>
        <td>{{ c.value }}</td>
        <td>{% if c.dev_status %}<span class="badge badge-{{ (status_label.get(c.dev_status) or ['','secondary'])[1] }}">{{ (status_label.get(c.dev_status) or [c.dev_status])[0] }}</span>{% else %}<span class="badge badge-light">未填</span>{% endif %}</td>
        <td>{{ c.author or '—' }}</td>
        <td>{% if c.reviewers %}{{ c.reviewers|join(', ') }}{% else %}<span class="text-muted">—</span>{% endif %}</td>
        <td>
          <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=c.id) }}">查看</a>
          {% if c.can_edit %}<a class="btn btn-sm btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=c.id) }}">編輯</a>
          <a class="btn btn-sm btn-outline-info" href="{{ url_for('is1ab_authoring.challenge_export', challenge_id=c.id) }}">匯出</a>{% endif %}
        </td>
      </tr>
    {% else %}
      <tr><td colspan="9" class="text-center text-muted">還沒有題目。點右上「新增題目」。</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

_FORM_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div>
  <h1>{{ "編輯題目" if challenge else "新增題目" }}</h1>
  {% if challenge %}<p class="text-muted">#{{ challenge.id }}
    <a class="btn btn-sm btn-outline-primary ml-2" href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=challenge.id) }}">檢視 / 部署測試 →</a></p>{% endif %}
</div></div>
<div class="container">
  {% if created %}<div class="alert alert-success">
    <strong>✅ 題目已建立！</strong> 接下來：
    <ol class="mb-0 mt-1">
      <li>到「<a href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=challenge.id) }}">檢視 / 部署測試</a>」頁上傳 docker 檔 → 一鍵建立實例試玩、確認 flag</li>
      <li>寫好 code 後，在題目頁「匯出」public/private.yml 到你的 clone</li>
      <li>本機 <code>make verify-solution</code> 綠燈 → commit + PR</li>
    </ol></div>{% endif %}
  {% if saved %}<div class="alert alert-success">已儲存。</div>{% endif %}
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <h4>原生欄位（CTFd）</h4>
    <div class="form-row">
      <div class="form-group col-md-8"><label>題名 *</label>
        <input class="form-control" name="name" value="{{ f.name }}" required></div>
      <div class="form-group col-md-4"><label>分類 <small class="text-muted">建議用既有分類，否則不進儀表板配額格</small></label>
        <input class="form-control" name="category" value="{{ f.category }}" list="cat_list" placeholder="web / pwn / crypto …">
        <datalist id="cat_list">{% for c in categories %}<option value="{{ c }}">{% endfor %}</datalist></div>
    </div>
    <div class="form-row">
      <div class="form-group col-md-3"><label>分數</label>
        <input class="form-control" type="number" name="value" value="{{ f.value }}"></div>
      <div class="form-group col-md-4"><label>開發進度</label>
        <select class="form-control" name="dev_status">
          {% for s in dev_statuses %}<option value="{{ s }}" {{ 'selected' if f.dev_status==s else '' }}>{{ (status_label.get(s) or [s])[0] }}</option>{% endfor %}
        </select></div>
      <div class="form-group col-md-5"><label>Tags（逗號分隔）</label>
        <input class="form-control" name="tags" value="{{ f.tags }}"></div>
    </div>
    <div class="form-group"><label>描述</label>
      <textarea class="form-control" name="description" rows="3">{{ f.description }}</textarea></div>
    <div class="form-row">
      <div class="form-group col-md-6"><label>Flag <small class="text-muted">格式 {{ flag_prefix }}{...}</small></label>
        <input class="form-control" name="flag" value="{{ f.flag }}" placeholder="{{ flag_prefix }}{...}"></div>
      <div class="form-group col-md-2"><label>載入 <small class="text-muted">load</small></label>
        <select class="form-control" name="flag_load">
          {% for s in flag_loads %}<option value="{{ s }}" {{ 'selected' if f.flag_load==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label>範圍 <small class="text-muted">scope</small></label>
        <select class="form-control" name="flag_scope">
          {% for s in flag_scopes %}<option value="{{ s }}" {{ 'selected' if f.flag_scope==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label>比對 <small class="text-muted">match</small></label>
        <select class="form-control" name="flag_match">
          {% for s in flag_matches %}<option value="{{ s }}" {{ 'selected' if f.flag_match==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
    </div>
    <small class="form-text text-muted mb-2">static/shared=經典內建統一 · dynamic=部署注入 · per_team=每隊唯一（隱含 dynamic） · regex=樣式比對</small>
    <div class="form-group"><label>Hints（每行 <code>cost|內容</code>）</label>
      <textarea class="form-control" name="hints" rows="3" style="font-family:monospace">{{ f.hints }}</textarea></div>

    <h4 class="mt-4">詳細資訊 <small class="text-muted">（存匯出時，公開與敏感欄位由系統自動分流）</small></h4>
    <div class="form-row">
      <div class="form-group col-md-3"><label>難度</label>
        <select class="form-control" name="difficulty"><option value="">—</option>
          {% for s in difficulties %}<option value="{{ s }}" {{ 'selected' if f.difficulty==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-3"><label>交付方式</label>
        <select class="form-control" name="deploy_type">
          {% for t in deploy_types %}<option value="{{ t }}" {{ 'selected' if f.deploy_type==t else '' }}>{{ t or '—' }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label>連線 <small class="text-muted">container</small></label>
        <select class="form-control" name="deploy_connection">
          {% for t in connection_types %}<option value="{{ t }}" {{ 'selected' if f.deploy_connection==t else '' }}>{{ t or '—' }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-4"><label>出題者</label>
        <input class="form-control" name="author" value="{{ f.author }}"></div>
    </div>
    <details class="mb-3">
      <summary class="text-muted">更多欄位（選填，大多題不用填：發布旗標 / 附件 / 部署參數）</summary>
      <div class="mt-2 mb-2">
        <span class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="ready_for_release" id="rfr" {{ 'checked' if f.ready_for_release else '' }}><label class="form-check-label" for="rfr">可發布</label></span>
        <span class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="source_code_provided" id="scp" {{ 'checked' if f.source_code_provided else '' }}><label class="form-check-label" for="scp">提供原始碼</label></span>
      </div>
      <div class="form-group"><label>附件 files（一行一個）</label><textarea class="form-control" name="files" rows="2">{{ f.files }}</textarea></div>
      <h6 class="text-muted">部署資訊 deploy_info（container 題；port/nc_port 供 verify-solution 使用）</h6>
      <div class="form-row">
        <div class="form-group col-md-2"><label>port</label><input class="form-control" name="deploy_port" value="{{ f.deploy_port }}"></div>
        <div class="form-group col-md-4"><label>url</label><input class="form-control" name="deploy_url" value="{{ f.deploy_url }}"></div>
        <div class="form-group col-md-2"><label>nc_port</label><input class="form-control" name="deploy_nc_port" value="{{ f.deploy_nc_port }}"></div>
        <div class="form-group col-md-2"><label>memory</label><input class="form-control" name="deploy_memory" value="{{ f.deploy_memory }}"></div>
        <div class="form-group col-md-2"><label>cpu</label><input class="form-control" name="deploy_cpu" value="{{ f.deploy_cpu }}"></div>
      </div>
      <div class="form-check mb-2"><input class="form-check-input" type="checkbox" name="deploy_requires_build" id="drb" {{ 'checked' if f.deploy_requires_build else '' }}><label class="form-check-label" for="drb">requires_build</label></div>
    </details>

    <div class="form-group"><label>內部筆記 <small class="text-muted">（官方解 / 學習資訊 / 測試帳密請寫 writeup/README.md，不進此表單）</small></label>
      <textarea class="form-control" name="internal_notes" rows="3">{{ f.internal_notes }}</textarea></div>
    <details class="mb-3">
      <summary class="text-muted">更多（動態 flag / 驗題記錄）</summary>
      <div class="form-row mt-2">
        <div class="form-group col-md-6"><label>dynamic_flag template</label><input class="form-control" name="dyn_template" value="{{ f.dyn_template }}"></div>
        <div class="form-group col-md-6"><label>dynamic_flag salt</label><input class="form-control" name="dyn_salt" value="{{ f.dyn_salt }}"></div>
      </div>
      <div class="form-row">
        <div class="form-group col-md-6"><label>tested_by</label><input class="form-control" name="test_by" value="{{ f.test_by }}"></div>
        <div class="form-group col-md-6"><label>test_status</label><input class="form-control" name="test_status" value="{{ f.test_status }}"></div>
      </div>
    </details>
    <input type="hidden" name="passthrough" value="{{ f.passthrough }}">

    {% if challenge %}
    <h4 class="mt-4">權限</h4>
    <p class="text-muted">擁有者：{{ owner_name or '（未設）' }}</p>
    <div class="form-group"><label>協作者（可共同編輯）</label>
      <select class="form-control" name="collaborators" multiple {{ 'disabled' if not can_manage else '' }}>
        {% for u in users %}<option value="{{ u.id }}" {{ 'selected' if (u.id|string) in f.collaborators else '' }}>{{ u.name }}</option>{% endfor %}
      </select>
      {% if not can_manage %}<small class="form-text text-muted">只有擁有者 / admin 能改協作者。</small>{% endif %}
    </div>
    {% endif %}

    <button class="btn btn-primary" type="submit">儲存</button>
    {% if challenge %}<a class="btn btn-outline-info" href="{{ url_for('is1ab_authoring.challenge_export', challenge_id=challenge.id) }}">匯出 YAML</a>{% endif %}
    <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回清單</a>
  </form>
</div>
{% endblock %}
"""

_EXPORT_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div>
  <h1>匯出：{{ challenge.name }}</h1>
  <p class="text-muted">複製到你自己 clone 的 <code>challenges/{{ repo_path }}/</code>，連同 code 一起 commit / PR。</p>
</div></div>
<div class="container">
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% else %}
  <div class="row">
    <div class="col-md-6">
      <h5>public.yml <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('is1ab_authoring.challenge_export_file', challenge_id=challenge.id, which='public') }}">下載</a></h5>
      <pre style="max-height:60vh;overflow:auto;background:#f6f8fa;padding:1em">{{ public_yaml }}</pre>
    </div>
    <div class="col-md-6">
      <h5>private.yml <span class="badge badge-danger">敏感</span> <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('is1ab_authoring.challenge_export_file', challenge_id=challenge.id, which='private') }}">下載</a></h5>
      <pre style="max-height:60vh;overflow:auto;background:#fff5f5;padding:1em">{{ private_yaml }}</pre>
    </div>
  </div>
  <h5 class="mt-4">本機部署測試 / 驗 exploit</h5>
  <p class="text-muted">code 在你自己的 clone。把上面的 YAML 放進 <code>challenges/{{ repo_path }}/</code>、
  寫好 <code>docker/</code> 與 <code>solution/exploit.py</code> 後，在 repo 根目錄跑：</p>
  <pre style="background:#f6f8fa;padding:1em"># 起服務自己試玩
cd challenges/{{ repo_path }}/docker && docker compose up -d

# 一鍵：起服務 → 跑官方解 → 比對 flag（含 flag drift 偵測）
make verify-solution ARGS="challenges/{{ repo_path }}"</pre>
  {% endif %}
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回清單</a>
</div>
{% endblock %}
"""


def _form_defaults():
    f = {"name": "", "category": "", "value": 100, "dev_status": "developing",
         "description": "", "flag": "", "tags": "", "hints": "", "difficulty": "",
         "deploy_type": "", "deploy_connection": "",
         "flag_load": "static", "flag_scope": "shared", "flag_match": "exact"}
    for k in _META_STR_ALL:
        f[k] = ""
    for k in _META_BOOL_ALL:
        f[k] = False
    return f


def _form_from_request():
    g = request.form.get
    f = {
        "name": g("name", "").strip(), "category": g("category", "").strip().lower(),
        "value": g("value", "100").strip() or "100", "dev_status": g("dev_status", "developing"),
        "description": g("description", ""), "flag": g("flag", "").strip(),
        "flag_load": g("flag_load", "static"), "flag_scope": g("flag_scope", "shared"),
        "flag_match": g("flag_match", "exact"),
        "tags": g("tags", ""), "hints": g("hints", ""),
        "difficulty": g("difficulty", ""), "deploy_type": g("deploy_type", ""),
    }
    for k in _META_STR_ALL:
        f[k] = g(k, "")
    for k in _META_BOOL_ALL:
        f[k] = g(k) == "on"
    return f


def _assignment_for(challenge_id):
    """找這題對應的工單：先 challenge_id 直連，否則以 出題者×分類×難度 關聯 PM 的工單（challenge_id=None）。"""
    a = Assignment.query.filter_by(challenge_id=challenge_id).first()
    if a:
        return a
    meta = _get_meta(challenge_id)
    chal = Challenges.query.filter_by(id=challenge_id).first()
    if meta and meta.owner_id and chal:
        return Assignment.query.filter_by(
            author_id=meta.owner_id, category=chal.category,
            difficulty=_challenge_difficulty(challenge_id), challenge_id=None).first()
    return None


def _reviewers_by_cid(metas_by_cid, umap):
    """把每張工單的驗題者對應到題目 id（工單有 challenge_id 用它，否則以 出題者×分類×難度 自動關聯）。"""
    by_owner_catdiff = {}
    for c in Challenges.query.all():
        m = metas_by_cid.get(c.id)
        if m:
            by_owner_catdiff[(m.owner_id, c.category, _challenge_difficulty(c.id))] = c.id
    result = {}
    for a in Assignment.query.all():
        cid = a.challenge_id or (by_owner_catdiff.get((a.author_id, a.category, a.difficulty)) if a.author_id else None)
        if not cid:
            continue
        for x in (a.reviewer_ids or "").split(","):
            name = umap.get(int(x)) if x.strip().isdigit() else None
            if name:
                result.setdefault(cid, []).append(name)
    return result


@bp.route("/is1ab", methods=["GET"])
@authed_only
def challenge_list():
    metas = {m.challenge_id: m for m in ChallengeMetadata.query.all()}
    umap = _users_map()
    reviewers = _reviewers_by_cid(metas, umap)
    rows = []
    for c in Challenges.query.order_by(Challenges.id).all():
        meta = metas.get(c.id)
        rows.append(type("Row", (), {
            "id": c.id, "name": c.name, "category": c.category,
            "difficulty": _challenge_difficulty(c.id), "value": c.value,
            "dev_status": (meta.dev_status if meta else None),
            "author": (umap.get(meta.owner_id) if meta else None),
            "reviewers": reviewers.get(c.id, []),
            "has_meta": meta is not None,
            "can_edit": _can_edit(meta),  # meta None → 僅 admin（不再對所有人開放）
        }))
    return render_template_string(_LIST_TMPL, rows=rows, status_label=DEV_STATUS_LABEL)


@bp.route("/is1ab/new", methods=["GET", "POST"])
@authed_only
def challenge_new():
    if request.method == "POST":
        f = _form_from_request()
        blob, error = _fields_to_blob(f)
        if not f["name"]:
            error = "題名必填"
        if error:
            return render_template_string(_FORM_TMPL, challenge=None, f=f,
                                          nonce=session.get("nonce", ""), error=error, saved=False,
                                          dev_statuses=DEV_STATUSES, difficulties=DIFFICULTIES,
                                  categories=CATEGORIES,
                                  status_label=DEV_STATUS_LABEL, flag_prefix=_flag_prefix(),
                                          deploy_types=DEPLOY_TYPES, connection_types=CONNECTION_TYPES,
                                  flag_loads=FLAG_LOADS, flag_scopes=FLAG_SCOPES, flag_matches=FLAG_MATCHES)
        chal = Challenges(name=f["name"], description=f["description"],
                          value=int(f["value"] or 0), category=f["category"],
                          state="visible", type="standard")  # dev 站預設可見 → 直接上 /challenges 試玩
        db.session.add(chal)
        db.session.commit()
        owner = get_current_user()
        repo_path = f"{_slugify(f['category'])}/{_slugify(f['name'])}"
        db.session.add(ChallengeMetadata(
            challenge_id=chal.id, owner_id=(owner.id if owner else None),
            uid=_new_uid(), repo_path=repo_path, blob=blob, dev_status=f["dev_status"]))
        db.session.commit()
        _sync_flag(chal.id, f["flag"], f["flag_match"])
        _sync_tags(chal.id, f["tags"])
        _sync_hints(chal.id, f["hints"])
        return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=chal.id, created=1))
    f = _form_defaults()
    if request.args.get("category"):
        f["category"] = request.args.get("category").strip()
    if request.args.get("difficulty"):
        f["difficulty"] = request.args.get("difficulty").strip()
    return render_template_string(_FORM_TMPL, challenge=None, f=f,
                                  nonce=session.get("nonce", ""), error=None, saved=False,
                                  dev_statuses=DEV_STATUSES, difficulties=DIFFICULTIES,
                                  categories=CATEGORIES,
                                  status_label=DEV_STATUS_LABEL, flag_prefix=_flag_prefix(),
                                  deploy_types=DEPLOY_TYPES, connection_types=CONNECTION_TYPES,
                                  flag_loads=FLAG_LOADS, flag_scopes=FLAG_SCOPES, flag_matches=FLAG_MATCHES)


@bp.route("/is1ab/challenges/<int:challenge_id>/edit", methods=["GET", "POST"])
@authed_only
def challenge_edit(challenge_id):
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = _get_meta(challenge_id)
    # meta 為 None（無擁有者的異常題）時 _can_edit 只放行 admin，避免任何登入者可編
    if not _can_edit(meta):
        abort(403)

    saved = False
    error = None
    if request.method == "POST":
        f = _form_from_request()
        blob, error = _fields_to_blob(f)
        if not f["name"]:
            error = "題名必填"
        if error is None:
            chal.name = f["name"] or chal.name
            chal.category = f["category"]
            chal.description = f["description"]
            chal.value = int(f["value"] or 0)
            db.session.commit()  # state 不在表單上動（dev 站維持 visible）
            if meta is None:
                owner = get_current_user()
                meta = ChallengeMetadata(
                    challenge_id=challenge_id, owner_id=(owner.id if owner else None),
                    uid=_new_uid(),
                    repo_path=f"{_slugify(f['category'])}/{_slugify(f['name'])}",
                    blob=blob)
                db.session.add(meta)
            else:
                meta.blob = blob  # uid / repo_path 不可變（Ⓓ）
            meta.dev_status = f["dev_status"]  # Ⓑ 單一真相
            meta.dev_status_at = datetime.utcnow()  # 記最後異動 → 停滯偵測
            db.session.commit()
            # 只有 owner/admin 能改協作者清單（不信任表單，後端再判一次）
            if _can_manage_acl(meta):
                meta.collaborators = ",".join(request.form.getlist("collaborators"))
                db.session.commit()
            _sync_flag(challenge_id, f["flag"], f["flag_match"])
            _sync_tags(challenge_id, f["tags"])
            _sync_hints(challenge_id, f["hints"])
            saved = True

    meta = _get_meta(challenge_id)
    if request.method == "POST" and error:
        f = _form_from_request()
    else:
        native = _read_native(challenge_id)
        f = {
            "name": chal.name or "", "category": chal.category or "",
            "value": chal.value or 0,
            "dev_status": (meta.dev_status if meta else "developing"),
            "description": chal.description or "",
            "flag": native["flag"], "flag_match": native["flag_match"],
            "tags": native["tags"], "hints": native["hints"],
        }
        # flag_load/flag_scope 由 blob 補（_blob_to_fields 會設）
        f.update(_blob_to_fields(meta.blob if meta else ""))
    f["collaborators"] = _collaborator_ids(meta)
    owner = Users.query.filter_by(id=meta.owner_id).first() if (meta and meta.owner_id) else None
    return render_template_string(_FORM_TMPL, challenge=chal, f=f,
                                  nonce=session.get("nonce", ""), error=error, saved=saved,
                                  created=request.args.get("created"),
                                  dev_statuses=DEV_STATUSES, difficulties=DIFFICULTIES,
                                  categories=CATEGORIES,
                                  status_label=DEV_STATUS_LABEL, flag_prefix=_flag_prefix(),
                                  deploy_types=DEPLOY_TYPES, connection_types=CONNECTION_TYPES,
                                  flag_loads=FLAG_LOADS, flag_scopes=FLAG_SCOPES, flag_matches=FLAG_MATCHES,
                                  users=Users.query.all(), can_manage=_can_manage_acl(meta),
                                  owner_name=(owner.name if owner else None))


@bp.route("/is1ab/challenges/<int:challenge_id>/export", methods=["GET"])
@authed_only
def challenge_export(challenge_id):
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    # 匯出含 private.yml（flag/官方解/內部筆記）→ 必須通過與編輯相同的 ACL
    if not _can_edit(_get_meta(challenge_id)):
        abort(403)
    pub, priv, repo_path, error = _build_export(challenge_id)
    return render_template_string(_EXPORT_TMPL, challenge=chal, public_yaml=pub,
                                  private_yaml=priv, repo_path=repo_path, error=error)


@bp.route("/is1ab/challenges/<int:challenge_id>/export/<which>.yml", methods=["GET"])
@authed_only
def challenge_export_file(challenge_id, which):
    if which not in ("public", "private"):
        abort(404)
    # 下載 private.yml 會直接洩漏 flag/官方解 → 同樣要 ACL
    if not _can_edit(_get_meta(challenge_id)):
        abort(403)
    pub, priv, _repo_path, error = _build_export(challenge_id)
    if error:
        abort(400)
    body = pub if which == "public" else priv
    return Response(body or "", mimetype="text/yaml",
                    headers={"Content-Disposition": f"attachment; filename={which}.yml"})


# --------------------------------------------------------------------------- #
# 唯讀檢視 + 留言（任何登入者；不含 flag/私密欄位）
# --------------------------------------------------------------------------- #

def _flag_prefix():
    try:
        with open("/repo/config.yml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("project", {}).get("flag_prefix", "is1abCTF")
    except Exception:
        return "is1abCTF"


def _flag_format_ok(flag):
    if not flag:
        return False
    return bool(re.match(rf"^{re.escape(_flag_prefix())}\{{.*\}}$", str(flag)))


def _comments_for(challenge_id):
    umap = _users_map()
    out = []
    for c in (ChallengeComment.query.filter_by(challenge_id=challenge_id)
              .order_by(ChallengeComment.id).all()):
        out.append({"name": umap.get(c.user_id) or "（未知）", "body": c.body,
                    "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""})
    return out


_CHAL_SRC_BASES = ["/repo/challenges", "/repo/challenges/examples", "/repo"]
_SRC_TEXT_EXT = {".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".js", ".ts", ".go", ".rs",
                 ".java", ".rb", ".php", ".sh", ".txt", ".md", ".yml", ".yaml", ".json",
                 ".html", ".css", ".sql", ".cfg", ".ini", ".toml", ".env", ".s", ".asm"}
_SRC_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv"}
_SRC_SENSITIVE_FILES = {"flag", "flag.txt", "private.yml"}       # 不顯示（洩 flag）
_SRC_EDITOR_ONLY_DIRS = {"solution", "writeup"}                 # 官方解/writeup 洩答案 → 僅編輯者


def _source_dir(repo_path):
    if not repo_path:
        return None
    safe = repo_path.strip("/").replace("..", "")
    for base in _CHAL_SRC_BASES:
        cand = os.path.join(base, safe)
        if os.path.isdir(cand):
            return cand
    return None


def _read_source(repo_path, include_editor_only):
    """讀掛載 repo 內的題目程式（src/docker/files…）供唯讀檢視。回傳 (顯示用相對路徑, [檔案])。
    flag 檔一律略過；solution/writeup 僅編輯者可見。文字檔 <60KB 附內容，其餘只列大小。"""
    d = _source_dir(repo_path)
    if not d:
        return None, []
    out = []
    for root, dirs, fnames in os.walk(d):
        dirs[:] = [x for x in dirs if x not in _SRC_SKIP_DIRS]
        rel_root = os.path.relpath(root, d)
        top = "" if rel_root == "." else rel_root.split(os.sep)[0]
        if not include_editor_only and top in _SRC_EDITOR_ONLY_DIRS:
            dirs[:] = []
            continue
        for fn in sorted(fnames):
            if fn in _SRC_SENSITIVE_FILES:
                continue
            full = os.path.join(root, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            is_text = (ext in _SRC_TEXT_EXT or fn in ("Dockerfile", "Makefile")) and size < 60000
            text = None
            if is_text:
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    text = None
            out.append({"path": os.path.relpath(full, d), "size": size, "text": text})
    out.sort(key=lambda x: x["path"])
    try:
        rel = os.path.relpath(d, "/repo")
    except ValueError:
        rel = d
    return rel, out


_VIEW_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div>
  <h1>{{ v.name }}
    {% if v.dev_status %}<span class="badge badge-{{ (status_label.get(v.dev_status) or ['','secondary'])[1] }}">{{ (status_label.get(v.dev_status) or [v.dev_status])[0] }}</span>{% endif %}
  </h1>
  <p class="text-muted">#{{ v.id }} · {{ v.category }} / {{ v.difficulty }} · {{ v.value }} 分</p>
  {% if can_edit %}<a class="btn btn-primary btn-sm" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=v.id) }}">編輯</a>{% else %}<span class="badge badge-light">唯讀（你不是出題者/協作者）</span>{% endif %}
  <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回清單</a>
</div></div>
<div class="container">
  <table class="table table-sm">
    <tr><th style="width:120px">Flag</th><td><code>{{ v.flag or '（未設）' }}</code>{% if v.flag_type=='regex' %} <span class="badge badge-info">regex</span>{% endif %} {% if flag_ok %}<span class="badge badge-success">格式正確</span>{% else %}<span class="badge badge-danger" title="應為 {{ flag_prefix }}{...}">格式不符 / 未設（應為 {{ flag_prefix }}{...}）</span>{% endif %} <small class="text-muted">載入:{{ v.flag_load or 'static' }} · 範圍:{{ v.flag_scope or 'shared' }}</small></td></tr>
    <tr><th>出題者</th><td>{{ v.author or '—' }}</td></tr>
    <tr><th>驗題者</th><td>{% if v.reviewers %}{{ v.reviewers|join(', ') }}{% else %}—{% endif %}</td></tr>
    <tr><th>交付方式</th><td>{{ v.deploy_type or '—' }}{% if v.connection %}（{{ v.connection }}）{% endif %} · 原始碼：{{ '提供' if v.source_code_provided else '不提供' }}</td></tr>
    {% if v.tags %}<tr><th>Tags</th><td>{{ v.tags|join(', ') }}</td></tr>{% endif %}
    {% if v.files %}<tr><th>附件</th><td>{{ v.files|join(', ') }}</td></tr>{% endif %}
  </table>
  <h5 class="mt-3">描述</h5>
  <div class="border rounded p-2 mb-3" style="white-space:pre-wrap">{{ v.description or '（無）' }}</div>
  {% if v.hints %}<h5>提示</h5><ul>{% for h in v.hints %}<li>[{{ h.cost }}分] {{ h.content }}</li>{% endfor %}</ul>{% endif %}
  {% if v.internal_notes %}<h5 class="mt-3">內部筆記 <small class="text-muted">（開發/審題）</small></h5>
  <div class="border rounded p-2 mb-2" style="white-space:pre-wrap">{{ v.internal_notes }}</div>{% endif %}
  {% if src_files %}
  <h5 class="mt-3">題目程式 <small class="text-muted">（repo: {{ src_rel }}／{{ src_files|length }} 檔）</small></h5>
  {% for f in src_files %}
    <div class="mb-2"><code>{{ f.path }}</code> <small class="text-muted">({{ f.size }} bytes)</small>
    {% if f.text %}<pre class="border rounded p-2" style="max-height:360px;overflow:auto;font-size:.85em">{{ f.text }}</pre>{% else %}<div class="text-muted"><small>（二進位 / 大檔，不顯示內容）</small></div>{% endif %}</div>
  {% endfor %}
  {% else %}
  <p class="text-muted mt-3"><small>題目程式不在掛載的 repo（此題為匯入或尚未 commit 到 <code>challenges/{{ v.repo_path }}</code>）。</small></p>
  {% endif %}
  <p class="text-muted"><small>全體出題者皆可檢視此頁（含 flag / 官方解），方便審題與確認 flag；但只有出題者／協作者／admin 能「編輯」或「匯出」，避免誤改。</small></p>

  <h4 class="mt-4">建立實例 <small class="text-muted">（CTFd 內 build+run 題目 docker，注入正確 flag，快速驗題）</small></h4>
  {% if deploy_msg %}<div class="alert alert-secondary" style="white-space:pre-wrap">{{ deploy_msg }}</div>{% endif %}
  <p>狀態：{% if deploy_running %}<span class="badge badge-success">運行中</span>{% if deploy_ports %} · 連線埠：{% for p in deploy_ports %}<code>localhost:{{ p }}</code>{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}{% else %}<span class="badge badge-secondary">未部署</span>{% endif %}
    {% if deploy_files %} · 已上傳：{% for fn in deploy_files %}<code>{{ fn }}</code>{% if not loop.last %}, {% endif %}{% endfor %}{% elif deploy_ready %} · <span class="text-muted">用 repo 內題目程式部署</span>{% else %} · <span class="text-muted">尚未上傳 docker 檔</span>{% endif %}</p>
  {% if can_edit %}
  <form method="post" action="{{ url_for('is1ab_authoring.deploy_upload', challenge_id=v.id) }}" enctype="multipart/form-data" class="form-inline mb-2">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <input type="file" name="files" multiple class="form-control-file mr-2">
    <button class="btn btn-sm btn-outline-secondary" type="submit">上傳 docker 檔（可多檔 / .zip）</button>
  </form>
  {% endif %}
  {% if not deploy_ready %}<p class="text-muted"><small>此題無可部署的 compose。{% if not can_edit %}請出題者上傳 docker 檔，或把題目 code commit 到 repo。{% else %}請上傳 docker 檔（Dockerfile + docker-compose.yml）。{% endif %}</small></p>{% endif %}
  <form method="post" action="{{ url_for('is1ab_authoring.deploy_up', challenge_id=v.id) }}" style="display:inline">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <button class="btn btn-sm btn-success" type="submit" {{ 'disabled' if not deploy_ready else '' }}>▶ 建立實例</button>
  </form>
  <form method="post" action="{{ url_for('is1ab_authoring.deploy_stop', challenge_id=v.id) }}" style="display:inline">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <button class="btn btn-sm btn-outline-danger" type="submit" {{ 'disabled' if not deploy_running else '' }}>🧹 收掉</button>
  </form>

  <h4 class="mt-4">驗題 <small class="text-muted">（任何出題者皆可設驗題者 / 自薦 / 標記結論）</small></h4>
  <p>驗題結果：
    {% if v.test_status == 'passed' %}<span class="badge badge-success">通過</span>
    {% elif v.test_status == 'failed' %}<span class="badge badge-danger">退回</span>
    {% else %}<span class="badge badge-secondary">待驗</span>{% endif %}
    {% if v.tested_by %}<small class="text-muted">by {{ v.tested_by }}</small>{% endif %}
    <form method="post" action="{{ url_for('is1ab_authoring.challenge_review_outcome', challenge_id=v.id) }}" style="display:inline" class="ml-2">
      <input type="hidden" name="nonce" value="{{ nonce }}"><input type="hidden" name="outcome" value="passed">
      <button class="btn btn-sm btn-outline-success" type="submit">標記通過</button></form>
    <form method="post" action="{{ url_for('is1ab_authoring.challenge_review_outcome', challenge_id=v.id) }}" style="display:inline">
      <input type="hidden" name="nonce" value="{{ nonce }}"><input type="hidden" name="outcome" value="failed">
      <button class="btn btn-sm btn-outline-danger" type="submit">退回</button></form>
    <form method="post" action="{{ url_for('is1ab_authoring.challenge_review_me', challenge_id=v.id) }}" style="display:inline">
      <input type="hidden" name="nonce" value="{{ nonce }}">
      <button class="btn btn-sm btn-outline-secondary" type="submit">＋把我加為驗題者</button></form>
  </p>
  <form method="post" action="{{ url_for('is1ab_authoring.challenge_set_reviewers', challenge_id=v.id) }}" class="mb-3">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <label class="text-muted"><small>驗題者名單（多選；按住 Ctrl/Cmd 可複選，避免洗掉他人）</small></label>
    <select class="form-control" name="reviewers" multiple size="4">
      {% for u in users %}<option value="{{ u.id }}" {{ 'selected' if (u.id|string) in cur_reviewers else '' }}>{{ u.name }}</option>{% endfor %}
    </select>
    <button class="btn btn-sm btn-primary mt-2" type="submit">更新驗題者名單</button>
  </form>

  {% if verify_cmd %}
  <h4 class="mt-4">快速驗題 <small class="text-muted">（本機 clone 執行：起服務 → 跑官方解 → 比對 flag）</small></h4>
  <pre class="border rounded p-2">{{ verify_cmd }}</pre>
  {% endif %}

  <h4 class="mt-4">留言 <small class="text-muted">（{{ comments|length }}）</small></h4>
  {% for c in comments %}
    <div class="border rounded p-2 mb-2"><strong>{{ c.name }}</strong> <small class="text-muted">{{ c.created_at }}</small>
      <div style="white-space:pre-wrap">{{ c.body }}</div></div>
  {% else %}<p class="text-muted">還沒有留言。</p>{% endfor %}

  <form method="post" action="{{ url_for('is1ab_authoring.challenge_comment', challenge_id=v.id) }}" class="mt-2 mb-4">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <div class="form-group"><textarea class="form-control" name="body" rows="2" placeholder="留言（審題回饋 / 討論）" required></textarea></div>
    <button class="btn btn-success btn-sm" type="submit">送出留言</button>
  </form>
</div>
{% endblock %}
"""


@bp.route("/is1ab/challenges/<int:challenge_id>/view", methods=["GET"])
@authed_only
def challenge_view(challenge_id):
    """任何登入者可唯讀檢視（不含 flag/私密欄位）+ 看留言。"""
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = _get_meta(challenge_id)
    mf = _blob_to_fields(meta.blob if meta else "")
    fl = Flags.query.filter_by(challenge_id=challenge_id).first()
    umap = _users_map()
    reviewers = _reviewers_by_cid({m.challenge_id: m for m in ChallengeMetadata.query.all()},
                                  umap).get(challenge_id, [])
    hints = Hints.query.filter_by(challenge_id=challenge_id).order_by(Hints.cost).all()
    tags = [t.value for t in Tags.query.filter_by(challenge_id=challenge_id)]
    view = {
        "id": chal.id, "name": chal.name, "category": chal.category,
        "difficulty": mf.get("difficulty") or _challenge_difficulty(challenge_id),
        "value": chal.value, "description": chal.description,
        "deploy_type": mf.get("deploy_type"), "connection": mf.get("deploy_connection"),
        "source_code_provided": mf.get("source_code_provided"),
        "files": [x for x in (mf.get("files") or "").splitlines() if x.strip()],
        "author": (umap.get(meta.owner_id) if meta else None),
        "reviewers": reviewers, "dev_status": (meta.dev_status if meta else None),
        "hints": [{"cost": h.cost, "content": h.content} for h in hints], "tags": tags,
        "repo_path": (meta.repo_path if meta else None),
        "flag": (fl.content if fl else None), "flag_type": (fl.type if fl else None),
        "flag_load": mf.get("flag_load"), "flag_scope": mf.get("flag_scope"),
        "internal_notes": mf.get("internal_notes"),
        "test_status": mf.get("test_status"), "tested_by": mf.get("test_by"),
    }
    # 點1：全體出題者皆可檢視（含官方解/writeup）；只有「編輯/匯出」受 ACL 保護
    src_rel, src_files = _read_source(meta.repo_path if meta else None, True)
    asg = _assignment_for(challenge_id)
    cur_reviewers = set((asg.reviewer_ids or "").split(",")) if asg else set()
    # 快速驗題指令只在程式實際掛在 repo 時才顯示（否則本機也跑不動）
    verify_cmd = (f'make verify-solution ARGS="challenges/{view["repo_path"]}"'
                  if (view["repo_path"] and _source_dir(view["repo_path"])) else None)
    return render_template_string(_VIEW_TMPL, v=view, comments=_comments_for(challenge_id),
                                  can_edit=_can_edit(meta), nonce=session.get("nonce", ""),
                                  status_label=DEV_STATUS_LABEL, src_rel=src_rel, src_files=src_files,
                                  flag_ok=_flag_format_ok(view["flag"]), verify_cmd=verify_cmd,
                                  flag_prefix=_flag_prefix(),
                                  users=Users.query.all(), cur_reviewers=cur_reviewers,
                                  deploy_msg=session.pop("deploy_msg", None),
                                  deploy_files=_list_deploy_files(challenge_id),
                                  deploy_ready=_deploy_ready(challenge_id, view["repo_path"]),
                                  deploy_running=_deploy_status(challenge_id) > 0,
                                  deploy_ports=_deploy_live_ports(challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/comment", methods=["POST"])
@authed_only
def challenge_comment(challenge_id):
    """任何登入者可留言（審題/討論）。"""
    Challenges.query.filter_by(id=challenge_id).first_or_404()
    user = get_current_user()
    body = (request.form.get("body") or "").strip()
    if body:
        db.session.add(ChallengeComment(
            challenge_id=challenge_id, user_id=(user.id if user else None), body=body[:5000]))
        db.session.commit()
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/reviewers", methods=["POST"])
@authed_only
def challenge_set_reviewers(challenge_id):
    """任何登入出題者皆可設定驗題者（自薦 / 指定他人）；PM 的 /assignments 仍可指派。"""
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    rids = ",".join(x for x in request.form.getlist("reviewers") if x.strip())
    asg = _assignment_for(challenge_id)   # 找 PM 既有工單（含自動關聯），避免重建
    if asg is None:
        meta = _get_meta(challenge_id)
        asg = Assignment(challenge_id=challenge_id,
                         author_id=(meta.owner_id if meta else None),
                         category=chal.category, difficulty=_challenge_difficulty(challenge_id),
                         reviewer_ids=rids, status="assigned")
        db.session.add(asg)
    else:
        asg.reviewer_ids = rids
        if asg.challenge_id is None:      # 回填 challenge_id → 之後直連、不再靠猜
            asg.challenge_id = challenge_id
    db.session.commit()
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/review-me", methods=["POST"])
@authed_only
def challenge_review_me(challenge_id):
    """驗題者自薦：把自己 append 進驗題者名單（不覆寫他人）。"""
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    user = get_current_user()
    asg = _assignment_for(challenge_id)
    ids = set(x for x in (asg.reviewer_ids or "").split(",") if x) if asg else set()
    if user:
        ids.add(str(user.id))
    if asg is None:
        meta = _get_meta(challenge_id)
        asg = Assignment(challenge_id=challenge_id, author_id=(meta.owner_id if meta else None),
                         category=chal.category, difficulty=_challenge_difficulty(challenge_id),
                         reviewer_ids=",".join(sorted(ids)), status="assigned")
        db.session.add(asg)
    else:
        asg.reviewer_ids = ",".join(sorted(ids))
        if asg.challenge_id is None:
            asg.challenge_id = challenge_id
    db.session.commit()
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/review-outcome", methods=["POST"])
@authed_only
def challenge_review_outcome(challenge_id):
    """驗題者標記結論（通過/退回），寫入 metadata blob 的 testing.test_status + tested_by。"""
    Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = _get_meta(challenge_id)
    if not meta:
        abort(404)
    outcome = request.form.get("outcome")
    if outcome not in ("passed", "failed"):
        abort(400)
    user = get_current_user()
    try:
        blob = yaml.safe_load(meta.blob) if meta.blob else {}
    except yaml.YAMLError:
        blob = {}
    if not isinstance(blob, dict):
        blob = {}
    testing = blob.get("testing") if isinstance(blob.get("testing"), dict) else {}
    testing["test_status"] = outcome
    testing["tested_by"] = (user.name if user else "")
    blob["testing"] = testing
    meta.blob = yaml.safe_dump(blob, sort_keys=False, allow_unicode=True)
    db.session.commit()
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


# --------------------------------------------------------------------------- #
# CTFd 內一鍵部署（掛 docker socket；上傳 docker 檔 → build/run → 收掉）
# --------------------------------------------------------------------------- #

DEPLOY_ROOT = "/var/uploads/is1ab_deploy"
_COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")


def _deploy_dir(cid):
    return os.path.join(DEPLOY_ROOT, str(cid))


def _deploy_project(cid):
    return f"is1ab{cid}"


def _list_deploy_files(cid):
    d = _deploy_dir(cid)
    out = []
    if os.path.isdir(d):
        for root, _dirs, fns in os.walk(d):
            for fn in fns:
                if fn == "docker-compose.deploy.yml":
                    continue
                out.append(os.path.relpath(os.path.join(root, fn), d))
    return sorted(out)


def _find_compose(d):
    for root, _dirs, fns in os.walk(d):
        for name in _COMPOSE_NAMES:
            if name in fns:
                return os.path.join(root, name)
    return None


def _transform_compose(src_path, out_path, flag):
    """處理已知坑：剝 external network（frp/whale）、expose→補 ports、注入 FLAG=正確flag。"""
    data = yaml.safe_load(open(src_path, encoding="utf-8")) or {}
    data.pop("networks", None)
    warnings = []
    for _name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        svc.pop("networks", None)
        if isinstance(svc.get("services"), dict):   # 巢狀畸形 services（whale 模板）
            svc.pop("services", None)
            warnings.append("移除巢狀 services（whale 模板）")
        if not svc.get("ports"):                    # expose 但無 ports → 補 host port
            ports = [f"{p}:{p}" for p in (svc.get("expose") or [])]
            if ports:
                svc["ports"] = ports
                warnings.append(f"補 ports {ports}")
        env = svc.get("environment")                # 注入正確 flag（env-based 題目）
        if isinstance(env, list):
            env = [e for e in env if str(e).split("=", 1)[0].strip() != "FLAG"]
            if flag:
                env.append(f"FLAG={flag}")
            svc["environment"] = env
        elif isinstance(env, dict):
            if flag:
                env["FLAG"] = flag
        elif flag:
            svc["environment"] = [f"FLAG={flag}"]
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return warnings, data


def _deploy_ports(compose_data):
    ports = []
    for _name, svc in (compose_data.get("services") or {}).items():
        for pm in (svc.get("ports") or []):
            host = str(pm).split(":")[0]
            if host.isdigit():
                ports.append(host)
    return ports


def _deploy_ready(cid, repo_path):
    """是否有可部署的 compose：上傳目錄，或 repo 內的題目目錄（committed 題）。"""
    d = _deploy_dir(cid)
    if os.path.isdir(d) and _find_compose(d):
        return True
    src = _source_dir(repo_path)
    return bool(src and _find_compose(src))


def _resolve_deploy_dir(cid, repo_path):
    """回傳可部署工作目錄。優先上傳目錄；否則把 repo 題目目錄複製到上傳目錄（不在 repo 內 build / 留 deploy 檔）。"""
    d = _deploy_dir(cid)
    if os.path.isdir(d) and _find_compose(d):
        return d
    src = _source_dir(repo_path)
    if src and _find_compose(src):
        if os.path.isdir(d):
            shutil.rmtree(d)
        shutil.copytree(src, d, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        return d
    return None


def _deploy_instance(cid, flag, repo_path=None):
    d = _resolve_deploy_dir(cid, repo_path)
    if not d:
        return False, "尚未上傳 docker 檔，且 repo 內也沒有可部署的 compose（Dockerfile / docker-compose.yml）", []
    compose = _find_compose(d)
    if not compose:
        return False, "找不到 docker-compose.yml（目前一鍵部署僅支援 compose）", []
    workdir = os.path.dirname(compose)
    out = os.path.join(workdir, "docker-compose.deploy.yml")
    try:
        warnings, data = _transform_compose(compose, out, flag)
    except Exception as e:
        return False, f"compose 解析失敗：{e}", []
    try:
        r = subprocess.run(["docker", "compose", "-p", _deploy_project(cid), "-f", out,
                            "up", "--build", "-d"], cwd=workdir,
                           capture_output=True, text=True, timeout=420)
    except subprocess.TimeoutExpired:
        return False, "部署逾時（>7 分鐘）", []
    if r.returncode != 0:
        return False, "部署失敗：\n" + (r.stderr or r.stdout)[-1800:], []
    note = ("；".join(warnings) + "。") if warnings else ""
    return True, f"部署成功。{note}", _deploy_ports(data)


def _deploy_status(cid):
    """回傳運行中的服務數（>0 即已部署）。"""
    try:
        r = subprocess.run(["docker", "compose", "-p", _deploy_project(cid), "ps", "-q"],
                           capture_output=True, text=True, timeout=30)
        return len([x for x in r.stdout.splitlines() if x.strip()])
    except Exception:
        return 0


def _deploy_live_ports(cid):
    """查目前運行中實例對外發布的 host 埠（常駐顯示，不靠 session）。"""
    try:
        r = subprocess.run(["docker", "ps", "--filter",
                            f"label=com.docker.compose.project={_deploy_project(cid)}",
                            "--format", "{{.Ports}}"], capture_output=True, text=True, timeout=30)
        ports = set()
        for line in r.stdout.splitlines():
            for m in re.findall(r":(\d+)->", line):
                ports.add(m)
        return sorted(ports, key=lambda x: int(x))
    except Exception:
        return []


def _deploy_down(cid):
    try:
        subprocess.run(["docker", "compose", "-p", _deploy_project(cid), "down", "-v"],
                       capture_output=True, text=True, timeout=120)
    except Exception:
        pass


@bp.route("/is1ab/challenges/<int:challenge_id>/deploy-files", methods=["POST"])
@authed_only
def deploy_upload(challenge_id):
    """上傳 Dockerfile / docker-compose.yml / 其他設定檔（含 .zip 解壓）。僅編輯者。"""
    Challenges.query.filter_by(id=challenge_id).first_or_404()
    if not _can_edit(_get_meta(challenge_id)):
        abort(403)
    d = _deploy_dir(challenge_id)
    os.makedirs(d, exist_ok=True)
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        name = os.path.basename(f.filename)
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                    for member in z.namelist():
                        if member.endswith("/") or ".." in member or member.startswith("/"):
                            continue
                        target = os.path.join(d, member)
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with z.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            except zipfile.BadZipFile:
                pass
        else:
            f.save(os.path.join(d, name))
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/deploy", methods=["POST"])
@authed_only
def deploy_up(challenge_id):
    """一鍵部署實例（任何出題者可測）。注入 CTFd 的正確 flag 為 FLAG env。"""
    Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = _get_meta(challenge_id)
    fl = Flags.query.filter_by(challenge_id=challenge_id).first()
    ok, msg, ports = _deploy_instance(challenge_id, fl.content if fl else "",
                                      meta.repo_path if meta else None)
    session["deploy_msg"] = ("✅ " if ok else "❌ ") + msg + (f"（連線埠：{', '.join(ports)}）" if ports else "")
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


@bp.route("/is1ab/challenges/<int:challenge_id>/deploy-down", methods=["POST"])
@authed_only
def deploy_stop(challenge_id):
    Challenges.query.filter_by(id=challenge_id).first_or_404()
    _deploy_down(challenge_id)
    session["deploy_msg"] = "🧹 已收掉實例。"
    return redirect(url_for("is1ab_authoring.challenge_view", challenge_id=challenge_id))


# --------------------------------------------------------------------------- #
# PM：配額 + 指派（admin-only）
# --------------------------------------------------------------------------- #

_QUOTA_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div>
  <h1>配額規劃</h1>
  <p>各分類 × 難度的目標題數。格子顯示 <b>已建 / 目標</b>；已達標為綠色。</p>
</div></div>
<div class="container">
  {% if saved %}<div class="alert alert-success">已儲存。</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <table class="table table-bordered text-center">
      <thead><tr><th>分類 \\ 難度</th>{% for d in difficulties %}<th>{{ d }}</th>{% endfor %}</tr></thead>
      <tbody>
      {% for cat in categories %}
        <tr><th class="align-middle">{{ cat }}</th>
        {% for d in difficulties %}
          {% set target, actual = data[cat][d] %}
          <td>
            <span class="{{ 'text-success font-weight-bold' if target>0 and actual>=target else 'text-muted' }}">{{ actual }}</span>
            / <input type="number" min="0" name="t_{{ cat }}_{{ d }}" value="{{ target }}" style="width:4em">
          </td>
        {% endfor %}
        </tr>
      {% endfor %}
      </tbody>
    </table>
    <button class="btn btn-primary" type="submit">儲存配額</button>
    <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回</a>
  </form>
</div>
{% endblock %}
"""

_ASSIGN_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div><h1>出題 / 驗題指派</h1>
  <p>PM 建工單、指派出題者與驗題者；題目建好後可回填「對應題目」。</p></div></div>
<div class="container">
  <h4>建立工單</h4>
  <p class="text-muted">只需「誰出什麼 × 誰驗」。進度看題目本身的 dev_status,不用另填狀態;題目建好會自動關聯(同分類×難度×出題者),不必手動連。</p>
  <form method="POST" class="form-row">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <div class="form-group col-md-2"><label>分類</label><select class="form-control" name="category">{% for c in categories %}<option>{{ c }}</option>{% endfor %}</select></div>
    <div class="form-group col-md-2"><label>難度</label><select class="form-control" name="difficulty">{% for d in difficulties %}<option>{{ d }}</option>{% endfor %}</select></div>
    <div class="form-group col-md-3"><label>出題者</label><select class="form-control" name="author_id"><option value="">—</option>{% for u in users %}<option value="{{ u.id }}">{{ u.name }}</option>{% endfor %}</select></div>
    <div class="form-group col-md-3"><label>驗題者（多選）</label><select class="form-control" name="reviewers" multiple>{% for u in users %}<option value="{{ u.id }}">{{ u.name }}</option>{% endfor %}</select></div>
    <div class="form-group col-md-2 align-self-end"><button class="btn btn-success btn-block" type="submit">新增工單</button></div>
  </form>
  <hr>
  <table class="table table-striped">
    <thead><tr><th>#</th><th>分類/難度</th><th>出題者</th><th>驗題者</th><th>對應題目</th><th>進度</th><th></th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td>{{ r.a.id }}</td><td>{{ r.a.category }}/{{ r.a.difficulty }}</td>
        <td>{{ r.author }}</td><td>{{ r.reviewers }}</td>
        <td>{% if r.cid %}<a href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=r.cid) }}">進題目 #{{ r.cid }}</a>{% else %}<span class="text-muted">未建</span>{% endif %}</td>
        <td>{% if r.status %}<span class="badge badge-{{ (status_label.get(r.status) or ['','secondary'])[1] }}">{{ (status_label.get(r.status) or [r.status])[0] }}</span>{% else %}<span class="text-muted">—</span>{% endif %}</td>
        <td><form method="POST" onsubmit="return confirm('刪除工單？')">
          <input type="hidden" name="nonce" value="{{ nonce }}">
          <input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ r.a.id }}">
          <button class="btn btn-sm btn-outline-danger">刪</button></form></td>
      </tr>
    {% else %}<tr><td colspan="7" class="text-center text-muted">還沒有工單。</td></tr>{% endfor %}
    </tbody>
  </table>
  {% if quota_rows %}
  <h4 class="mt-4">配額 vs 指派 vs 已建</h4>
  <table class="table table-sm" style="max-width:520px">
    <thead><tr><th>分類/難度</th><th>配額</th><th>已指派</th><th>已建</th><th>缺</th></tr></thead>
    <tbody>{% for q in quota_rows %}<tr>
      <td>{{ q.category }}/{{ q.difficulty }}</td><td>{{ q.target }}</td>
      <td>{% if q.assigned > q.target %}<span class="text-danger">{{ q.assigned }}（超額）</span>{% else %}{{ q.assigned }}{% endif %}</td>
      <td>{{ q.built }}</td>
      <td>{% set miss = q.target - q.built %}{% if miss > 0 %}<span class="badge badge-danger">{{ miss }}</span>{% else %}0{% endif %}</td>
    </tr>{% endfor %}</tbody>
  </table>{% endif %}
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回</a>
</div>
{% endblock %}
"""


@bp.route("/is1ab/quota", methods=["GET", "POST"])
@admins_only
def quota_page():
    saved = False
    if request.method == "POST":
        for cat in CATEGORIES:
            for diff in DIFFICULTIES:
                raw = request.form.get(f"t_{cat}_{diff}", "").strip()
                target = int(raw) if raw.isdigit() else 0
                q = ChallengeQuota.query.filter_by(category=cat, difficulty=diff).first()
                if q is None:
                    if target:
                        db.session.add(ChallengeQuota(category=cat, difficulty=diff, target=target))
                else:
                    q.target = target
        db.session.commit()
        saved = True
    return render_template_string(_QUOTA_TMPL, data=_quota_data(),
                                  categories=CATEGORIES, difficulties=DIFFICULTIES,
                                  nonce=session.get("nonce", ""), saved=saved)


@bp.route("/is1ab/assignments", methods=["GET", "POST"])
@admins_only
def assignments_page():
    if request.method == "POST":
        if request.form.get("action") == "delete":
            Assignment.query.filter_by(id=request.form.get("id")).delete()
            db.session.commit()
        else:
            # 工單只記「誰出、誰驗、哪個 category×difficulty」；進度用題目的 dev_status，不另開狀態機
            db.session.add(Assignment(
                category=request.form.get("category", ""),
                difficulty=request.form.get("difficulty", ""),
                author_id=int(request.form["author_id"]) if request.form.get("author_id") else None,
                reviewer_ids=",".join(request.form.getlist("reviewers")),
                challenge_id=int(request.form["challenge_id"]) if request.form.get("challenge_id") else None,
            ))
            db.session.commit()
        return redirect(url_for("is1ab_authoring.assignments_page"))

    umap = _users_map()
    metas = ChallengeMetadata.query.all()
    status_by_cid = {m.challenge_id: m.dev_status for m in metas}
    by_owner_catdiff = {}
    built_ct = {}
    for c in Challenges.query.all():
        m = next((x for x in metas if x.challenge_id == c.id), None)
        diff = _challenge_difficulty(c.id)
        if m and m.owner_id:
            by_owner_catdiff[(m.owner_id, c.category, diff)] = c.id
        built_ct[(c.category, diff)] = built_ct.get((c.category, diff), 0) + 1
    rows = []
    assigned_ct = {}
    for a in Assignment.query.order_by(Assignment.id).all():
        cid = a.challenge_id or by_owner_catdiff.get((a.author_id, a.category, a.difficulty))
        assigned_ct[(a.category, a.difficulty)] = assigned_ct.get((a.category, a.difficulty), 0) + 1
        rows.append({
            "a": a, "cid": cid,
            "author": umap.get(a.author_id, "—"),
            "reviewers": ", ".join(umap.get(int(x), x) for x in (a.reviewer_ids or "").split(",") if x),
            "status": status_by_cid.get(cid),
        })
    # 配額 vs 指派 vs 已建（超額 / 未指派一眼可辨）
    quota_rows = []
    for q in ChallengeQuota.query.all():
        key = (q.category, q.difficulty)
        quota_rows.append({"category": q.category, "difficulty": q.difficulty, "target": q.target,
                           "assigned": assigned_ct.get(key, 0), "built": built_ct.get(key, 0)})
    quota_rows.sort(key=lambda x: (x["category"], x["difficulty"]))
    return render_template_string(_ASSIGN_TMPL, rows=rows, users=Users.query.all(),
                                  quota_rows=quota_rows, status_label=DEV_STATUS_LABEL,
                                  categories=CATEGORIES, difficulties=DIFFICULTIES,
                                  nonce=session.get("nonce", ""))


# --------------------------------------------------------------------------- #
# Phase 8：前台儀表板 + 我的題目（登入才可見）
# --------------------------------------------------------------------------- #

_DASH_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div><h1>開發進度儀表板</h1>
  <p>全隊共用視圖（登入才可見）：題目分布（含指派）、在途 PR。</p></div></div>
<div class="container">
  {% if show_admin %}<div class="mb-3">
    <a class="btn btn-outline-primary btn-sm" href="{{ url_for('is1ab_authoring.quota_page') }}">配額</a>
    <a class="btn btn-outline-primary btn-sm" href="{{ url_for('is1ab_authoring.assignments_page') }}">指派</a>
    <a class="btn btn-outline-secondary btn-sm" href="/admin/config">CTFd 後台設定</a>
    <a class="btn btn-outline-secondary btn-sm" href="/admin/users">帳號管理</a>
  </div>{% endif %}
  <div class="card mb-3"><div class="card-body py-2">
    <span class="mr-3"><strong>總配額</strong> {{ summary.target }}</span>
    <span class="mr-3">已建 <span class="badge badge-info">{{ summary.built }}</span></span>
    <span class="mr-3">完成 <span class="badge badge-success">{{ summary.completed }}</span></span>
    <span class="mr-3">缺 <span class="badge badge-{{ 'danger' if summary.missing else 'secondary' }}">{{ summary.missing }}</span></span>
    <span class="mr-3">完成率 <strong>{{ summary.rate }}%</strong></span>
    {% if summary.stalled %}<span class="mr-3">停滯 <span class="badge badge-danger">{{ summary.stalled }}</span></span>{% endif %}
    {% if summary.uncat %}<span class="mr-3">未分類 <span class="badge badge-warning">{{ summary.uncat }}</span></span>{% endif %}
  </div></div>
  {% if stalled %}
  <div class="alert alert-danger py-2"><strong>🕒 停滯題（{{ stalled|length }}，逾 7 天沒動）</strong>：
    {% for s in stalled %}<a href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=s.cid) }}" class="badge badge-light border">{{ s.cname }} · {{ s.days }}天 · 出:{{ s.author or '?' }}</a> {% endfor %}
  </div>{% endif %}
  {% if uncategorized %}
  <div class="alert alert-warning py-2"><strong>⚠️ 落在配額格外的題（{{ uncategorized|length }}）</strong>
    ——分類非既有值或難度未填，不計入上方矩陣/配額：
    {% for u in uncategorized %}<a href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=u.cid) }}" class="badge badge-light border">{{ u.cname }}（{{ u.category }}/{{ u.difficulty }}）</a> {% endfor %}
  </div>{% endif %}
  <h4>題目分布（配額幾題就幾個位；點方格進題目）</h4>
  <table class="table table-bordered">
    <thead><tr><th>分類 \\ 難度</th>{% for d in difficulties %}<th class="text-center">{{ d }}</th>{% endfor %}</tr></thead>
    <tbody>{% for cat in categories %}<tr><th class="align-middle">{{ cat }}</th>
      {% for d in difficulties %}{% set cell = data[cat][d] %}
      <td style="vertical-align:top">
        {% for s in cell.slots %}
          {% if s.cid %}
          <a class="d-block mb-1 px-2 py-1 border rounded" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=s.cid) }}">{{ s.cname }}{% if s.status %} <span class="badge badge-{{ (status_label.get(s.status) or ['','secondary'])[1] }}">{{ (status_label.get(s.status) or [s.status])[0] }}</span>{% endif %}{% if s.review == 'passed' %} <span class="badge badge-success">驗✓</span>{% elif s.review == 'failed' %} <span class="badge badge-danger">驗✗</span>{% endif %}{% if s.author %} <small class="text-muted">出:{{ s.author }}</small>{% endif %}{% if s.reviewers %}<br><small class="text-muted">驗:{{ s.reviewers|join(',') }}</small>{% endif %}</a>
          {% elif s.author %}
            {% if s.author_id == me %}
            <a class="d-block mb-1 px-2 py-1 border rounded bg-light" href="{{ url_for('is1ab_authoring.challenge_new') }}?category={{ cat }}&difficulty={{ d }}"><span class="text-info">{{ s.author }}</span> <small class="text-muted">未建 · 點我建題</small>{% if s.reviewers %}<br><small class="text-muted">驗:{{ s.reviewers|join(',') }}</small>{% endif %}</a>
            {% else %}
            <div class="mb-1 px-2 py-1 border rounded bg-light"><span class="text-info">{{ s.author }}</span> <small class="text-muted">未建</small>{% if s.reviewers %}<br><small class="text-muted">驗:{{ s.reviewers|join(',') }}</small>{% endif %}</div>
            {% endif %}
          {% else %}
          <div class="mb-1 px-2 py-1 border rounded text-center text-muted">缺</div>
          {% endif %}
        {% endfor %}
      </td>
      {% endfor %}</tr>{% endfor %}</tbody>
  </table>

  <h4 class="mt-4">在途 PR（尚未 merge）</h4>
  {% if pr_error %}<p class="text-muted">{{ pr_error }}</p>
  {% else %}<table class="table table-sm">
    <thead><tr><th>#</th><th>標題</th><th>作者</th><th>branch</th></tr></thead>
    <tbody>{% for p in prs %}<tr><td><a href="{{ p.url }}" target="_blank">#{{ p.number }}</a></td>
      <td>{{ p.title }}</td><td>{{ p.user }}</td><td><code>{{ p.branch }}</code></td></tr>
    {% else %}<tr><td colspan="4" class="text-muted text-center">沒有開著的 PR</td></tr>{% endfor %}</tbody>
  </table>{% endif %}
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">出題清單</a>
</div>
{% endblock %}
"""

_MINE_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div><h1>我的題目 / 指派給我</h1></div></div>
<div class="container">
  <h4>我的題目 <small class="text-muted">（出題 / 協作 / 指派待出）</small></h4>
  <table class="table table-sm table-striped">
    <thead><tr><th>題目</th><th>分類</th><th>難度</th><th>進度</th><th>角色</th><th></th></tr></thead>
    <tbody>{% for c in mine %}<tr>
      <td>{% if c.built %}{{ c.name }}{% else %}<span class="badge badge-warning">尚未建題</span>{% endif %}</td>
      <td>{{ c.category }}</td><td>{{ c.difficulty }}</td>
      <td>{% if c.dev_status %}<span class="badge badge-{{ (status_label.get(c.dev_status) or ['','secondary'])[1] }}">{{ (status_label.get(c.dev_status) or [c.dev_status])[0] }}</span>{% else %}<span class="text-muted">—</span>{% endif %}</td>
      <td>{{ c.role }}</td>
      <td>{% if c.built %}<a class="btn btn-sm btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=c.id) }}">編輯</a>{% else %}<a class="btn btn-sm btn-outline-info" href="{{ url_for('is1ab_authoring.challenge_new') }}?category={{ c.category }}&difficulty={{ c.difficulty }}">建題</a>{% endif %}</td>
    </tr>{% else %}<tr><td colspan="6" class="text-muted text-center">還沒有題目。想自己出題 → <a href="{{ url_for('is1ab_authoring.challenge_new') }}">＋新增題目</a>；或等 PM 在<a href="{{ url_for('is1ab_authoring.dashboard') }}">儀表板</a>指派給你。</td></tr>{% endfor %}</tbody>
  </table>

  <h4 class="mt-4">指派給我「驗題」</h4>
  <table class="table table-sm"><thead><tr><th>#</th><th>分類</th><th>難度</th><th>對應題目</th></tr></thead>
  <tbody>{% for a in to_review %}<tr><td>{{ a.id }}</td><td>{{ a.category }}</td><td>{{ a.difficulty }}</td>
    <td>{% if a.challenge_id %}<a href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=a.challenge_id) }}">進題目 #{{ a.challenge_id }} →</a>{% else %}<span class="text-muted">尚未建題</span>{% endif %}</td></tr>
  {% else %}<tr><td colspan="4" class="text-muted text-center">目前沒有指派給你的驗題。出題者可在題目頁把你設為驗題者。</td></tr>{% endfor %}</tbody></table>
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.dashboard') }}">儀表板</a>
</div>
{% endblock %}
"""


@bp.route("/is1ab/dashboard", methods=["GET"])
@authed_only
def dashboard():
    prs, pr_error = _open_prs()
    user = get_current_user()
    dash = _dashboard_matrix()
    return render_template_string(_DASH_TMPL, data=dash["grid"], summary=dash["summary"],
                                  uncategorized=dash["uncategorized"], stalled=dash["stalled"],
                                  categories=CATEGORIES, difficulties=DIFFICULTIES,
                                  prs=prs, pr_error=pr_error, status_label=DEV_STATUS_LABEL,
                                  show_admin=is_admin(), me=(user.id if user else None))


@bp.route("/is1ab/mine", methods=["GET"])
@authed_only
def my_page():
    user = get_current_user()
    mine, to_review = _my_stuff(user.id) if user else ([], [])
    return render_template_string(_MINE_TMPL, mine=mine, to_review=to_review,
                                  status_label=DEV_STATUS_LABEL)


# --------------------------------------------------------------------------- #
# 反向匯入：repo YAML → CTFd（round-trip）
# --------------------------------------------------------------------------- #

_IMPORT_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div><h1>從 repo 匯入題目</h1>
  <p>貼上既有題目的 <code>public.yml</code> 與 <code>private.yml</code>，在 dev CTFd 建出可編輯 / 試玩的題目（round-trip）。</p></div></div>
<div class="container">
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <div class="form-row">
      <div class="form-group col-md-6"><label>public.yml</label>
        <textarea class="form-control" name="public_yaml" rows="18" style="font-family:monospace">{{ public_yaml }}</textarea></div>
      <div class="form-group col-md-6"><label>private.yml <span class="badge badge-danger">敏感</span></label>
        <textarea class="form-control" name="private_yaml" rows="18" style="font-family:monospace">{{ private_yaml }}</textarea></div>
    </div>
    <button class="btn btn-primary" type="submit">匯入</button>
    <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.challenge_list') }}">返回清單</a>
  </form>
</div>
{% endblock %}
"""


@bp.route("/is1ab/import", methods=["GET", "POST"])
@authed_only
def challenge_import():
    error = None
    public_yaml = private_yaml = ""
    if request.method == "POST":
        public_yaml = request.form.get("public_yaml", "")
        private_yaml = request.form.get("private_yaml", "")
        if ctfd_convert is None:
            error = "轉換器未載入（/repo/scripts 未掛載？）"
        else:
            try:
                public = yaml.safe_load(public_yaml) or {}
                private = yaml.safe_load(private_yaml) or {}
            except yaml.YAMLError as e:
                error = f"YAML 解析失敗：{e}"
            else:
                if not isinstance(public, dict) or not public.get("title"):
                    error = "public.yml 需要至少 title"
                elif not isinstance(private, (dict, type(None))):
                    error = "private.yml 必須是一組鍵值"
        if not error:
            c = ctfd_convert.challenge_to_ctfd(public, private if isinstance(private, dict) else {})
            dev_status = str(c["blob"].pop("status", "developing")) or "developing"  # Ⓑ 抽成 first-class
            chal = Challenges(name=c["name"], description=c["description"],
                              value=int(c["value"] or 0), category=c["category"],
                              state="visible", type="standard")
            db.session.add(chal)
            db.session.commit()
            owner = get_current_user()
            db.session.add(ChallengeMetadata(
                challenge_id=chal.id, owner_id=(owner.id if owner else None),
                uid=(c["uid"] or _new_uid()), dev_status=dev_status,
                repo_path=f"{_slugify(c['category'])}/{_slugify(c['name'])}",
                blob=(yaml.safe_dump(c["blob"], sort_keys=False, allow_unicode=True) if c["blob"] else "")))
            db.session.commit()
            _sync_flag(chal.id, c["flag"], c["flag_type"])
            _sync_tags(chal.id, ",".join(c["tags"]))  # c["tags"] 是 list，_sync_tags 吃 CSV
            for h in c["hints"]:
                db.session.add(Hints(challenge_id=chal.id, content=h["content"], cost=int(h["cost"])))
            db.session.commit()
            return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=chal.id, created=1))
    return render_template_string(_IMPORT_TMPL, error=error, nonce=session.get("nonce", ""),
                                  public_yaml=public_yaml, private_yaml=private_yaml)


# --------------------------------------------------------------------------- #
# 團隊頁（取代參賽者 /users，顯示每人負載）
# --------------------------------------------------------------------------- #

_TEAM_TMPL = """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4 mb-3"><div><h1>團隊</h1>
  <p>每位成員的負載：出的題 / 協作 / 被指派出題 / 被指派驗題。</p></div></div>
<div class="container">
  <table class="table table-striped">
    <thead><tr><th>成員</th><th>出的題</th><th>協作</th><th>指派出題</th><th>指派驗題</th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td>{{ r.user.name }}{% if r.user.type == 'admin' %} <span class="badge badge-dark">admin</span>{% endif %}</td>
        <td>{{ r.owned|length }}{% if r.owned %} <small class="text-muted">{{ r.owned|join(', ') }}</small>{% endif %}</td>
        <td>{{ r.collab|length }}</td>
        <td>{{ r.as_author|length }}</td>
        <td>{{ r.as_review|length }}</td>
      </tr>
    {% else %}<tr><td colspan="5" class="text-center text-muted">沒有成員</td></tr>{% endfor %}
    </tbody>
  </table>
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.dashboard') }}">儀表板</a>
</div>
{% endblock %}
"""


@bp.route("/is1ab/team", methods=["GET"])
@authed_only
def team_page():
    return render_template_string(_TEAM_TMPL, rows=_team_overview())


# --------------------------------------------------------------------------- #
# load
# --------------------------------------------------------------------------- #

def load(app):
    try:
        register_plugin_assets_directory(app, base_path=f"/plugins/{PLUGIN_NAME}/assets/")
    except Exception:  # pragma: no cover
        pass

    app.register_blueprint(bp)
    register_admin_plugin_menu_bar(title="is1ab 儀表板", route="/is1ab/dashboard")
    register_admin_plugin_menu_bar(title="is1ab 出題", route="/is1ab")
    register_admin_plugin_menu_bar(title="is1ab 配額", route="/is1ab/quota")
    register_admin_plugin_menu_bar(title="is1ab 指派", route="/is1ab/assignments")
    register_admin_plugin_menu_bar(title="is1ab 團隊", route="/is1ab/team")
    # 前台主導覽（登入才可見）：儀表板 / 出題 / 我的題目 / 團隊
    register_user_page_menu_bar(title="儀表板", route="/is1ab/dashboard")
    register_user_page_menu_bar(title="出題", route="/is1ab")
    register_user_page_menu_bar(title="我的題目", route="/is1ab/mine")
    register_user_page_menu_bar(title="團隊", route="/is1ab/team")

    try:
        with app.app_context():
            db.create_all()
            # 輕量遷移：既有表補上後加的欄位（create_all 不會 ALTER 既有表）
            for stmt in ("ALTER TABLE is1ab_challenge_metadata ADD COLUMN dev_status_at DATETIME",):
                try:
                    db.session.execute(db.text(stmt))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
    except Exception as exc:  # pragma: no cover
        app.logger.warning("[%s] db.create_all skipped: %s", PLUGIN_NAME, exc)

    # admin 齒輪預設落地頁（/admin/statistics）導到我們的儀表板
    @app.before_request
    def _admin_landing():
        if request.method == "GET" and request.path == "/admin/statistics":
            return redirect("/is1ab/dashboard")

    # 藏掉用不到的導覽連結（CSS 注入，不動 CTFd 模板）
    @app.after_request
    def _hide_nav(resp):
        try:
            ctype = resp.content_type or ""
            if NAV_HIDE and ctype.startswith("text/html"):
                body = resp.get_data(as_text=True)
                if "</head>" in body:
                    css = "".join(f'a[href="{h}"]{{display:none!important}}' for h in NAV_HIDE)
                    resp.set_data(body.replace("</head>", f"<style>{css}</style></head>", 1))
        except Exception:  # pragma: no cover - 注入失敗不影響頁面
            pass
        return resp

    conv = "ok" if ctfd_convert else "MISSING"
    app.logger.info("[%s] plugin loaded (Phase 4 export; converter=%s)", PLUGIN_NAME, conv)
