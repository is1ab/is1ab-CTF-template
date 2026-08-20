"""is1ab_authoring 的純邏輯（不依賴 CTFd / Flask），方便在 repo CI 直接單元測試。

這裡只放「輸入 → 輸出」的決定性函式：
- 受控詞彙（類型/難度）的 config 解析與後台輸入解析
- 首次導引（onboarding redirect）的判斷

__init__.py 負責把 CTFd/Flask 的東西（get_config / request / is_admin）餵進來。
"""

from __future__ import annotations

import json

# 首次導引時「不攔、放行」的路徑前綴（資產/API/認證/外掛自身/安裝精靈）。
ONBOARD_SKIP_PREFIX = (
    "/is1ab", "/themes", "/files", "/plugins", "/api", "/setup",
    "/login", "/logout", "/register", "/reset_password", "/confirm",
)


def parse_vocab(raw, default):
    """把 CTFd config 存的 JSON list 字串解析成清單；沒設/壞掉/空→回 default。

    去空白、去重、保序。default 會被複製一份回傳（呼叫端可安全修改）。
    """
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, list):
                cleaned = list(dict.fromkeys(
                    str(x).strip() for x in v if str(x).strip()))
                if cleaned:
                    return cleaned
        except Exception:
            pass
    return list(default)


def parse_vocab_input(raw):
    """後台設定頁的 textarea 輸入 → 清單（逗號或換行分隔、去空白、去重、保序）。"""
    items = [x.strip() for x in str(raw or "").replace(",", "\n").splitlines()]
    return list(dict.fromkeys(x for x in items if x))


def should_onboard_redirect(method, path, setup_done, onboarded, is_admin,
                            skip_prefixes=ONBOARD_SKIP_PREFIX):
    """要不要把這個請求導去「is1ab 設定」做首次導引。

    只在「admin + 已裝完 setup + 尚未 onboarded + GET 全頁導覽（非資產/API/認證等）」時 True。
    """
    if method != "GET":
        return False
    if not setup_done:            # setup 精靈本身不碰
        return False
    if onboarded:                 # 已設/略過過
        return False
    if not is_admin:              # 只導 admin
        return False
    p = path or "/"
    if any(p.startswith(prefix) for prefix in skip_prefixes):
        return False
    return True
