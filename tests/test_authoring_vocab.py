"""is1ab_authoring.vocab 純邏輯單元測試。

vocab.py 是刻意抽出來、不依賴 CTFd 的模組，所以直接用 importlib 載入檔案
（繞過會 import CTFd 的 package __init__.py），在 repo CI 就能跑。
"""

import importlib.util
import pathlib

_VOCAB_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "ctfd-plugin" / "is1ab_authoring" / "vocab.py"
)
_spec = importlib.util.spec_from_file_location("is1ab_authoring_vocab", _VOCAB_PATH)
vocab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vocab)


DEF = ["a", "b", "c"]


# ── parse_vocab（config JSON → 清單）─────────────────────────────────────
def test_parse_vocab_valid_json():
    assert vocab.parse_vocab('["web","pwn"]', DEF) == ["web", "pwn"]


def test_parse_vocab_none_or_empty_falls_back():
    assert vocab.parse_vocab(None, DEF) == DEF
    assert vocab.parse_vocab("", DEF) == DEF
    assert vocab.parse_vocab("[]", DEF) == DEF          # 空 list → default


def test_parse_vocab_bad_json_falls_back():
    assert vocab.parse_vocab("not json", DEF) == DEF
    assert vocab.parse_vocab('{"a": 1}', DEF) == DEF    # 非 list → default


def test_parse_vocab_cleans_whitespace_dupes_order():
    assert vocab.parse_vocab('[" web ","pwn","web",""," "]', DEF) == ["web", "pwn"]


def test_parse_vocab_returns_copy_of_default():
    out = vocab.parse_vocab(None, DEF)
    out.append("x")
    assert DEF == ["a", "b", "c"]                       # default 未被汙染


# ── parse_vocab_input（後台 textarea → 清單）────────────────────────────
def test_parse_vocab_input_comma_and_newline():
    assert vocab.parse_vocab_input("web, pwn\ncrypto") == ["web", "pwn", "crypto"]


def test_parse_vocab_input_dedup_order_empty():
    assert vocab.parse_vocab_input(" web \n web \n\n pwn ") == ["web", "pwn"]
    assert vocab.parse_vocab_input("") == []
    assert vocab.parse_vocab_input(None) == []


# ── should_onboard_redirect（首次導引判斷）──────────────────────────────
def _decide(**kw):
    base = dict(method="GET", path="/admin", setup_done=True,
                onboarded=False, is_admin=True)
    base.update(kw)
    return vocab.should_onboard_redirect(**base)


def test_onboard_happy_path_true():
    assert _decide() is True


def test_onboard_false_when_not_get():
    assert _decide(method="POST") is False


def test_onboard_false_when_setup_not_done():
    assert _decide(setup_done=False) is False


def test_onboard_false_when_onboarded():
    assert _decide(onboarded=True) is False


def test_onboard_false_when_not_admin():
    assert _decide(is_admin=False) is False


def test_onboard_false_on_skip_prefixes():
    for p in ("/is1ab/settings", "/api/v1/x", "/themes/y", "/setup", "/login", "/files/z"):
        assert _decide(path=p) is False


def test_onboard_true_on_normal_admin_pages():
    assert _decide(path="/admin/config") is True
    assert _decide(path="/challenges") is True
