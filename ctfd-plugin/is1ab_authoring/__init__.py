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

import json
import os
import re
import sys
import urllib.request
import uuid

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
CATEGORIES = ["web", "pwn", "reverse", "crypto", "forensic", "misc", "general"]
DIFFICULTIES = ["baby", "easy", "middle", "hard", "impossible"]
ASSIGN_STATUSES = ["unassigned", "assigned", "in_progress", "in_review", "done"]
# 題目「開發進度」的單一真相（Ⓑ）。與工單 status / CTFd state / ready_for_release 是不同概念。
DEV_STATUSES = ["planning", "developing", "testing", "completed", "deployed"]
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
    uid = db.Column(db.String(16), nullable=True)        # Ⓓ 隱形亂碼綁定鍵
    repo_path = db.Column(db.String(255), nullable=True)  # Ⓓ 可讀目錄 <cat>/<slug>
    blob = db.Column("metadata_yaml", db.Text, default="")

    def __init__(self, challenge_id, owner_id=None, uid=None, repo_path=None, blob="",
                 collaborators="", dev_status="developing"):
        self.challenge_id = challenge_id
        self.owner_id = owner_id
        self.collaborators = collaborators
        self.dev_status = dev_status
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
    owner_by_cid = {m.challenge_id: m.owner_id for m in ChallengeMetadata.query.all()}

    chal_cell = {cat: {d: [] for d in DIFFICULTIES} for cat in CATEGORIES}
    for c in Challenges.query.order_by(Challenges.id).all():
        cat, diff = (c.category or ""), _challenge_difficulty(c.id)
        if cat in chal_cell and diff in chal_cell[cat]:
            chal_cell[cat][diff].append(c)

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
                slots.append({"author": umap.get(a.author_id), "author_id": a.author_id,
                              "reviewers": [umap.get(int(x)) for x in (a.reviewer_ids or "").split(",") if x],
                              "cid": chal.id if chal else None,
                              "cname": chal.name if chal else None})
            for c in chal_cell[cat][d]:                     # 再放沒對應指派的題
                if c.id not in linked:
                    slots.append({"author": None, "author_id": None, "reviewers": [], "cid": c.id, "cname": c.name})
            while len(slots) < target:                      # 補滿到配額數 → 缺
                slots.append({"author": None, "author_id": None, "reviewers": [], "cid": None, "cname": None})
            data[cat][d] = {"slots": slots, "target": target}
    return data


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
    """回傳 (我出/協作的題, 指派給我出的工單, 指派給我驗的工單)。"""
    my_challenges = []
    for m in ChallengeMetadata.query.all():
        if m.owner_id == user_id or str(user_id) in _collaborator_ids(m):
            chal = Challenges.query.filter_by(id=m.challenge_id).first()
            if chal:
                my_challenges.append({
                    "id": chal.id, "name": chal.name,
                    "role": "owner" if m.owner_id == user_id else "collaborator",
                })
    to_author = Assignment.query.filter_by(author_id=user_id).all()
    to_review = [a for a in Assignment.query.all()
                 if str(user_id) in (a.reviewer_ids or "").split(",")]
    return my_challenges, to_author, to_review


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
    <thead><tr><th>ID</th><th>題目</th><th>分類</th><th>分數</th><th>狀態</th><th>詳細</th><th></th></tr></thead>
    <tbody>
    {% for c in rows %}
      <tr>
        <td>{{ c.id }}</td><td>{{ c.name }}</td><td>{{ c.category }}</td>
        <td>{{ c.value }}</td><td>{{ c.state }}</td>
        <td>{% if c.has_meta %}<span class="badge badge-success">已填</span>{% else %}<span class="badge badge-secondary">未填</span>{% endif %}</td>
        <td>
          {% if c.can_edit %}<a class="btn btn-sm btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=c.id) }}">編輯</a>{% endif %}
          <a class="btn btn-sm btn-outline-info" href="{{ url_for('is1ab_authoring.challenge_export', challenge_id=c.id) }}">匯出</a>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="7" class="text-center text-muted">還沒有題目。點右上「新增題目」。</td></tr>
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
  {% if challenge %}<p class="text-muted">#{{ challenge.id }}</p>{% endif %}
