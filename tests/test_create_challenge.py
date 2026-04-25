"""Tests for scripts/create-challenge.py author fallback and CLI surface."""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "create-challenge.py"


@pytest.fixture
def isolated_repo(tmp_path, monkeypatch):
    """建立有 config.yml 的隔離工作目錄，並設好 git user.name = GitUser。"""
    (tmp_path / "challenges").mkdir()
    (tmp_path / "config.yml").write_text(
        "project:\n"
        "  name: test\n"
        "  flag_prefix: testCTF\n"
        "team:\n"
        "  default_author: ConfigDefault\n"
        "points:\n"
        "  easy: 100\n"
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "GitUser"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "git@example.com"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_author_prefers_git_user_over_config_default(isolated_repo):
    """author 順序：--author > git user.name > team.default_author"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "test_chall", "easy"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (isolated_repo / "challenges/web/test_chall/private.yml").read_text()
    assert "author: GitUser" in private_yml
    assert "ConfigDefault" not in private_yml


def test_explicit_author_flag_wins(isolated_repo):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "explicit_chall", "easy",
         "--author", "ExplicitFlag"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (isolated_repo / "challenges/web/explicit_chall/private.yml").read_text()
    assert "author: ExplicitFlag" in private_yml


def test_falls_back_to_config_when_git_user_missing(tmp_path, monkeypatch):
    """git user.name 未設時 fallback 到 config 的 default_author"""
    (tmp_path / "challenges").mkdir()
    (tmp_path / "config.yml").write_text(
        "project:\n  name: t\n  flag_prefix: testCTF\n"
        "team:\n  default_author: FallbackUser\n"
        "points:\n  easy: 100\n"
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    # 建立空的全域 git config，確保 user.name 不被繼承自真實全域設定
    fake_global = tmp_path / "fake_gitconfig"
    fake_global.write_text("[core]\n")
    monkeypatch.chdir(tmp_path)

    env = {**__import__("os").environ,
           "GIT_CONFIG_GLOBAL": str(fake_global),
           "GIT_CONFIG_NOSYSTEM": "1"}

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "fallback_chall", "easy"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (tmp_path / "challenges/web/fallback_chall/private.yml").read_text()
    assert "author: FallbackUser" in private_yml


def test_reviewer_flag_no_longer_exists(isolated_repo):
    """--reviewer 應該已被移除"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert "--reviewer" not in result.stdout


def test_generated_private_yml_has_no_validation_keys(isolated_repo):
    """private.yml 模板不應包含驗題三鍵（reviewer / validation_status / internal_validation_notes）"""
    import yaml as _yaml

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "no_validation", "easy"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = isolated_repo / "challenges/web/no_validation/private.yml"
    data = _yaml.safe_load(private_yml.read_text())
    assert "reviewer" not in data
    assert "validation_status" not in data
    assert "internal_validation_notes" not in data
