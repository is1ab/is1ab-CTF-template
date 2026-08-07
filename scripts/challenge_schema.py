"""題目 schema 讀取 helper —— 新 canonical 與舊 schema 相容。

canonical 定義見 docs/challenge-schema.md。新舊對應：
- deploy_type(attachment|container|none) 取代 challenge_type(5 值)；nc 收進 connection_type
- flag_load/flag_scope/flag_match 取代 flag_type(static|dynamic|regex)
- author 取代 owners/assignee

所有 getter 皆「新欄位優先、缺則由舊欄位推導」，讓遷移期間新舊題目都讀得動。
"""

_LEGACY_ATTACH = {"static_attachment", "dynamic_attachment"}
_LEGACY_CONTAINER = {"static_container", "dynamic_container", "nc_challenge"}

_DIFFICULTY_ALIASES = {"medium": "middle", "mid": "middle"}


def deploy_type(public: dict) -> str:
    """attachment | container | none（新欄位優先，舊 challenge_type 推導）。"""
    dt = str(public.get("deploy_type") or "").strip().lower()
    if dt in ("attachment", "container", "none"):
        return dt
    legacy = str(public.get("challenge_type") or "").strip().lower()
    if legacy in _LEGACY_CONTAINER:
        return "container"
    if legacy in _LEGACY_ATTACH:
        return "attachment"
    return "attachment"


def connection_type(public: dict) -> str:
    """nc | http | https | ''（玩家怎麼連）。"""
    return str((public.get("deploy_info") or {}).get("connection_type") or "").strip().lower()


def is_nc(public: dict) -> bool:
    """nc 連線題：新 = container + connection_type=nc；舊 = challenge_type=nc_challenge。"""
    legacy = str(public.get("challenge_type") or "").strip().lower()
    return legacy == "nc_challenge" or (
        deploy_type(public) == "container" and connection_type(public) == "nc"
    )


def has_service(public: dict) -> bool:
    """是否要起服務（container 類需要；attachment/none 不用）。"""
    return deploy_type(public) == "container"


def kind(public: dict) -> str:
    """顯示用歸類：nc | container | attachment | none。"""
    if is_nc(public):
        return "nc"
    return deploy_type(public)


def flag_axes(private: dict):
    """(load, scope, match)：新欄位優先，舊 flag_type 推導。"""
    legacy = str(private.get("flag_type") or "").strip().lower()
    load = str(private.get("flag_load") or ("dynamic" if legacy == "dynamic" else "static")).strip().lower()
    scope = str(private.get("flag_scope") or ("per_team" if legacy == "dynamic" else "shared")).strip().lower()
    match = str(private.get("flag_match") or ("regex" if legacy == "regex" else "exact")).strip().lower()
    return load, scope, match


def ctfd_flag_type(private: dict) -> str:
    """CTFd flag type：regex 比對→regex，否則 static。"""
    _, _, match = flag_axes(private)
    return "regex" if match == "regex" else "static"


def needs_static_flag(private: dict) -> bool:
    """要不要在 CTFd 建靜態 flag：per_team（每隊注入）就不建。"""
    _, scope, _ = flag_axes(private)
    return scope != "per_team"


def authors(public: dict):
    """(owners:list[str], assignee:str)：以 author 為單一來源，相容舊 owners/assignee。"""
    author = str(public.get("author") or "").strip()
    owners = public.get("owners")
    if owners:
        owners = [str(x).strip() for x in owners if str(x).strip()]
    else:
        owners = [author] if author else []
    assignee = str(public.get("assignee") or author or "").strip()
    return owners, assignee


def difficulty(public: dict) -> str:
    """正規化難度（medium→middle，小寫）。"""
    d = str(public.get("difficulty") or "").strip().lower()
    return _DIFFICULTY_ALIASES.get(d, d)


def category(public: dict) -> str:
    """正規化分類（小寫；自由填寫）。"""
    return str(public.get("category") or "").strip().lower()