</div></div>
<div class="container">
  {% if saved %}<div class="alert alert-success">已儲存。</div>{% endif %}
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    <h4>原生欄位（CTFd）</h4>
    <div class="form-row">
      <div class="form-group col-md-8"><label>題名 *</label>
        <input class="form-control" name="name" value="{{ f.name }}" required></div>
      <div class="form-group col-md-4"><label>分類</label>
        <input class="form-control" name="category" value="{{ f.category }}"></div>
    </div>
    <div class="form-row">
      <div class="form-group col-md-3"><label>分數</label>
        <input class="form-control" type="number" name="value" value="{{ f.value }}"></div>
      <div class="form-group col-md-4"><label>開發進度</label>
        <select class="form-control" name="dev_status">
          {% for s in dev_statuses %}<option value="{{ s }}" {{ 'selected' if f.dev_status==s else '' }}>{{ s }}</option>{% endfor %}
        </select></div>
      <div class="form-group col-md-5"><label>Tags（逗號分隔）</label>
        <input class="form-control" name="tags" value="{{ f.tags }}"></div>
    </div>
    <div class="form-group"><label>描述</label>
      <textarea class="form-control" name="description" rows="3">{{ f.description }}</textarea></div>
    <div class="form-row">
      <div class="form-group col-md-6"><label>Flag</label>
        <input class="form-control" name="flag" value="{{ f.flag }}"></div>
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
      <summary class="text-muted">更多欄位（選填，大多題不用填：發布旗標 / 學習資訊 / 部署 / metadata）</summary>
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
        "name": g("name", "").strip(), "category": g("category", "").strip(),
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


