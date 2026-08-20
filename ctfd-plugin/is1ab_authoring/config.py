"""is1ab_authoring 的受控詞彙 config（拆檔第三步）。

類型/難度的預設對齊 repo 單一真相 challenge_schema（掛 /repo 時），沒掛用內建 fallback；
實際清單可在後台「is1ab 設定」頁增刪、存進 CTFd config 覆蓋（`is1ab_categories` /
`is1ab_difficulties`）。抽成獨立模組是為了讓 dashboard/routes 之後能引用而不必回頭 import
__init__（避免循環）。自帶 /repo/scripts 的 sys.path 保險，import 順序無關。
"""

from __future__ import annotations

import sys

from CTFd.utils import get_config

from . import vocab

DEFAULT_CATEGORIES = ["web", "pwn", "reverse", "crypto", "forensic", "misc", "osint", "general"]
DEFAULT_DIFFICULTIES = ["baby", "easy", "middle", "hard", "impossible"]

# 對齊 repo 單一真相；沒掛 /repo 或 import 失敗 → 用上面 fallback。
_CONV_PATH = "/repo/scripts"
if _CONV_PATH not in sys.path:
    sys.path.insert(0, _CONV_PATH)
try:
    import challenge_schema as _cs
    CATEGORIES = list(_cs.SUGGESTED_CATEGORIES)
    DIFFICULTIES = list(_cs.DIFFICULTIES)
except Exception:  # pragma: no cover - 沒掛 repo 時仍可用 fallback
    CATEGORIES = list(DEFAULT_CATEGORIES)
    DIFFICULTIES = list(DEFAULT_DIFFICULTIES)


def get_vocab(config_key, default):
    """讀 CTFd config 的 JSON list；沒設/壞掉→回 default（純解析在 vocab.parse_vocab）。"""
    return vocab.parse_vocab(get_config(config_key), default)


def categories():
    return get_vocab("is1ab_categories", CATEGORIES)


def difficulties():
    return get_vocab("is1ab_difficulties", DIFFICULTIES)
