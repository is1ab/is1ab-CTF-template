#!/usr/bin/env python3
"""
CTFd ↔ 題目 YAML 轉換
=====================

把「CTFd 題目資料 + plugin 的 metadata blob」轉成 template 的
`public.yml` / `private.yml`（匯出方向）。

設計原則
--------
1. **純函式、無外部依賴、無 I/O**。輸入 dict、輸出 dict，好測、好被 plugin 與 CLI 共用。
2. **敏感界線以 `private.yml.template` 為準**。凡屬敏感一律進 private。
3. **未知欄位 fail-safe 進 private**。寧可少發佈，也不要不小心把不認識的欄位寫進 public。

輸入來源對照
------------
- CTFd 原生欄位（`name` / `category` / `description` / `value` …）→ 直接對應 public。
- CTFd flags（`/challenges/<id>/flags`）→ private 的 `flag` / `flag_type`（**權威**，有就以它為準）。
- CTFd hints / tags / files → public。
- plugin metadata blob（CTFd 原生沒有的富欄位）→ 依 §KNOWN_PUBLIC / §SENSITIVE 分流。
"""

from __future__ import annotations

from typing import Any, Iterable, Optional


# --------------------------------------------------------------------------- #
# 欄位分流表
# --------------------------------------------------------------------------- #

# metadata blob 中屬於「敏感、只能進 private.yml」的鍵。
# 這份清單對齊 challenge-template/private.yml.template 底部的宣告。
SENSITIVE_KEYS: frozenset[str] = frozenset({
    "flag",
    "flag_type",
    "dynamic_flag",
    "flag_description",
    "solution_steps",
    "test_credentials",
    "deploy_secrets",
    "internal_notes",
    "test_cases",
    "verified_solutions",
    "last_tested",
    "tested_by",
    "test_result",
})

# metadata blob 中屬於「公開、進 public.yml」的鍵。
# 不在這裡、也不在 SENSITIVE_KEYS 的鍵，一律 fail-safe 進 private（見 split_metadata）。
KNOWN_PUBLIC_KEYS: frozenset[str] = frozenset({
    "author",
    "difficulty",
    "challenge_type",
    "owners",
    "assignee",
    "source_code_provided",
    "status",
    "ready_for_release",
    "created_at",
    "updated_at",
    "deploy_info",
    "learning_objectives",
    "required_skills",
    "recommended_tools",
    "references",
    "metadata",
    "files",  # player-facing 附件清單（實體檔在 repo files/，見 spec Ⓒ）
})

# public.yml 中「CTFd 有原生對應」的鍵；challenge_to_ctfd 逆轉時不放進 blob。
NATIVE_PUBLIC_KEYS: frozenset[str] = frozenset({
    "id", "title", "category", "description", "points", "tags", "hints",
})

# CTFd flag type → private.yml 的 flag_type
_CTFD_FLAG_TYPE = {
    "static": "static",
    "regex": "regex",
}


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #

def normalize_tags(tags: Optional[Iterable[Any]]) -> list[str]:
    """CTFd tags 可能是 [{'value': 'web'}] 或 ['web']，統一成 ['web', ...]。"""
    result: list[str] = []
    for tag in tags or []:
        if isinstance(tag, dict):
            value = tag.get("value")
        else:
            value = tag
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def normalize_hints(hints: Optional[Iterable[dict]]) -> list[dict]:
    """CTFd hints（{'content', 'cost'}）→ public 的 [{'level', 'cost', 'content'}]。

    level 依輸入順序推導（1 起算）；空內容略過。
    """
    result: list[dict] = []
    level = 0
    for hint in hints or []:
        content = str((hint or {}).get("content", "")).strip()
        if not content:
            continue
        level += 1
        result.append({
            "level": level,
            "cost": int((hint or {}).get("cost", 0) or 0),
            "content": content,
        })
    return result


def first_flag(flags: Optional[Iterable[dict]]) -> Optional[tuple[str, str]]:
    """取第一個 CTFd flag，回傳 (content, flag_type)；沒有則 None。

    未知的 CTFd flag type 一律退回 'static'（唯一安全的預設）。
    """
    for flag in flags or []:
        content = (flag or {}).get("content")
        if content is None or str(content) == "":
            continue
        ctfd_type = str((flag or {}).get("type", "static")).lower()
        return str(content), _CTFD_FLAG_TYPE.get(ctfd_type, "static")
    return None


