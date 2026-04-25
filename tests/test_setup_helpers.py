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


def test_generate_branch_protection_doc_has_gh_cli_steps():
    from setup_helpers import generate_branch_protection_doc

    config = {"project": {"organization": "is1ab", "name": "2026-CTF"}}
    text = generate_branch_protection_doc(config)

    # 必含 gh CLI 指令
    assert "gh api" in text or "gh repo edit" in text
    # 必含 main 分支保護要點
    assert "main" in text
    assert "approval" in text.lower() or "approving_review" in text
    # 必含 require status check
    assert "status check" in text.lower() or "required_status_checks" in text


def test_generate_branch_protection_doc_substitutes_organization():
    from setup_helpers import generate_branch_protection_doc

    text = generate_branch_protection_doc({
        "project": {"organization": "is1ab", "name": "2026-CTF"},
    })
    assert 'ORG="is1ab"' in text
    assert 'REPO="2026-CTF"' in text


def test_generate_branch_protection_doc_handles_missing_org():
    from setup_helpers import generate_branch_protection_doc

    text = generate_branch_protection_doc({})
    assert "your-org" in text
    assert "your-repo" in text
