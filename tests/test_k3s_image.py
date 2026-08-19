"""Tests for container→k3s image 整合。

涵蓋：
- challenge_schema 的 registry / slugify / image_version / image_ref
- sync-to-ctfd 的 k3s_payload 對應與 sync_challenge 的 type/merge 行為
- build-images 的 skip_reason / plan_challenge（ref 計算與探索，不呼叫 docker）
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import challenge_schema as cs  # noqa: E402


def _load(mod_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(mod_name, str(SCRIPTS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sync():
    return _load("sync_to_ctfd", "sync-to-ctfd.py")


@pytest.fixture
def bi():
    return _load("build_images", "build-images.py")


# --------------------------------------------------------------------------- #
# challenge_schema：registry / slug / version / image_ref
# --------------------------------------------------------------------------- #

def test_registry_from_config(monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    config = {"deployment": {"docker_registry": "reg.example.com"}}
    assert cs.registry(config) == "reg.example.com"


def test_registry_env_overrides_config(monkeypatch):
    monkeypatch.setenv("IS1AB_REGISTRY", "env-reg.example.com/")
    config = {"deployment": {"docker_registry": "reg.example.com"}}
    # 環境變數優先，且去掉尾端 /
    assert cs.registry(config) == "env-reg.example.com"


def test_registry_empty_when_unset(monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    assert cs.registry({}) == ""
    assert cs.registry({"deployment": {"docker_registry": ""}}) == ""


def test_slugify():
    assert cs.slugify("sql_injection") == "sql_injection"
    assert cs.slugify("My Cool Chall!") == "my-cool-chall"
    assert cs.slugify("--Weird__.name--") == "weird__.name"
    assert cs.slugify("") == "challenge"


def test_image_version_default_and_explicit():
    assert cs.image_version({}) == "v1"
    assert cs.image_version({"deploy_info": {}}) == "v1"
    assert cs.image_version({"deploy_info": {"version": "v3"}}) == "v3"


def test_image_ref_with_registry(monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    config = {"deployment": {"docker_registry": "reg.example.com"}}
    assert cs.image_ref(config, "web", "my_chall", "v1") == "reg.example.com/web/my_chall:v1"


def test_image_ref_local_tag_when_no_registry(monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    # registry 未設 → 純本地 tag，不含 registry 前綴
    assert cs.image_ref({}, "pwn", "bof", "v2") == "pwn/bof:v2"


# --------------------------------------------------------------------------- #
# sync-to-ctfd：k3s_payload
# --------------------------------------------------------------------------- #

BASE_CONFIG = {
    "project": {"flag_prefix": "is1abCTF"},
    "deployment": {"docker_registry": "reg.example.com"},
}


def test_k3s_payload_http(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    public = {
        "category": "web",
        "deploy_type": "container",
        "deploy_info": {
            "connection_type": "http",
            "port": 8080,
            "requires_build": True,
            "resources": {"memory": "256Mi", "cpu": "100m"},
        },
    }
    payload = sync.k3s_payload(public, {}, BASE_CONFIG, "sql_injection")
    assert payload["image"] == "reg.example.com/web/sql_injection:v1"
    assert payload["protocol"] == "http"
    assert payload["port"] == 8080
    assert payload["memory"] == "256Mi"
    assert payload["cpu"] == "100m"
    assert payload["flag_format"] == "is1abCTF{%s}"


def test_k3s_payload_nc_uses_nc_port_and_tcp(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    public = {
        "category": "pwn",
        "deploy_type": "container",
        "deploy_info": {
            "connection_type": "nc",
            "port": 8080,
            "nc_port": 9999,
            "requires_build": True,
        },
    }
    payload = sync.k3s_payload(public, {}, BASE_CONFIG, "bof")
    assert payload["protocol"] == "tcp"
    assert payload["port"] == 9999  # nc 題用 nc_port
    assert payload["image"] == "reg.example.com/pwn/bof:v1"


def test_k3s_payload_omits_resources_and_port_when_absent(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    public = {
        "category": "misc",
        "deploy_type": "container",
        "deploy_info": {"connection_type": "http", "requires_build": True},
    }
    payload = sync.k3s_payload(public, {}, BASE_CONFIG, "x")
    assert "memory" not in payload
    assert "cpu" not in payload
    assert "port" not in payload  # 沒填 → 交給插件預設


def test_k3s_payload_image_local_tag_when_no_registry(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    config = {"project": {"flag_prefix": "is1abCTF"}, "deployment": {"docker_registry": ""}}
    public = {"category": "web", "deploy_type": "container",
              "deploy_info": {"connection_type": "http", "requires_build": True}}
    payload = sync.k3s_payload(public, {}, config, "sqli")
    assert payload["image"] == "web/sqli:v1"


def test_k3s_payload_no_flag_prefix_omits_flag_format(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    config = {"deployment": {"docker_registry": "reg.example.com"}}
    public = {"category": "web", "deploy_type": "container",
              "deploy_info": {"connection_type": "http", "requires_build": True}}
    payload = sync.k3s_payload(public, {}, config, "sqli")
    assert "flag_format" not in payload


def test_k3s_payload_version_bump(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    public = {"category": "web", "deploy_type": "container",
              "deploy_info": {"connection_type": "http", "requires_build": True, "version": "v5"}}
    payload = sync.k3s_payload(public, {}, BASE_CONFIG, "sqli")
    assert payload["image"] == "reg.example.com/web/sqli:v5"


# --- flag_mode 對齊插件 attempt()/注入（見 sync-to-ctfd.k3s_payload 註解）---

def _container_public():
    return {"category": "web", "deploy_type": "container",
            "deploy_info": {"connection_type": "http", "requires_build": True}}


def test_k3s_payload_flag_mode_static_shared(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    # private 空 → flag 三軸預設 static + shared → 用 image 內建 flag、不注入
    payload = sync.k3s_payload(_container_public(), {}, BASE_CONFIG, "sqli")
    assert payload["flag_mode"] == "static"
    assert "flag_delivery" not in payload


def test_k3s_payload_flag_mode_dynamic(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(_container_public(), {"flag_load": "dynamic"}, BASE_CONFIG, "sqli")
    assert payload["flag_mode"] == "dynamic"
    assert payload["flag_delivery"] == "file+env"  # 生成的 flag 同時進檔案與 env


def test_k3s_payload_flag_mode_per_team_is_dynamic(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(_container_public(), {"flag_scope": "per_team"}, BASE_CONFIG, "sqli")
    assert payload["flag_mode"] == "dynamic"
    assert payload["flag_delivery"] == "file+env"


# --- deploy_info → 更多 k3s 欄位（#3 adapter 擴充；全部有填才送）---

def _container_public_with(**deploy_extra):
    """container 題 public，deploy_info 可再塞欄位。"""
    info = {"connection_type": "http", "port": 8080, "requires_build": True}
    info.update(deploy_extra)
    return {"category": "web", "deploy_type": "container", "deploy_info": info}


def test_k3s_payload_sidecars_json_string(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    import json
    sidecars = [{"name": "bot", "image": "web/sqli-bot:v1"}]
    payload = sync.k3s_payload(_container_public_with(sidecars=sidecars), {}, BASE_CONFIG, "sqli")
    # 插件收字串後才 json.loads，故 adapter 必須送 JSON 字串
    assert isinstance(payload["sidecars"], str)
    assert json.loads(payload["sidecars"]) == sidecars


def test_k3s_payload_sidecars_empty_omitted(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(_container_public_with(sidecars=[]), {}, BASE_CONFIG, "sqli")
    assert "sidecars" not in payload  # 空 list → 不送


def test_k3s_payload_allow_egress_sent_when_present(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    on = sync.k3s_payload(_container_public_with(allow_egress=True), {}, BASE_CONFIG, "sqli")
    assert on["allow_egress"] is True
    off = sync.k3s_payload(_container_public_with(allow_egress=False), {}, BASE_CONFIG, "sqli")
    # key 存在才送，包含明確關閉（False）
    assert off["allow_egress"] is False


def test_k3s_payload_allow_egress_omitted_when_absent(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(_container_public_with(), {}, BASE_CONFIG, "sqli")
    assert "allow_egress" not in payload


def test_k3s_payload_ttl_and_max_renews(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(
        _container_public_with(ttl_minutes=45, max_renews=2), {}, BASE_CONFIG, "sqli"
    )
    assert payload["ttl_minutes"] == 45
    assert payload["max_renews"] == 2


def test_k3s_payload_ttl_and_max_renews_omitted_when_absent(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    payload = sync.k3s_payload(_container_public_with(), {}, BASE_CONFIG, "sqli")
    assert "ttl_minutes" not in payload
    assert "max_renews" not in payload


# --------------------------------------------------------------------------- #
# sync-to-ctfd：sync_challenge 的 type 與 merge 行為
# --------------------------------------------------------------------------- #

class FakeClient:
    """只記錄送出的 payload，不連網。"""

    def __init__(self):
        self.dry_run = False
        self.posted = []

    def find_challenge_by_name(self, name):
        return None

    def post(self, path, payload):
        self.posted.append((path, payload))
        return {"data": {"id": 1}}

    def patch(self, path, payload):
        self.posted.append((path, payload))
        return {"data": {"id": 1}}

    def get(self, path):
        return {"data": []}

    def delete(self, path):
        return None


def _container_public(**deploy):
    info = {"connection_type": "http", "port": 8080, "requires_build": True}
    info.update(deploy)
    return {
        "title": "T",
        "category": "web",
        "description": "d",
        "deploy_type": "container",
        "deploy_info": info,
    }


# flag_load=dynamic → resolve_flag 回 []，sync_flag 不建靜態 flag（container 題的 flag 由插件發）
DYNAMIC_PRIVATE = {"flag_load": "dynamic", "flag_scope": "per_team"}


def test_sync_challenge_container_becomes_k3s(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    client = FakeClient()
    sync.sync_challenge(
        client, Path("challenges/web/my_chall"),
        _container_public(), DYNAMIC_PRIVATE, BASE_CONFIG, "staging",
    )
    _, payload = client.posted[0]
    assert payload["type"] == "k3s"
    assert payload["image"] == "reg.example.com/web/my_chall:v1"
    assert payload["protocol"] == "http"
    assert payload["port"] == 8080


def test_sync_challenge_ctfd_override_wins(sync, monkeypatch):
    """public.yml 的 ctfd: 在 adapter 之後 merge，作者可覆蓋任何欄位。"""
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    client = FakeClient()
    public = _container_public()
    public["ctfd"] = {"image": "custom/img:latest", "memory": "512Mi", "run_as_user": 1000}
    sync.sync_challenge(
        client, Path("challenges/web/my_chall"),
        public, DYNAMIC_PRIVATE, BASE_CONFIG, "staging",
    )
    _, payload = client.posted[0]
    assert payload["type"] == "k3s"
    assert payload["image"] == "custom/img:latest"  # ctfd 覆蓋 adapter
    assert payload["memory"] == "512Mi"
    assert payload["run_as_user"] == 1000


def test_sync_challenge_attachment_stays_standard(sync, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    client = FakeClient()
    public = {"title": "A", "category": "web", "description": "d",
              "deploy_type": "attachment"}
    sync.sync_challenge(
        client, Path("challenges/web/att"),
        public, {"flag_load": "dynamic", "flag_scope": "per_team"}, BASE_CONFIG, "staging",
    )
    _, payload = client.posted[0]
    assert payload["type"] == "standard"
    assert "image" not in payload


# --------------------------------------------------------------------------- #
# build-images：skip_reason / plan_challenge / discover
# --------------------------------------------------------------------------- #

def test_skip_reason(bi):
    assert bi.skip_reason({"deploy_type": "attachment"})
    assert bi.skip_reason({"deploy_type": "container", "deploy_info": {"requires_build": False}})
    assert bi.skip_reason(
        {"deploy_type": "container", "deploy_info": {"requires_build": True}}
    ) is None


def _make_challenge(tmp_path: Path, name: str, public_yaml: str) -> Path:
    chal = tmp_path / "web" / name
    (chal / "docker").mkdir(parents=True)
    (chal / "public.yml").write_text(public_yaml, encoding="utf-8")
    (chal / "docker" / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    return chal


def test_plan_challenge_computes_ref_and_cmds(bi, tmp_path, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    chal = _make_challenge(
        tmp_path, "sql_injection",
        "category: web\ndeploy_type: container\ndeploy_info:\n  requires_build: true\n",
    )
    config = {"deployment": {"docker_registry": "reg.example.com"}}
    plan = bi.plan_challenge(chal, config)
    assert plan.ref == "reg.example.com/web/sql_injection:v1"
    assert plan.dockerfile == chal / "docker" / "Dockerfile"
    assert plan.context == chal
    # build 慣例：-f docker/Dockerfile、context = 題目根
    assert plan.build_cmd() == [
        "docker", "build", "-f", str(chal / "docker" / "Dockerfile"),
        "-t", "reg.example.com/web/sql_injection:v1", str(chal),
    ]
    assert plan.push_cmd() == ["docker", "push", "reg.example.com/web/sql_injection:v1"]


def test_plan_challenge_local_tag_without_registry(bi, tmp_path, monkeypatch):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    chal = _make_challenge(
        tmp_path, "bof",
        "category: pwn\ndeploy_type: container\ndeploy_info:\n  requires_build: true\n  version: v2\n",
    )
    plan = bi.plan_challenge(chal, {})
    assert plan.ref == "pwn/bof:v2"


def test_discover_challenges(bi, tmp_path):
    _make_challenge(tmp_path, "a", "category: web\ndeploy_type: container\n")
    _make_challenge(tmp_path, "b", "category: web\ndeploy_type: container\n")
    found = bi.discover_challenges(tmp_path)
    assert len(found) == 2
    assert all((p / "public.yml").exists() for p in found)


def test_build_one_dry_run_does_not_call_docker(bi, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("IS1AB_REGISTRY", raising=False)
    chal = _make_challenge(
        tmp_path, "x",
        "category: web\ndeploy_type: container\ndeploy_info:\n  requires_build: true\n",
    )
    plan = bi.plan_challenge(chal, {"deployment": {"docker_registry": "reg.example.com"}})

    # 若 dry-run 真的呼叫 docker，_run 會被觸發；這裡讓它爆掉以證明沒被呼叫
    def _boom(cmd):
        raise AssertionError(f"dry-run 不該呼叫 docker：{cmd}")

    monkeypatch.setattr(bi, "_run", _boom)
    bi.build_one(plan, dry_run=True, push=True, has_registry=True)
    out = capsys.readouterr().out
    assert "docker build" in out
    assert "docker push" in out
