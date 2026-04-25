"""Integration tests for /setup wizard and team.members schema."""
import importlib
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web-interface"
sys.path.insert(0, str(WEB_DIR))

import app as _app_module  # noqa: E402  (imported for monkeypatch string resolution)


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Provide an isolated temp config.yml and reload app module with patched paths."""
    cfg = tmp_path / "config.yml"
    (tmp_path / "challenges").mkdir()

    # Reload app so module-level code re-runs (clears any prior state).
    importlib.reload(_app_module)

    # After reload the module-level constants are reset — patch them now.
    monkeypatch.setattr(_app_module, "CONFIG_FILE", cfg)
    monkeypatch.setattr(_app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(_app_module, "CHALLENGES_DIR", tmp_path / "challenges")

    return cfg


def test_load_config_migrates_old_reviewers_authors(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "testCTF"},
        "team": {
            "default_author": "alice",
            "reviewers": ["bob", "carol"],
            "authors": ["alice", "dave"],
        },
        "points": {"easy": 100},
    }))

    mgr = _app_module.CTFManager()

    members = mgr.config.get("members") or []
    usernames = {m["github_username"] for m in members}
    # 預期：合併 reviewers + authors + default_author，去重
    assert usernames == {"alice", "bob", "carol", "dave"}
    # display_name 預設等於 github_username
    for m in members:
        assert m.get("display_name") == m["github_username"]
        assert m.get("specialty", "") == ""


def test_load_config_reads_native_members(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "testCTF"},
        "team": {
            "members": [
                {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
                {"github_username": "bob", "display_name": "Bob", "specialty": "pwn"},
            ],
        },
        "points": {"easy": 100},
    }))

    mgr = _app_module.CTFManager()

    members = mgr.config.get("members") or []
    assert len(members) == 2
    assert members[0]["github_username"] == "alice"
    assert members[0]["specialty"] == "web"


def test_compute_step_status_empty_config(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "", "flag_prefix": ""},
        "team": {},
        "event": {},
        "challenge_quota": {},
        "points": {"easy": 100},
    }))

    mgr = _app_module.CTFManager()

    statuses = mgr.compute_step_status()
    assert statuses == {
        "project": "pending",
        "team": "pending",
        "event": "pending",
        "quota": "pending",
        "finalize": "pending",
    }


def test_compute_step_status_all_done(temp_config, tmp_path):
    # 預先建立 .github 檔案模擬 finalize 已跑過
    gh_dir = tmp_path / ".github"
    gh_dir.mkdir()
    (gh_dir / "PULL_REQUEST_TEMPLATE.md").write_text("dummy")
    (gh_dir / "CODEOWNERS").write_text("dummy")

    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "is1ab-CTF", "flag_prefix": "is1abCTF"},
        "team": {
            "members": [{"github_username": "alice", "display_name": "Alice"}],
        },
        "event": {"start_date": "2026-05-01", "end_date": "2026-05-30"},
        "challenge_quota": {
            "by_category": {"web": 6},
            "by_difficulty": {"easy": 10},
            "total_target": 16,
        },
        "points": {"easy": 100},
    }))

    mgr = _app_module.CTFManager()

    statuses = mgr.compute_step_status()
    assert statuses["project"] == "done"
    assert statuses["team"] == "done"
    assert statuses["event"] == "done"
    assert statuses["quota"] == "done"
    assert statuses["finalize"] == "done"


def test_save_step_project_writes_only_project_fields(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "old"},
        "team": {"default_author": "preserved"},
    }))

    mgr = _app_module.CTFManager()
    result = mgr.save_setup_step("project", {
        "project_name": "new-name",
        "organization": "is1ab",
        "flag_prefix": "is1abCTF",
        "year": "2026",
        "description": "desc",
    })

    assert result["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["project"]["name"] == "new-name"
    assert raw["project"]["flag_prefix"] == "is1abCTF"
    # team 區塊不被改動
    assert raw["team"]["default_author"] == "preserved"


def test_save_step_team_replaces_members_list(temp_config):
    temp_config.write_text(yaml.safe_dump({"team": {}}))

    mgr = _app_module.CTFManager()
    result = mgr.save_setup_step("team", {
        "members": [
            {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
            {"github_username": "bob", "display_name": "Bob", "specialty": ""},
        ],
        "default_author": "",
    })

    assert result["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["team"]["members"] == [
        {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
        {"github_username": "bob", "display_name": "Bob", "specialty": ""},
    ]


def test_save_step_invalid_step_returns_error(temp_config):
    temp_config.write_text(yaml.safe_dump({}))
    mgr = _app_module.CTFManager()
    result = mgr.save_setup_step("not_a_step", {})
    assert result["status"] == "error"


@pytest.fixture
def client(temp_config, monkeypatch):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "tCTF"},
        "team": {"members": []},
        "event": {},
        "challenge_quota": {},
        "points": {"easy": 100},
    }))
    import importlib, app as app_module
    importlib.reload(app_module)
    # Re-apply path patches after reload (reload resets module-level constants).
    monkeypatch.setattr(app_module, "CONFIG_FILE", temp_config)
    monkeypatch.setattr(app_module, "BASE_DIR", temp_config.parent)
    monkeypatch.setattr(app_module, "CHALLENGES_DIR", temp_config.parent / "challenges")
    # Re-create ctf_manager so it reads from the patched CONFIG_FILE.
    app_module.ctf_manager = app_module.CTFManager()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_get_setup_root_redirects_to_project(client):
    resp = client.get("/setup")
    assert resp.status_code in (301, 302)
    assert "/setup/project" in resp.location


def test_get_setup_step_returns_200(client):
    for step in ("project", "team", "event", "quota", "finalize"):
        resp = client.get(f"/setup/{step}")
        assert resp.status_code == 200, f"{step} returned {resp.status_code}"


def test_get_setup_unknown_step_returns_404(client):
    resp = client.get("/setup/bogus")
    assert resp.status_code == 404


def test_post_setup_project_writes_config(client, temp_config):
    resp = client.post("/setup/project", data={
        "project_name": "is1ab-CTF-2026",
        "organization": "is1ab",
        "flag_prefix": "is1abCTF",
        "year": "2026",
        "description": "annual CTF",
        "gzctf_url": "http://gzctf.example",
        "host": "10.0.0.1",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["project"]["name"] == "is1ab-CTF-2026"
    assert raw["project"]["flag_prefix"] == "is1abCTF"
    assert raw["platform"]["gzctf_url"] == "http://gzctf.example"
    assert raw["deployment"]["host"] == "10.0.0.1"


def test_post_setup_team_replaces_members(client, temp_config):
    payload = {
        "default_author": "alice",
        "members": [
            {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
            {"github_username": "bob", "display_name": "Bob", "specialty": "pwn"},
        ],
    }
    resp = client.post("/setup/team", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["team"]["default_author"] == "alice"
    assert len(raw["team"]["members"]) == 2
    assert raw["team"]["members"][1]["github_username"] == "bob"


def test_post_setup_event_writes_dates(client, temp_config):
    resp = client.post("/setup/event", data={
        "start_date": "2026-05-01",
        "end_date": "2026-05-30",
        "authoring_deadline": "2026-04-15",
        "review_deadline": "2026-04-25",
        "freeze_deadline": "2026-04-28",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["event"]["start_date"] == "2026-05-01"
    assert raw["event"]["freeze_deadline"] == "2026-04-28"


def test_post_setup_quota_writes_dict(client, temp_config):
    payload = {
        "by_category": {"web": 6, "pwn": 4, "crypto": 3},
        "by_difficulty": {"easy": 8, "middle": 5},
        "total_target": "13",
    }
    resp = client.post("/setup/quota", json=payload)
    assert resp.status_code == 200
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["challenge_quota"]["by_category"] == {"web": 6, "pwn": 4, "crypto": 3}
    assert raw["challenge_quota"]["total_target"] == 13


def test_finalize_generates_github_files(client, temp_config, tmp_path):
    resp = client.post("/setup/finalize", json={
        "generate_pr_template": True,
        "generate_codeowners": True,
        "generate_branch_protection_doc": True,
        "cleanup_legacy": False,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success"
    pr_tmpl = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md"
    codeowners = tmp_path / ".github" / "CODEOWNERS"
    bp_doc = tmp_path / ".github" / "branch-protection.md"
    assert pr_tmpl.exists()
    assert codeowners.exists()
    assert bp_doc.exists()
    assert "出題人 Checklist" in pr_tmpl.read_text()


def test_legacy_count_endpoint_returns_zero_for_clean_repo(client):
    resp = client.get("/api/setup/legacy-count")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 0


def test_validation_route_returns_404(client):
    resp = client.get("/validation")
    assert resp.status_code == 404


def test_api_review_route_returns_404(client):
    resp = client.post("/api/challenges/web/foo/review", json={"action": "approve", "actor": "x"})
    assert resp.status_code == 404


def test_web_create_challenge_does_not_write_legacy_keys(temp_config, tmp_path):
    """POST /api/challenges should produce a private.yml without the 3 legacy keys."""
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "tCTF"},
        "team": {"members": [{"github_username": "alice", "display_name": "Alice"}]},
        "points": {"easy": 100},
    }))
    import importlib, app as app_module
    importlib.reload(app_module)
    monkey_attrs = {
        "CONFIG_FILE": temp_config,
        "BASE_DIR": tmp_path,
        "CHALLENGES_DIR": tmp_path / "challenges",
    }
    for attr, value in monkey_attrs.items():
        setattr(app_module, attr, value)
    app_module.ctf_manager = app_module.CTFManager()
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()

    resp = client.post("/api/challenges", json={
        "category": "web",
        "name": "test_no_legacy",
        "difficulty": "easy",
        "author": "alice",
    })
    # 不論回 200 還是 201，只要建立成功就 OK
    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    private_yml = tmp_path / "challenges/web/test_no_legacy/private.yml"
    assert private_yml.exists()
    data = yaml.safe_load(private_yml.read_text())
    assert "reviewer" not in data
    assert "validation_status" not in data
    assert "internal_validation_notes" not in data
