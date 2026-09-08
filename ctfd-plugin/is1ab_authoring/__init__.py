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
import sys
import urllib.request
import uuid
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
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin

from . import vocab

# 分類/難度詞彙抽到 config.py（可後台增刪、對齊 challenge_schema）；狀態詞彙留此。
from .config import CATEGORIES, DIFFICULTIES  # noqa: E402
ASSIGN_STATUSES = ["unassigned", "assigned", "in_progress", "in_review", "done"]
# 題目「開發進度」的單一真相（Ⓑ）。與工單 status / CTFd state / ready_for_release 是不同概念。
DEV_STATUSES = ["planning", "developing", "testing", "completed", "deployed"]
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
    "/challenges", "/teams",
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


# 受控詞彙 helper 抽到 config.py（沿用 _categories/_difficulties 名稱給既有程式用）。
from .config import categories as _categories, difficulties as _difficulties  # noqa: E402


# 首次導引：CTFd 裝完後，admin 還沒設過類型/配額 → 全頁導覽時自動帶到「is1ab 設定」，
# 當作 setup 的延伸步驟。存/略過後 set is1ab_onboarded 就不再提示。
# 安全：fail-open（任何例外都放行）、不動核心 setup 精靈、不碰資產/API/認證路徑。
# 判斷邏輯在 vocab.should_onboard_redirect（純函式，可單元測試）。
def _onboard_redirect():
    try:
        if vocab.should_onboard_redirect(
            method=request.method,
            path=request.path,
            setup_done=bool(get_config("setup")),
            onboarded=bool(get_config("is1ab_onboarded")),
            is_admin=is_admin(),
        ):
            return redirect(url_for("is1ab_authoring.settings_page"))
    except Exception:                        # fail-open：絕不因此擋掉任何請求
        return


# --------------------------------------------------------------------------- #
# Model —— 定義已抽到 models.py（拆檔）；import 進來讓 db.create_all 建表、其餘程式沿用同名。
# --------------------------------------------------------------------------- #

from .models import (  # noqa: E402
    Assignment,
    ChallengeComment,
    ChallengeMetadata,
    ChallengeQuota,
)

# flag / tag 同步抽到 flags.py（純寫入 CTFd 原生表，沿用同名給既有程式用）。
from . import access, collaboration, review
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from .flags import _sync_flag, _sync_tags  # noqa: E402,F401

# 儀表板彙總抽到 dashboard.py（純讀取聚合，不 import __init__）；連同它獨用的
# _challenge_difficulty / _users_map / STALE_DAYS 一併搬過去，route 沿用同名 re-import。
from .dashboard import (  # noqa: E402,F401
    STALE_DAYS,
    _challenge_difficulty,
    _dashboard_matrix,
    _quota_data,
    _users_map,
)


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
    return access.can_edit(meta)


def _can_manage_acl(meta):
    """只有 admin 或 owner 能改協作者清單（避免協作者互相提權）。"""
    if is_admin():
        return True
    user = get_current_user()
    return bool(user and meta and access.has_role("author") and meta.owner_id == user.id)


def _sync_hints(challenge_id, hints_text, commit=True):
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
    db.session.commit() if commit else db.session.flush()


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
    mine = []
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
    # 工單只依明確 challenge_id 判斷是否已建立。
    for a in Assignment.query.filter_by(author_id=user_id).all():
        if a.challenge_id:
            continue
        mine.append({"id": None, "assignment_id": a.id, "name": a.title, "category": a.category,
                     "difficulty": a.difficulty, "dev_status": None,
                     "role": "指派待出", "built": False})
    to_review = [a for a in Assignment.query.all()
                 if str(user_id) in (a.reviewer_ids or "").split(",")]
    return mine, to_review


# --------------------------------------------------------------------------- #
# Views（@authed_only + 擁有權）
# --------------------------------------------------------------------------- #

bp = Blueprint(PLUGIN_NAME, __name__)


@bp.before_request
def _staff_only():
    if not access.roles_for(get_current_user()):
        abort(403, description="這是出題工作區，請由管理員授予工作角色。參賽者請使用正式比賽站。")


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
    <a class="btn btn-sm btn-outline-primary ml-2" href="{{ url_for('is1ab_authoring.challenge_view', challenge_id=challenge.id) }}">檢視題目 →</a></p>{% endif %}
