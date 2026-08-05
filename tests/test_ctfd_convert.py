"""Tests for scripts/ctfd_convert.py（CTFd → public/private.yml 轉換）。"""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location(
        "ctfd_convert", str(SCRIPTS_DIR / "ctfd_convert.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def cc():
    return _load()


# --------------------------------------------------------------------------- #
# 原生欄位對應
# --------------------------------------------------------------------------- #

def test_native_fields_map_to_public(cc):
    challenge = {
        "name": "SQL Injection 101",
        "category": "web",
        "description": "try union select",
        "value": 100,
    }
    public, private = cc.ctfd_to_challenge(challenge)
    assert public["title"] == "SQL Injection 101"
    assert public["category"] == "web"
    assert public["description"] == "try union select"
    assert public["points"] == 100
    assert private == {}


def test_missing_value_omits_points(cc):
    public, _ = cc.ctfd_to_challenge({"name": "x", "category": "misc"})
    assert "points" not in public


# --------------------------------------------------------------------------- #
# tags / hints / files
# --------------------------------------------------------------------------- #

def test_tags_accepts_dicts_and_strings(cc):
    _, _ = cc.ctfd_to_challenge({"name": "x"})  # smoke
    assert cc.normalize_tags([{"value": "web"}, "sql", {"value": " "}, None]) == ["web", "sql"]


def test_hints_ordered_with_level_and_cost(cc):
    hints = [
        {"content": "first", "cost": 0},
        {"content": "  ", "cost": 5},   # 空內容略過
        {"content": "second", "cost": 25},
    ]
    public, _ = cc.ctfd_to_challenge({"name": "x"}, hints=hints)
    assert public["hints"] == [
        {"level": 1, "cost": 0, "content": "first"},
        {"level": 2, "cost": 25, "content": "second"},
    ]


def test_files_filtered_and_included(cc):
    public, _ = cc.ctfd_to_challenge({"name": "x"}, files=["a.zip", "", "b.tar.gz"])
    assert public["files"] == ["a.zip", "b.tar.gz"]


def test_empty_optional_fields_omitted(cc):
    public, _ = cc.ctfd_to_challenge({"name": "x"}, tags=[], hints=[], files=[])
    for key in ("tags", "hints", "files"):
        assert key not in public


# --------------------------------------------------------------------------- #
# flags → private
# --------------------------------------------------------------------------- #

def test_static_flag_to_private(cc):
    _, private = cc.ctfd_to_challenge(
        {"name": "x"}, flags=[{"content": "is1abCTF{real}", "type": "static"}]
    )
    assert private["flag"] == "is1abCTF{real}"
    assert private["flag_type"] == "static"


def test_regex_flag_type_preserved(cc):
    _, private = cc.ctfd_to_challenge(
        {"name": "x"}, flags=[{"content": "is1abCTF{.*}", "type": "regex"}]
    )
    assert private["flag_type"] == "regex"


def test_unknown_flag_type_falls_back_to_static(cc):
    _, private = cc.ctfd_to_challenge(
        {"name": "x"}, flags=[{"content": "f", "type": "weird"}]
    )
    assert private["flag_type"] == "static"


def test_no_flag_leaves_private_without_flag(cc):
    _, private = cc.ctfd_to_challenge({"name": "x"}, flags=[])
    assert "flag" not in private
    assert "flag_type" not in private


def test_ctfd_flag_overrides_blob_flag_type(cc):
    # blob 帶了 dynamic，但 CTFd 有實際 static flag → 以 CTFd 為準
    _, private = cc.ctfd_to_challenge(
        {"name": "x"},
        flags=[{"content": "f", "type": "static"}],
        metadata={"flag_type": "dynamic"},
    )
    assert private["flag"] == "f"
    assert private["flag_type"] == "static"


# --------------------------------------------------------------------------- #
# metadata blob 分流
# --------------------------------------------------------------------------- #

def test_sensitive_metadata_routed_to_private(cc):
    metadata = {
        "solution_steps": [{"step": 1, "title": "t"}],
        "internal_notes": "secret notes",
        "test_credentials": {"admin": {"password": "p"}},
        "deploy_secrets": {"secret_key": "k"},
    }
    public, private = cc.ctfd_to_challenge({"name": "x"}, metadata=metadata)
    for key in metadata:
        assert key in private
        assert key not in public


def test_public_metadata_routed_to_public(cc):
    metadata = {
        "author": "Alice",
        "difficulty": "easy",
        "learning_objectives": ["obj1"],
        "deploy_info": {"port": 8080},
    }
    public, private = cc.ctfd_to_challenge({"name": "x"}, metadata=metadata)
    for key in metadata:
        assert key in public
        assert key not in private


def test_unknown_metadata_key_failsafe_to_private(cc):
    public, private = cc.ctfd_to_challenge(
        {"name": "x"}, metadata={"some_new_field": "value"}
    )
    assert private["some_new_field"] == "value"
    assert "some_new_field" not in public


def test_split_metadata_direct(cc):
    pub, priv = cc.split_metadata({
        "author": "A",          # public
        "flag": "secret",       # sensitive → private
        "mystery": 1,           # unknown → private
    })
    assert pub == {"author": "A"}
    assert priv == {"flag": "secret", "mystery": 1}


# --------------------------------------------------------------------------- #
# challenge_to_ctfd（逆轉）與 round-trip
# --------------------------------------------------------------------------- #

def test_challenge_to_ctfd_native_and_flag(cc):
    public = {"id": "abc123", "title": "T", "category": "web",
              "description": "d", "points": 200,
              "tags": ["web", "sqli"],
              "hints": [{"level": 1, "cost": 0, "content": "h1"}]}
    private = {"flag": "is1abCTF{x}", "flag_type": "static", "internal_notes": "n"}
    out = cc.challenge_to_ctfd(public, private)
    assert out["name"] == "T" and out["category"] == "web"
    assert out["value"] == 200 and out["uid"] == "abc123"
    assert out["tags"] == ["web", "sqli"]
    assert out["hints"] == [{"content": "h1", "cost": 0}]
    assert out["flag"] == "is1abCTF{x}" and out["flag_type"] == "static"


def test_challenge_to_ctfd_blob_excludes_native_and_flag(cc):
    public = {"title": "T", "author": "Alice", "difficulty": "hard"}
    private = {"flag": "f", "flag_type": "static", "internal_notes": "secret",
               "solution_steps": [{"step": 1}]}
    out = cc.challenge_to_ctfd(public, private)
    # 原生欄位與 flag/flag_type 不進 blob
    assert "title" not in out["blob"] and "flag" not in out["blob"] and "flag_type" not in out["blob"]
    # 富欄位（public 非原生 + private 敏感）進 blob
    assert out["blob"]["author"] == "Alice"
    assert out["blob"]["difficulty"] == "hard"
    assert out["blob"]["internal_notes"] == "secret"
    assert out["blob"]["solution_steps"] == [{"step": 1}]


def test_roundtrip_repo_to_ctfd_and_back(cc):
    """public/private → challenge_to_ctfd →（餵回）ctfd_to_challenge → 還原關鍵欄位。"""
    public0 = {"id": "uid00001", "title": "RT", "category": "crypto", "points": 300,
               "tags": ["crypto"], "hints": [{"level": 1, "cost": 10, "content": "hint"}],
               "author": "Bob", "difficulty": "middle", "learning_objectives": ["o1"]}
    private0 = {"flag": "is1abCTF{rt}", "flag_type": "static",
                "internal_notes": "notes", "solution_steps": [{"step": 1, "title": "t"}]}

    c = cc.challenge_to_ctfd(public0, private0)
    challenge = {"name": c["name"], "category": c["category"],
                 "description": c["description"], "value": c["value"]}
    flags = [{"content": c["flag"], "type": c["flag_type"]}] if c["flag"] else []
    public1, private1 = cc.ctfd_to_challenge(
        challenge, flags=flags, hints=c["hints"], tags=c["tags"], metadata=c["blob"])

    assert public1["title"] == "RT" and public1["category"] == "crypto"
    assert public1["points"] == 300 and public1["tags"] == ["crypto"]
    assert public1["author"] == "Bob" and public1["difficulty"] == "middle"
    assert public1["learning_objectives"] == ["o1"]
    assert private1["flag"] == "is1abCTF{rt}" and private1["flag_type"] == "static"
    assert private1["internal_notes"] == "notes"
    assert private1["solution_steps"] == [{"step": 1, "title": "t"}]