@bp.route("/is1ab", methods=["GET"])
@authed_only
def challenge_list():
    metas = {m.challenge_id: m for m in ChallengeMetadata.query.all()}
    rows = []
    for c in Challenges.query.order_by(Challenges.id).all():
        meta = metas.get(c.id)
        rows.append(type("Row", (), {
            "id": c.id, "name": c.name, "category": c.category,
            "value": c.value, "state": c.state,
            "has_meta": meta is not None,
            "can_edit": _can_edit(meta),  # meta None → 僅 admin（不再對所有人開放）
        }))
    return render_template_string(_LIST_TMPL, rows=rows)


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
        return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=chal.id))
    f = _form_defaults()
    if request.args.get("category"):
        f["category"] = request.args.get("category").strip()
    if request.args.get("difficulty"):
        f["difficulty"] = request.args.get("difficulty").strip()
    return render_template_string(_FORM_TMPL, challenge=None, f=f,
                                  nonce=session.get("nonce", ""), error=None, saved=False,
                                  dev_statuses=DEV_STATUSES, difficulties=DIFFICULTIES,
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
                                  dev_statuses=DEV_STATUSES, difficulties=DIFFICULTIES,
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
    <thead><tr><th>#</th><th>分類/難度</th><th>出題者</th><th>驗題者</th><th>對應題目</th><th></th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td>{{ r.a.id }}</td><td>{{ r.a.category }}/{{ r.a.difficulty }}</td>
        <td>{{ r.author }}</td><td>{{ r.reviewers }}</td>
        <td>{% if r.a.challenge_id %}#{{ r.a.challenge_id }}{% else %}<span class="text-muted">未建</span>{% endif %}</td>
        <td><form method="POST" onsubmit="return confirm('刪除工單？')">
          <input type="hidden" name="nonce" value="{{ nonce }}">
          <input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ r.a.id }}">
          <button class="btn btn-sm btn-outline-danger">刪</button></form></td>
      </tr>
    {% else %}<tr><td colspan="6" class="text-center text-muted">還沒有工單。</td></tr>{% endfor %}
    </tbody>
  </table>
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
    rows = []
    for a in Assignment.query.order_by(Assignment.id).all():
        rows.append({
            "a": a,
            "author": umap.get(a.author_id, "—"),
            "reviewers": ", ".join(umap.get(int(x), x) for x in (a.reviewer_ids or "").split(",") if x),
        })
    return render_template_string(_ASSIGN_TMPL, rows=rows, users=Users.query.all(),
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
  <h4>題目分布（配額幾題就幾個位；點方格進題目）</h4>
  <table class="table table-bordered">
    <thead><tr><th>分類 \\ 難度</th>{% for d in difficulties %}<th class="text-center">{{ d }}</th>{% endfor %}</tr></thead>
    <tbody>{% for cat in categories %}<tr><th class="align-middle">{{ cat }}</th>
      {% for d in difficulties %}{% set cell = data[cat][d] %}
      <td style="vertical-align:top">
        {% for s in cell.slots %}
          {% if s.cid %}
          <a class="d-block mb-1 px-2 py-1 border rounded" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=s.cid) }}">{{ s.cname }}{% if s.author %} <small class="text-muted">（{{ s.author }}）</small>{% endif %}{% if s.reviewers %}<br><small class="text-muted">驗:{{ s.reviewers|join(',') }}</small>{% endif %}</a>
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
  <h4>我出 / 協作的題</h4>
  <table class="table table-sm table-striped"><thead><tr><th>#</th><th>題目</th><th>角色</th><th></th></tr></thead>
  <tbody>{% for c in mine %}<tr><td>{{ c.id }}</td><td>{{ c.name }}</td><td>{{ c.role }}</td>
    <td><a class="btn btn-sm btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=c.id) }}">編輯</a></td></tr>
  {% else %}<tr><td colspan="4" class="text-muted text-center">還沒有</td></tr>{% endfor %}</tbody></table>

  <h4 class="mt-4">指派給我「出題」</h4>
  <table class="table table-sm"><thead><tr><th>#</th><th>標題</th><th>分類/難度</th><th>對應題目</th><th>狀態</th></tr></thead>
  <tbody>{% for a in to_author %}<tr><td>{{ a.id }}</td><td>{{ a.title }}</td><td>{{ a.category }}/{{ a.difficulty }}</td>
    <td>{% if a.challenge_id %}#{{ a.challenge_id }}{% else %}<span class="badge badge-warning">尚未建題</span>{% endif %}</td>
    <td>{{ a.status }}</td></tr>{% else %}<tr><td colspan="5" class="text-muted text-center">沒有</td></tr>{% endfor %}</tbody></table>

  <h4 class="mt-4">指派給我「驗題」</h4>
  <table class="table table-sm"><thead><tr><th>#</th><th>標題</th><th>對應題目</th><th>狀態</th></tr></thead>
  <tbody>{% for a in to_review %}<tr><td>{{ a.id }}</td><td>{{ a.title }}</td>
    <td>{% if a.challenge_id %}#{{ a.challenge_id }}{% else %}—{% endif %}</td><td>{{ a.status }}</td></tr>
  {% else %}<tr><td colspan="4" class="text-muted text-center">沒有</td></tr>{% endfor %}</tbody></table>
  <a class="btn btn-secondary" href="{{ url_for('is1ab_authoring.dashboard') }}">儀表板</a>
</div>
{% endblock %}
"""


@bp.route("/is1ab/dashboard", methods=["GET"])
@authed_only
def dashboard():
    prs, pr_error = _open_prs()
    user = get_current_user()
    return render_template_string(_DASH_TMPL, data=_dashboard_matrix(),
                                  categories=CATEGORIES, difficulties=DIFFICULTIES,
                                  prs=prs, pr_error=pr_error,
                                  show_admin=is_admin(), me=(user.id if user else None))


@bp.route("/is1ab/mine", methods=["GET"])
@authed_only
def my_page():
    user = get_current_user()
    mine, to_author, to_review = _my_stuff(user.id) if user else ([], [], [])
    return render_template_string(_MINE_TMPL, mine=mine, to_author=to_author, to_review=to_review)


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
            return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=chal.id))
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
