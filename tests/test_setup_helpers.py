"""Unit tests for scripts/setup_helpers.py"""
from pathlib import Path

import pytest

from tests.fixtures.yaml_strings import (
    CLEAN_PRIVATE_YML,
    CLEAN_PUBLIC_YML,
    LEGACY_PRIVATE_YML,
    LEGACY_PUBLIC_YML,
)


def test_generate_pr_template_contains_dual_checklists():
    from setup_helpers import generate_pr_template

    config = {"project": {"name": "is1ab-CTF"}}
    text = generate_pr_template(config)

    # 雙 checklist 結構
    assert "## 出題人 Checklist" in text
    assert "## 驗題人 Checklist" in text
    # 出題人關鍵項目
    assert "make validate" in text
    assert "make scan" in text
    # 驗題人關鍵項目
    assert "git checkout" in text
    assert "已實際解出 flag" in text


def test_generate_codeowners_is_empty_placeholder():
    from setup_helpers import generate_codeowners

    text = generate_codeowners({"team": {"members": []}})

    # spec 8.2: 留空 placeholder，不指派固定 reviewer
    assert "本專案不指派固定 reviewer" in text
    # 不應該預設 @admin / @senior-dev
    assert "@admin" not in text
    assert "@senior-dev" not in text
    # 必須是合法 CODEOWNERS（註解開頭 #）
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped == "":
            continue
        assert stripped.startswith("#"), f"非註解行不該預設指派: {line!r}"
