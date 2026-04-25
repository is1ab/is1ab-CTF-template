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