</div></div>
<div class="container">
  {% if created %}<div class="alert alert-success">
    <strong>題目草稿已建立。</strong> 接著補齊內容並匯出題目檔案。正式試解、核准與上線尚未接通。</div>{% endif %}
  {% if saved %}<div class="alert alert-success">已儲存。</div>{% endif %}
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="nonce" value="{{ nonce }}">
    {% if challenge %}<input type="hidden" name="draft_version" value="{{ draft_version }}">{% endif %}
    {% if assignment %}<input type="hidden" name="assignment_id" value="{{ assignment.id }}"><input type="hidden" name="assignment_version" value="{{ assignment_version }}">{% endif %}
    <h4>題目內容</h4>
    <div class="form-row">
      <div class="form-group col-md-8"><label for="field-name">題名 *</label>
        <input id="field-name" class="form-control" name="name" value="{{ f.name }}" required></div>
      <div class="form-group col-md-4"><label for="field-category">分類 <small class="text-muted">建議用既有分類，否則不進儀表板配額格</small></label>
        <input id="field-category" class="form-control" name="category" value="{{ f.category }}" list="cat_list" placeholder="web / pwn / crypto …">
        <datalist id="cat_list">{% for c in categories %}<option value="{{ c }}">{% endfor %}</datalist></div>
    </div>
    <div class="form-row">
      <div class="form-group col-md-3"><label for="field-value">分數</label>
        <input id="field-value" class="form-control" type="number" name="value" value="{{ f.value }}"></div>
      <div class="form-group col-md-4"><label for="field-dev_status">開發進度（自行回報，不代表驗題通過）</label>
        <select id="field-dev_status" class="form-control" name="dev_status">
          {% for s in dev_statuses %}<option value="{{ s }}" {{ 'selected' if f.dev_status==s else '' }}>{{ (status_label.get(s) or [s])[0] }}</option>{% endfor %}
        </select></div>
      <div class="form-group col-md-5"><label for="field-tags">Tags（逗號分隔）</label>
        <input id="field-tags" class="form-control" name="tags" value="{{ f.tags }}"></div>
    </div>
    <div class="form-group"><label for="field-description">描述</label>
      <textarea id="field-description" class="form-control" name="description" rows="3">{{ f.description }}</textarea></div>
    <div class="form-row">
      <div class="form-group col-md-6"><label for="field-flag">Flag <small class="text-muted">格式 {{ flag_prefix }}{...}</small></label>
        <input id="field-flag" class="form-control" name="flag" value="{{ f.flag }}" placeholder="{{ flag_prefix }}{...}"></div>
      <div class="form-group col-md-2"><label for="field-flag_load">載入 <small class="text-muted">load</small></label>
        <select id="field-flag_load" class="form-control" name="flag_load">
          {% for s in flag_loads %}<option value="{{ s }}" {{ 'selected' if f.flag_load==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label for="field-flag_scope">範圍 <small class="text-muted">scope</small></label>
        <select id="field-flag_scope" class="form-control" name="flag_scope">
          {% for s in flag_scopes %}<option value="{{ s }}" {{ 'selected' if f.flag_scope==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label for="field-flag_match">比對 <small class="text-muted">match</small></label>
        <select id="field-flag_match" class="form-control" name="flag_match">
          {% for s in flag_matches %}<option value="{{ s }}" {{ 'selected' if f.flag_match==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
    </div>
    <small class="form-text text-muted mb-2">static/shared=經典內建統一 · dynamic=部署注入 · per_team=每隊唯一（隱含 dynamic） · regex=樣式比對</small>
    <div class="form-group"><label for="field-hints">Hints（每行 <code>cost|內容</code>）</label>
      <textarea id="field-hints" class="form-control" name="hints" rows="3" style="font-family:monospace">{{ f.hints }}</textarea></div>

    <h4 class="mt-4">詳細資訊 <small class="text-muted">（存匯出時，公開與敏感欄位由系統自動分流）</small></h4>
    <div class="form-row">
      <div class="form-group col-md-3"><label for="field-difficulty">難度</label>
        <select id="field-difficulty" class="form-control" name="difficulty"><option value="">—</option>
          {% for s in difficulties %}<option value="{{ s }}" {{ 'selected' if f.difficulty==s else '' }}>{{ s }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-3"><label for="field-deploy_type">交付方式</label>
        <select id="field-deploy_type" class="form-control" name="deploy_type">
          {% for t in deploy_types %}<option value="{{ t }}" {{ 'selected' if f.deploy_type==t else '' }}>{{ t or '—' }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-2"><label for="field-deploy_connection">連線 <small class="text-muted">container</small></label>
        <select id="field-deploy_connection" class="form-control" name="deploy_connection">
          {% for t in connection_types %}<option value="{{ t }}" {{ 'selected' if f.deploy_connection==t else '' }}>{{ t or '—' }}</option>{% endfor %}</select></div>
      <div class="form-group col-md-4"><label for="field-author">公開署名（不會變更題目擁有者）</label>
        <input id="field-author" class="form-control" name="author" value="{{ f.author }}"></div>
    </div>
    <details class="mb-3">
      <summary class="text-muted">更多欄位（選填，大多題不用填：發布旗標 / 附件 / 部署參數）</summary>
      <div class="mt-2 mb-2">
        <span class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="ready_for_release" id="rfr" {{ 'checked' if f.ready_for_release else '' }}><label class="form-check-label" for="rfr">作者自評可發布（待正式核准）</label></span>
        <span class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="source_code_provided" id="scp" {{ 'checked' if f.source_code_provided else '' }}><label class="form-check-label" for="scp">提供原始碼</label></span>
      </div>
      <div class="form-group"><label for="field-files">附件 files（一行一個）</label><textarea id="field-files" class="form-control" name="files" rows="2">{{ f.files }}</textarea></div>
      <h6 class="text-muted">部署資訊 deploy_info（container 題；port/nc_port 供 verify-solution 使用）</h6>
      <div class="form-row">
        <div class="form-group col-md-2"><label for="field-deploy_port">port</label><input id="field-deploy_port" class="form-control" name="deploy_port" value="{{ f.deploy_port }}"></div>
        <div class="form-group col-md-4"><label for="field-deploy_url">url</label><input id="field-deploy_url" class="form-control" name="deploy_url" value="{{ f.deploy_url }}"></div>
        <div class="form-group col-md-2"><label for="field-deploy_nc_port">nc_port</label><input id="field-deploy_nc_port" class="form-control" name="deploy_nc_port" value="{{ f.deploy_nc_port }}"></div>
        <div class="form-group col-md-2"><label for="field-deploy_memory">memory</label><input id="field-deploy_memory" class="form-control" name="deploy_memory" value="{{ f.deploy_memory }}"></div>
        <div class="form-group col-md-2"><label for="field-deploy_cpu">cpu</label><input id="field-deploy_cpu" class="form-control" name="deploy_cpu" value="{{ f.deploy_cpu }}"></div>
      </div>
      <div class="form-check mb-2"><input class="form-check-input" type="checkbox" name="deploy_requires_build" id="drb" {{ 'checked' if f.deploy_requires_build else '' }}><label class="form-check-label" for="drb">requires_build</label></div>
    </details>

    <div class="form-group"><label for="field-internal_notes">內部筆記 <small class="text-muted">（官方解 / 學習資訊 / 測試帳密請寫 writeup/README.md，不進此表單）</small></label>
      <textarea id="field-internal_notes" class="form-control" name="internal_notes" rows="3">{{ f.internal_notes }}</textarea></div>
    <details class="mb-3">
      <summary class="text-muted">更多（動態 flag / 驗題記錄）</summary>
      <div class="form-row mt-2">
        <div class="form-group col-md-6"><label for="field-dyn_template">dynamic_flag template</label><input id="field-dyn_template" class="form-control" name="dyn_template" value="{{ f.dyn_template }}"></div>
        <div class="form-group col-md-6"><label for="field-dyn_salt">dynamic_flag salt</label><input id="field-dyn_salt" class="form-control" name="dyn_salt" value="{{ f.dyn_salt }}"></div>
      </div>
      <div class="form-row">
        <div class="form-group col-md-6"><label for="field-test_by">作者記錄的測試人員</label><input id="field-test_by" class="form-control" name="test_by" value="{{ f.test_by }}"></div>
        <div class="form-group col-md-6"><label for="field-test_status">作者自填測試狀態（非正式驗題）</label><input id="field-test_status" class="form-control" name="test_status" value="{{ f.test_status }}"></div>
      </div>
    </details>
    <input type="hidden" name="passthrough" value="{{ f.passthrough }}">

    {% if challenge %}
    <h4 class="mt-4">權限</h4>
    <p class="text-muted">擁有者：{{ owner_name or '（未設）' }}</p>
    <div class="form-group"><fieldset><legend class="h6">協作者（可共同編輯）</legend><div class="d-flex flex-wrap" style="gap:1rem">
      {% for u in users %}<label><input type="checkbox" name="collaborators" value="{{ u.id }}" {{ 'checked' if (u.id|string) in f.collaborators else '' }} {{ 'disabled' if not can_manage else '' }}> {{ u.name }}</label>{% endfor %}
      </div></fieldset>
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
    return access.assignment_for(challenge_id)


def _reviewers_by_cid(metas_by_cid, umap):
    result = {}
    for a in Assignment.query.all():
        if a.challenge_id:
            result[a.challenge_id] = [umap[uid] for uid in sorted(access.ids(a.reviewer_ids)) if uid in umap]
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
        if not access.can_view(meta):
            continue
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
@access.require_roles("author")
def challenge_new():
    assignment = collaboration.creation_assignment()
    if assignment and assignment.challenge_id:
        return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=assignment.challenge_id))
    assignment_version = collaboration.plan_for(assignment).version if assignment else None
    if request.method == "POST":
        f = _form_from_request()
        blob, error = _fields_to_blob(f)
        if not f["name"]:
            error = "題名必填"
        try:
            if not 0 <= int(f["value"]) <= 2147483647:
                raise ValueError
        except (ValueError, TypeError):
            error = "分數須為 0 至 2147483647 的整數。"
        if error:
            return render_template_string(_FORM_TMPL, challenge=None, f=f, assignment=assignment, assignment_version=assignment_version,
                                          nonce=session.get("nonce", ""), error=error, saved=False,
                                          dev_statuses=DEV_STATUSES, difficulties=_difficulties(),
                                  categories=_categories(),
                                  status_label=DEV_STATUS_LABEL, flag_prefix=_flag_prefix(),
                                          deploy_types=DEPLOY_TYPES, connection_types=CONNECTION_TYPES,
                                  flag_loads=FLAG_LOADS, flag_scopes=FLAG_SCOPES, flag_matches=FLAG_MATCHES)
        chal = Challenges(name=f["name"], description=f["description"],
                          value=int(f["value"] or 0), category=f["category"],
                          state="hidden", type="standard")
        try:
            db.session.add(chal)
            db.session.flush()
            owner = get_current_user()
            meta = ChallengeMetadata(challenge_id=chal.id, owner_id=owner.id,
                uid=_new_uid(), repo_path=f"{_slugify(f['category'])}/{_slugify(f['name'])}",
                blob=blob, dev_status=f["dev_status"])
            db.session.add(meta)
            db.session.flush()
            access.remember_contributors(meta)
            access.draft_version(chal.id)
            collaboration.bind_created_challenge(assignment, chal.id)
            _sync_flag(chal.id, f["flag"], f["flag_match"], commit=False)
            _sync_tags(chal.id, f["tags"], commit=False)
            _sync_hints(chal.id, f["hints"], commit=False)
            db.session.commit()
        except (StaleDataError, IntegrityError):
            db.session.rollback()
            abort(409, description="工單已更新或已建立題目。請返回工單確認；此次沒有重複建立題目。")
        return redirect(url_for("is1ab_authoring.challenge_edit", challenge_id=chal.id, created=1))
    f = _form_defaults()
    if assignment:
        f.update(name=assignment.title, category=assignment.category, difficulty=assignment.difficulty)
    if request.args.get("category"):
        f["category"] = request.args.get("category").strip()
    if request.args.get("difficulty"):
        f["difficulty"] = request.args.get("difficulty").strip()
    return render_template_string(_FORM_TMPL, challenge=None, f=f, assignment=assignment, assignment_version=assignment_version,
                                  nonce=session.get("nonce", ""), error=None, saved=False,
                                  dev_statuses=DEV_STATUSES, difficulties=_difficulties(),
                                  categories=_categories(),
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

    revision = access.draft_version(challenge_id)
    db.session.commit()
    saved = False
    error = None
    code = 200
    if request.method == "POST":
        f = _form_from_request()
        blob, error = _fields_to_blob(f)
        if not f["name"]:
            error = "題名必填"
        try:
            if not 0 <= int(f["value"]) <= 2147483647:
                raise ValueError
        except (ValueError, TypeError):
            error = "分數須為 0 至 2147483647 的整數。"
        if _can_manage_acl(meta):
            selected = request.form.getlist("collaborators")
            allowed = {str(u.id) for u in access.eligible_users("author")}
            asg = _assignment_for(challenge_id)
            if not set(selected) <= allowed:
                error = "協作者必須是啟用中的出題成員。"
            elif asg and access.ids(",".join(selected)) & access.ids(asg.reviewer_ids):
                error = "本題驗題人不能同時加入協作；請先由 PM 協調指派。"
        if request.form.get("draft_version") != str(revision.version):
            error, code = "題目已由其他人更新。你的輸入已保留，請核對最新內容後再儲存。", 409
        if error is None:
            try:
                access.remember_contributors(meta)
                chal.name = f["name"] or chal.name
                chal.category = f["category"]
                chal.description = f["description"]
                chal.value = int(f["value"] or 0)
                db.session.flush()
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
                db.session.flush()
                # 只有 owner/admin 能改協作者清單（不信任表單，後端再判一次）
                if _can_manage_acl(meta):
                    meta.collaborators = ",".join(request.form.getlist("collaborators"))
                    access.remember_contributors(meta)
                    db.session.flush()
                _sync_flag(challenge_id, f["flag"], f["flag_match"], commit=False)
                _sync_tags(challenge_id, f["tags"], commit=False)
                _sync_hints(challenge_id, f["hints"], commit=False)
                revision.version += 1
                db.session.commit()
                saved = True

            except (StaleDataError, IntegrityError):
                db.session.rollback()
                error, code = "題目已由其他人更新。你的輸入已保留，請核對後再儲存。", 409

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
    f["collaborators"] = request.form.getlist("collaborators") if error and request.method == "POST" else _collaborator_ids(meta)
    owner = Users.query.filter_by(id=meta.owner_id).first() if (meta and meta.owner_id) else None
    return render_template_string(_FORM_TMPL, challenge=chal, f=f, draft_version=revision.version,
                                  nonce=session.get("nonce", ""), error=error, saved=saved,
                                  created=request.args.get("created"),
                                  dev_statuses=DEV_STATUSES, difficulties=_difficulties(),
                                  categories=_categories(),
                                  status_label=DEV_STATUS_LABEL, flag_prefix=_flag_prefix(),
                                  deploy_types=DEPLOY_TYPES, connection_types=CONNECTION_TYPES,
                                  flag_loads=FLAG_LOADS, flag_scopes=FLAG_SCOPES, flag_matches=FLAG_MATCHES,
                                  users=[u for u in access.eligible_users("author") if not _assignment_for(challenge_id) or u.id not in access.ids(_assignment_for(challenge_id).reviewer_ids)], can_manage=_can_manage_acl(meta),
                                  owner_name=(owner.name if owner else None)), code if code != 200 else (400 if error else 200)


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
# 依題目授權的檢視與討論
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
{% block content %}<div class="container my-4">
<h1>{{ v.name }}</h1><p>{{ v.category }}／{{ v.difficulty }} · 出題人：{{ v.author or '待確認' }}</p>
<nav class="d-flex flex-wrap mb-3" style="gap:.5rem">
<a class="btn btn-outline-primary" href="/is1ab/work">我的待辦</a>
{% if can_edit %}<a class="btn btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=v.id) }}">編輯題目</a>{% endif %}
{% if assignment %}<a class="btn btn-outline-primary" href="{{ url_for('is1ab_collaboration.detail', assignment_id=assignment.id) }}">查看工單與接案</a>{% endif %}</nav>
<div class="alert alert-secondary">此為製作中的題目。提案確認與手填開發進度不代表正式驗題通過；正式同版試解與上線功能尚未接通。</div>
<a class="btn btn-outline-primary mb-3" href="{{ url_for('is1ab_review.rounds',challenge_id=v.id) }}">送審與版本</a>
<h2 class="h5">題目描述</h2><div class="border rounded p-3" style="white-space:pre-wrap;overflow-wrap:anywhere">{{ v.description }}</div>
{% if can_edit %}
<h2 class="h5 mt-4">作者私有資料</h2><p>Flag：<code>{{ v.flag or '未設定' }}</code></p>
<pre style="white-space:pre-wrap">{{ v.internal_notes or '' }}</pre>
{% for f in src_files %}<details><summary>{{ f.path }}</summary><pre class="border p-2" style="overflow:auto">{{ f.text or '二進位／大檔案' }}</pre></details>{% endfor %}
{% endif %}

<h2 class="h5 mt-4">討論與回饋</h2><p class="text-muted">指定驗題人可閱讀討論，請勿貼出 flag 或官解。</p>
{% for c in comments %}<div class="border rounded p-2 mb-2"><strong>{{ c.name }}</strong> · {{ c.created_at }}<p style="white-space:pre-wrap;overflow-wrap:anywhere">{{ c.body }}</p></div>{% else %}<p>還沒有留言。</p>{% endfor %}
<form method="post" action="{{ url_for('is1ab_authoring.challenge_comment', challenge_id=v.id) }}">
<input type="hidden" name="nonce" value="{{ nonce }}"><label for="comment">留言</label><textarea id="comment" name="body" class="form-control mb-2" rows="3" maxlength="5000" required></textarea><button class="btn btn-primary">送出留言</button></form>
</div>{% endblock %}
"""


@bp.route("/is1ab/challenges/<int:challenge_id>/view", methods=["GET"])
@authed_only
def challenge_view(challenge_id):
    """Per-challenge scoped view; only current editors receive private materials."""
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = _get_meta(challenge_id)
    if not access.can_view(meta):
        abort(403)
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
        "flag": (fl.content if fl and _can_edit(meta) else None), "flag_type": (fl.type if fl else None),
        "flag_load": mf.get("flag_load"), "flag_scope": mf.get("flag_scope"),
        "internal_notes": mf.get("internal_notes") if _can_edit(meta) else None,
        "test_status": mf.get("test_status"), "tested_by": mf.get("test_by"),
    }
    # Private source is returned only to current editors.
    src_rel, src_files = _read_source(meta.repo_path if meta else None, True) if _can_edit(meta) else (None, [])
    asg = _assignment_for(challenge_id)
    return render_template_string(_VIEW_TMPL, v=view, comments=_comments_for(challenge_id),
        can_edit=_can_edit(meta), nonce=session.get("nonce", ""), src_files=src_files,
        assignment=asg, can_deploy=access.has_role("ops"))


@bp.route("/is1ab/challenges/<int:challenge_id>/comment", methods=["POST"])
@authed_only
def challenge_comment(challenge_id):
    if not access.can_view(_get_meta(challenge_id)):
        abort(403)
    """Only authorized participants can read and write discussion."""
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
    if not access.has_role("pm") or not access.can_view(_get_meta(challenge_id)):
        abort(403)
    abort(409, description="請由 PM 在工單指派，再由指定驗題人確認接案。")


@bp.route("/is1ab/challenges/<int:challenge_id>/review-me", methods=["POST"])
@authed_only
def challenge_review_me(challenge_id):
    if not access.has_role("reviewer") or not access.can_view(_get_meta(challenge_id)):
        abort(403)
    abort(409, description="請由 PM 在工單指派，再由指定驗題人確認接案。")


@bp.route("/is1ab/challenges/<int:challenge_id>/review-outcome", methods=["POST"])
@authed_only
def challenge_review_outcome(challenge_id):
    if not access.can_review(_get_meta(challenge_id)):
        abort(403)
    abort(409, description="正式驗題需要同版試解證據；此功能尚未接通。請先在題目頁留下回饋。")


# Legacy direct Docker execution is retired; verified runner deployment is a later stage.
@bp.route("/is1ab/challenges/<int:challenge_id>/deploy-files", methods=["POST"])
@bp.route("/is1ab/challenges/<int:challenge_id>/deploy", methods=["POST"])
@bp.route("/is1ab/challenges/<int:challenge_id>/deploy-down", methods=["POST"])
@authed_only
@access.require_roles("ops")
def legacy_deploy(challenge_id):
    abort(410, description="舊版直接部署已停用。獨立執行器與核准產物部署尚未接通。")


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



@bp.route("/is1ab/settings", methods=["GET", "POST"])
@admins_only
def settings_page():
    """類型 / 難度 受控詞彙的後台編輯（存進 CTFd config，隨時可改）。"""
    saved = reset = False
    if request.method == "POST":
        set_config("is1ab_onboarded", "1")   # 互動過 → 不再首次導引
        action = request.form.get("action")
        if action == "skip":
            return redirect("/admin")
        if action == "reset":
            set_config("is1ab_categories", None)
            set_config("is1ab_difficulties", None)
            reset = True
        else:
            cats = vocab.parse_vocab_input(request.form.get("categories", ""))
            diffs = vocab.parse_vocab_input(request.form.get("difficulties", ""))
            # 清空時不覆蓋（避免整個弄空）→ 存 None 讓它回退預設
            set_config("is1ab_categories",
                       json.dumps(cats, ensure_ascii=False) if cats else None)
            set_config("is1ab_difficulties",
                       json.dumps(diffs, ensure_ascii=False) if diffs else None)
            saved = True
    cats, diffs = _categories(), _difficulties()
    return render_template_string(
        _SETTINGS_TMPL,
        categories_text="\n".join(cats), difficulties_text="\n".join(diffs),
        default_categories=CATEGORIES, default_difficulties=DIFFICULTIES,
        nonce=session.get("nonce", ""), saved=saved, reset=reset)


@bp.route("/is1ab/quota", methods=["GET", "POST"])
@authed_only
@access.require_roles("pm")
def quota_page():
    saved = False
    if request.method == "POST":
        for cat in _categories():
            for diff in _difficulties():
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
                                  categories=_categories(), difficulties=_difficulties(),
                                  nonce=session.get("nonce", ""), saved=saved)


@bp.route("/is1ab/assignments", methods=["GET", "POST"])
@authed_only
@access.require_roles("pm")
def assignments_page():
    if request.method == "POST":
        abort(409, description="指派已移至工單，請重新開啟我的待辦／全場進度。")
    return redirect(url_for("is1ab_collaboration.work"))


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
            <a class="d-block mb-1 px-2 py-1 border rounded bg-light" href="{{ url_for('is1ab_collaboration.work') }}"><span class="text-info">{{ s.author }}</span> <small class="text-muted">未建 · 查看工單</small>{% if s.reviewers %}<br><small class="text-muted">驗:{{ s.reviewers|join(',') }}</small>{% endif %}</a>
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
      <td>{% if c.built %}<a class="btn btn-sm btn-primary" href="{{ url_for('is1ab_authoring.challenge_edit', challenge_id=c.id) }}">編輯</a>{% else %}<a class="btn btn-sm btn-outline-info" href="{{ url_for('is1ab_collaboration.detail', assignment_id=c.assignment_id) }}">查看工單</a>{% endif %}</td>
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
@access.require_roles("pm", "judge")
def dashboard():
    prs, pr_error = _open_prs()
    user = get_current_user()
    dash = _dashboard_matrix()
    return render_template_string(_DASH_TMPL, data=dash["grid"], summary=dash["summary"],
                                  uncategorized=dash["uncategorized"], stalled=dash["stalled"],
                                  categories=_categories(), difficulties=_difficulties(),
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
@access.require_roles("author")
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
                              state="hidden", type="standard")
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
@access.require_roles("pm", "judge")
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
    app.before_request(_onboard_redirect)   # 首次導引到「is1ab 設定」（裝完 setup 後）
    register_admin_plugin_menu_bar(title="is1ab 儀表板", route="/is1ab/dashboard")
    register_admin_plugin_menu_bar(title="is1ab 出題", route="/is1ab")
    register_admin_plugin_menu_bar(title="is1ab 配額", route="/is1ab/quota")
    register_admin_plugin_menu_bar(title="is1ab 設定", route="/is1ab/settings")
    register_admin_plugin_menu_bar(title="is1ab 指派", route="/is1ab/assignments")
    register_admin_plugin_menu_bar(title="is1ab 團隊", route="/is1ab/team")
    # 前台主導覽（登入才可見）：儀表板 / 出題 / 我的題目 / 團隊

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

    collaboration.initialize(app)
    review.initialize(app)
    register_user_page_menu_bar(title="我的待辦", route="/is1ab/work")
    register_admin_plugin_menu_bar(title="成員與角色", route="/is1ab/members")

    @app.before_request
    def _staging_native_boundary():
        if request.method == "GET" and request.path == "/" and not get_current_user():
            return redirect(url_for("auth.login"))
        if request.method == "GET" and request.path in ("/", "/challenges") and access.roles_for(get_current_user()):
            return redirect(url_for("is1ab_collaboration.work"))
        protected = ("/challenges", "/api/v1/challenges", "/api/v1/files", "/files")
        if any(request.path == p or request.path.startswith(p + "/") for p in protected) and not is_admin():
            abort(403, description="出題站請使用我的待辦；原生題目、試解與附件入口尚未開放。")

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
    app.logger.info("[%s] plugin loaded (staff collaboration; converter=%s)", PLUGIN_NAME, conv)
