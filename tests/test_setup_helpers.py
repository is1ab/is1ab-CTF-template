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


def test_detect_legacy_finds_legacy_files(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    (challenges / "private.yml").write_text(LEGACY_PRIVATE_YML)
    (challenges / "public.yml").write_text(LEGACY_PUBLIC_YML)

    paths = detect_legacy_validation_fields(tmp_path / "challenges")

    # 兩個檔都該被偵測（private 含三 key、public 含 validation_status）
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert names == {"private.yml", "public.yml"}


def test_detect_legacy_skips_clean_files(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "clean"
    challenges.mkdir(parents=True)
    (challenges / "private.yml").write_text(CLEAN_PRIVATE_YML)
    (challenges / "public.yml").write_text(CLEAN_PUBLIC_YML)

    paths = detect_legacy_validation_fields(tmp_path / "challenges")
    assert paths == []


def test_detect_legacy_handles_missing_root(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    paths = detect_legacy_validation_fields(tmp_path / "does_not_exist")
    assert paths == []


def test_cleanup_dry_run_does_not_modify_files(tmp_path):
    from setup_helpers import cleanup_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    private_yml = challenges / "private.yml"
    public_yml = challenges / "public.yml"
    private_yml.write_text(LEGACY_PRIVATE_YML)
    public_yml.write_text(LEGACY_PUBLIC_YML)

    private_before = private_yml.read_text()
    public_before = public_yml.read_text()

    report = cleanup_legacy_validation_fields(tmp_path / "challenges", dry_run=True)

    # 檔案內容未動
    assert private_yml.read_text() == private_before
    assert public_yml.read_text() == public_before

    # 報告內容
    assert report.dry_run is True
    assert len(report.files_changed) == 2
    assert any("reviewer" in keys for keys in report.keys_removed.values())
    assert any("validation_status" in keys for keys in report.keys_removed.values())