def split_metadata(metadata: Optional[dict]) -> tuple[dict, dict]:
    """把 plugin metadata blob 拆成 (public_part, private_part)。

    - 鍵在 SENSITIVE_KEYS → private
    - 鍵在 KNOWN_PUBLIC_KEYS → public
    - 其餘（未知）→ **fail-safe 進 private**
    """
    public_part: dict = {}
    private_part: dict = {}
    for key, value in (metadata or {}).items():
        if key in SENSITIVE_KEYS:
            private_part[key] = value
        elif key in KNOWN_PUBLIC_KEYS:
            public_part[key] = value
        else:
            # 不認識的欄位：寧可留在 private，也不要意外寫進 public
            private_part[key] = value
    return public_part, private_part


# --------------------------------------------------------------------------- #
# 主轉換
# --------------------------------------------------------------------------- #

def ctfd_to_challenge(
    challenge: dict,
    *,
    flags: Optional[Iterable[dict]] = None,
    hints: Optional[Iterable[dict]] = None,
    tags: Optional[Iterable[Any]] = None,
    files: Optional[Iterable[str]] = None,
    metadata: Optional[dict] = None,
) -> tuple[dict, dict]:
    """CTFd 題目資料 → (public.yml dict, private.yml dict)。

    參數
    ----
    challenge : CTFd challenge 物件（至少含 name/category/description/value）
    flags     : /challenges/<id>/flags 的 data（權威 flag 來源）
    hints     : /challenges/<id>/hints 的 data
    tags      : /challenges/<id>/tags 的 data（或字串清單）
    files     : 附件檔名清單
    metadata  : plugin 的 template metadata blob（富欄位）

    回傳
    ----
    (public, private) 兩個 dict，可直接 yaml.dump 成 public.yml / private.yml。
    """
    challenge = challenge or {}

    # metadata blob 先分流，native 欄位之後覆蓋（native / CTFd flag 為權威）
    public, private = split_metadata(metadata)

    # ---- CTFd 原生欄位 → public ----
    public["title"] = challenge.get("name", "")
    public["category"] = challenge.get("category", "")
    public["description"] = challenge.get("description", "")
    if challenge.get("value") is not None:
        public["points"] = challenge.get("value")

    tag_values = normalize_tags(tags)
    if tag_values:
        public["tags"] = tag_values

    hint_list = normalize_hints(hints)
    if hint_list:
        public["hints"] = hint_list

    file_list = [f for f in (files or []) if f]
    if file_list:
        public["files"] = file_list

    # ---- CTFd flags → private（權威，覆蓋 blob 帶進來的 flag/flag_type）----
    resolved = first_flag(flags)
    if resolved:
        private["flag"], private["flag_type"] = resolved

    return public, private


def challenge_to_ctfd(public: dict, private: Optional[dict] = None) -> dict:
    """ctfd_to_challenge 的逆：public/private.yml → 匯入 CTFd 所需的資料 + metadata blob。

    回傳 dict：
      name / category / description / value : CTFd 原生欄位
      tags   : [str]
      hints  : [{content, cost}]
      flag   : str | None      （建成 CTFd flag）
      flag_type : str
      uid    : durable 綁定鍵（來自 public['id']；沒有則 None）
      blob   : dict            （富欄位，供 ChallengeMetadata；round-trip 後 export 會拆回原位）
    """
    public = public or {}
    private = private or {}

    hints = []
    for hint in public.get("hints") or []:
        content = str((hint or {}).get("content", "")).strip()
        if content:
            hints.append({"content": content, "cost": int((hint or {}).get("cost", 0) or 0)})

    # blob = public 的非原生欄位 + private 的非 flag 欄位（flag/flag_type 走 CTFd flag，不入 blob）
    blob: dict = {}
    for key, value in public.items():
        if key not in NATIVE_PUBLIC_KEYS:
            blob[key] = value
    for key, value in private.items():
        if key not in ("flag", "flag_type"):
            blob[key] = value

    flag = private.get("flag")
    return {
        "name": public.get("title", ""),
        "category": public.get("category", ""),
        "description": public.get("description", ""),
        "value": public.get("points"),
        "tags": normalize_tags(public.get("tags")),
        "hints": hints,
        "flag": (str(flag) if flag else None),
        "flag_type": str(private.get("flag_type") or "static"),
        "uid": public.get("id"),
        "blob": blob,
    }
