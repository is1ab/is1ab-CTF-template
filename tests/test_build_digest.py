"""增量 ①:內容雜湊 tag + --platform + push 後 @sha256 digest。

純函式為主,不呼叫 docker:
- challenge_schema.content_hash / image_tag
- build-images 的 build_cmd(--platform)、digest_cmd、plan_challenge(content-hash tag)
"""

import importlib.util
import re
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
def bi():
    return _load("build_images", "build-images.py")


def _make_chal(root: Path) -> Path:
    """建一個最小 container 題目目錄。"""
    d = root / "web-demo"
    (d / "docker").mkdir(parents=True)
    (d / "solution").mkdir()
    (d / "public.yml").write_text(
        "title: Demo\ncategory: web\ndifficulty: easy\ndeploy_type: container\n"
        "deploy_info:\n  requires_build: true\n  port: 8080\n",
        encoding="utf-8",
    )
    (d / "private.yml").write_text("flag: FLAG{a}\n", encoding="utf-8")
    (d / "docker" / "Dockerfile").write_text("FROM alpine\nUSER 1000\n", encoding="utf-8")
    (d / "solution" / "exploit.py").write_text("print('flag')\n", encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# content_hash
# --------------------------------------------------------------------------- #

def test_content_hash_deterministic(tmp_path):
    d = _make_chal(tmp_path)
    assert cs.content_hash(d) == cs.content_hash(d)
    assert re.fullmatch(r"[0-9a-f]{12}", cs.content_hash(d))


def test_content_hash_excludes_private_and_solution(tmp_path):
    d = _make_chal(tmp_path)
    h0 = cs.content_hash(d)
    # 改 private.yml(flag)不該換產物身分
    (d / "private.yml").write_text("flag: FLAG{changed}\n", encoding="utf-8")
    assert cs.content_hash(d) == h0
    # 改 solution/ 也不該
    (d / "solution" / "exploit.py").write_text("print('other')\n", encoding="utf-8")
    assert cs.content_hash(d) == h0


def test_content_hash_changes_on_build_context(tmp_path):
    d = _make_chal(tmp_path)
    h0 = cs.content_hash(d)
    # 改 Dockerfile(進 image)→ 換 hash
    (d / "docker" / "Dockerfile").write_text("FROM alpine\nUSER 1001\n", encoding="utf-8")
    assert cs.content_hash(d) != h0


def test_content_hash_excludes_writeup(tmp_path):
    d = _make_chal(tmp_path)
    h0 = cs.content_hash(d)
    (d / "writeup").mkdir()
    (d / "writeup" / "wu.md").write_text("# writeup\n", encoding="utf-8")
    assert cs.content_hash(d) == h0


# --------------------------------------------------------------------------- #
# image_tag:內容雜湊優先,version 明確覆寫
# --------------------------------------------------------------------------- #

def test_image_tag_uses_content_hash_by_default(tmp_path):
    d = _make_chal(tmp_path)
    public = {"deploy_info": {"requires_build": True}}
    tag = cs.image_tag(d, public)
    assert tag == cs.content_hash(d)
    assert re.fullmatch(r"[0-9a-f]{12}", tag)


def test_image_tag_version_override(tmp_path):
    d = _make_chal(tmp_path)
    public = {"deploy_info": {"version": "v7"}}
    assert cs.image_tag(d, public) == "v7"


# --------------------------------------------------------------------------- #
# build-images:--platform / digest_cmd / plan_challenge tag
# --------------------------------------------------------------------------- #

def test_build_cmd_pins_amd64(bi):
    plan = bi.BuildPlan(chal_dir=Path("."), ref="r/x:tag",
                        dockerfile=Path("docker/Dockerfile"), context=Path("."))
    cmd = plan.build_cmd()
    assert "--platform=linux/amd64" in cmd
    assert cmd[0] == "docker" and "build" in cmd


def test_digest_cmd_shape(bi):
    plan = bi.BuildPlan(chal_dir=Path("."), ref="reg/web/x:abc",
                        dockerfile=Path("docker/Dockerfile"), context=Path("."))
    cmd = plan.digest_cmd()
    assert cmd[:3] == ["docker", "inspect", "--format"]
    assert cmd[-1] == "reg/web/x:abc"
    assert "RepoDigests" in cmd[3]


def test_plan_challenge_uses_content_hash_tag(bi, tmp_path, monkeypatch):
    monkeypatch.setenv("IS1AB_REGISTRY", "reg.example.com")
    d = _make_chal(tmp_path)
    plan = bi.plan_challenge(d, {})
    expected = f"reg.example.com/web/web-demo:{cs.content_hash(d)}"
    assert plan.ref == expected
    # 不再是舊的 :v1
    assert not plan.ref.endswith(":v1")


def test_plan_challenge_version_override(bi, tmp_path, monkeypatch):
    monkeypatch.setenv("IS1AB_REGISTRY", "reg.example.com")
    d = _make_chal(tmp_path)
    (d / "public.yml").write_text(
        "title: Demo\ncategory: web\ndeploy_type: container\n"
        "deploy_info:\n  requires_build: true\n  version: v9\n",
        encoding="utf-8",
    )
    plan = bi.plan_challenge(d, {})
    assert plan.ref.endswith(":v9")
