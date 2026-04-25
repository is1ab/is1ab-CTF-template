"""Smoke test for scripts/cleanup-validation-fields.py CLI."""
import subprocess
import sys
from pathlib import Path

import yaml

from tests.fixtures.yaml_strings import LEGACY_PRIVATE_YML, LEGACY_PUBLIC_YML

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "cleanup-validation-fields.py"


def _setup_legacy_repo(tmp_path: Path) -> Path:
    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    (challenges / "private.yml").write_text(LEGACY_PRIVATE_YML)
    (challenges / "public.yml").write_text(LEGACY_PUBLIC_YML)
    return tmp_path


def test_cli_dry_run_does_not_modify(tmp_path):
    repo = _setup_legacy_repo(tmp_path)
    private_before = (repo / "challenges/web/legacy/private.yml").read_text()

    result = subprocess.run(
        [sys.executable, str(CLI), "--dry-run", "--root", str(repo / "challenges")],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "DRY RUN" in result.stdout or "dry-run" in result.stdout.lower()
    assert (repo / "challenges/web/legacy/private.yml").read_text() == private_before


def test_cli_apply_removes_keys(tmp_path):
    repo = _setup_legacy_repo(tmp_path)

    subprocess.run(
        [sys.executable, str(CLI), "--apply", "--root", str(repo / "challenges")],
        capture_output=True,
        text=True,
        check=True,
    )

    private_after = yaml.safe_load(
        (repo / "challenges/web/legacy/private.yml").read_text()
    )
    assert "reviewer" not in private_after
    assert "validation_status" not in private_after
