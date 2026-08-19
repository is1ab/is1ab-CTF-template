#!/usr/bin/env python3
"""
Build 並 push 題目 container image 到私有 registry
=================================================

把 challenges/ 底下 `deploy_type: container` 且 `deploy_info.requires_build` 的題目
build 成 docker image，並 push 到 config.yml 的 `deployment.docker_registry`
（可用環境變數 IS1AB_REGISTRY 覆蓋）。sync-to-ctfd 之後會把 image ref 指進 CTFd 的
k3s_challenges 插件，讓 pod 起得起來。

image ref 慣例：{registry}/{category}/{slug}:{version}
  - slug     = 題目目錄名（轉小寫、docker 合法字元）
  - version  = deploy_info.version（預設 v1；改 image 時 bump）
  - registry 未設時只 build 純本地 tag（{category}/{slug}:{version}）並警告，不 push、不 crash。

build 慣例（見範例 docker/docker-compose.yml）：
  context = 題目根目錄、dockerfile = docker/Dockerfile
  → docker build -f <chal>/docker/Dockerfile -t <ref> <chal>

用法
----
    # build 並 push 全部（略過 examples/）
    ./scripts/build-images.py

    # 只 build 單一題目
    ./scripts/build-images.py --path challenges/web/my_chall

    # 只看會做什麼，不實際呼叫 docker
    ./scripts/build-images.py --dry-run

    # build 但不 push（本地測試用）
    ./scripts/build-images.py --no-push

環境變數
--------
    IS1AB_REGISTRY   覆蓋 config.yml 的 deployment.docker_registry
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import challenge_schema as cs  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    print("❌ 需要 pyyaml：uv sync 或 pip install pyyaml", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent

# 顏色 / log 風格對齊 scripts/build.sh（[INFO]/[STEP]/[SUCCESS]/[WARNING]/[ERROR]）
_RED = "\033[0;31m"
_GREEN = "\033[0;32m"
_YELLOW = "\033[1;33m"
_BLUE = "\033[0;34m"
_CYAN = "\033[0;36m"
_NC = "\033[0m"


def log_info(msg: str) -> None:
    print(f"{_BLUE}[INFO]{_NC} {msg}")


def log_step(msg: str) -> None:
    print(f"{_CYAN}[STEP]{_NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{_GREEN}[SUCCESS]{_NC} {msg}")


def log_warning(msg: str) -> None:
    print(f"{_YELLOW}[WARNING]{_NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{_RED}[ERROR]{_NC} {msg}")


# --------------------------------------------------------------------------- #
# 設定 / 題目載入（與 sync-to-ctfd.py 相同慣例）
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    """讀取 repo 根目錄的 config.yml"""
    config_path = REPO_ROOT / "config.yml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def discover_challenges(path: Path) -> list[Path]:
    """找出所有含 public.yml 的題目目錄"""
    if (path / "public.yml").exists():
        return [path]
    return sorted(p.parent for p in path.rglob("public.yml"))


def load_public(chal_dir: Path) -> dict:
    """只讀 public.yml（build 不需要 private.yml）"""
    with open(chal_dir / "public.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# --------------------------------------------------------------------------- #
# build 規劃（純函式，方便測試，不呼叫 docker）
# --------------------------------------------------------------------------- #

def skip_reason(public: dict) -> Optional[str]:
    """回傳略過原因；None 代表這題要 build。"""
    if cs.deploy_type(public) != "container":
        return "非 container 題（deploy_type != container）"
    if not (public.get("deploy_info") or {}).get("requires_build"):
        return "deploy_info.requires_build 非 true"
    return None


class BuildPlan:
    """單一題目的 build 計畫（純資料，不含副作用）。"""

    def __init__(self, chal_dir: Path, ref: str, dockerfile: Path, context: Path):
        self.chal_dir = chal_dir
        self.ref = ref
        self.dockerfile = dockerfile
        self.context = context

    def build_cmd(self) -> List[str]:
        return ["docker", "build", "-f", str(self.dockerfile), "-t", self.ref, str(self.context)]

    def push_cmd(self) -> List[str]:
        return ["docker", "push", self.ref]


def plan_challenge(chal_dir: Path, config: dict) -> BuildPlan:
    """算出單題的 image ref 與 build context / dockerfile 路徑。"""
    public = load_public(chal_dir)
    ref = cs.image_ref(
        config, cs.category(public), cs.slugify(chal_dir.name), cs.image_version(public)
    )
    dockerfile = chal_dir / "docker" / "Dockerfile"
    return BuildPlan(chal_dir=chal_dir, ref=ref, dockerfile=dockerfile, context=chal_dir)


# --------------------------------------------------------------------------- #
# 執行
# --------------------------------------------------------------------------- #

def _run(cmd: List[str]) -> None:
    """跑外部指令，非 0 直接拋 RuntimeError（訊息含指令）。"""
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"指令失敗（exit {result.returncode}）：{' '.join(cmd)}")


def build_one(
    plan: BuildPlan,
    *,
    dry_run: bool,
    push: bool,
    has_registry: bool,
) -> None:
    """build（並視情況 push）單一題目。dry_run 時只印不做。"""
    if not plan.dockerfile.exists():
        raise RuntimeError(f"找不到 Dockerfile：{_rel(plan.dockerfile)}")

    build_cmd = plan.build_cmd()
    if dry_run:
        log_info(f"  [dry-run] {' '.join(build_cmd)}")
    else:
        log_info(f"  build → {plan.ref}")
        _run(build_cmd)

    if not push:
        return
    if not has_registry:
        log_warning("  未設 registry，只 build 不 push（設 config.deployment.docker_registry 或 IS1AB_REGISTRY 以啟用 push）")
        return

    push_cmd = plan.push_cmd()
    if dry_run:
        log_info(f"  [dry-run] {' '.join(push_cmd)}")
    else:
        log_info(f"  push  → {plan.ref}")
        _run(push_cmd)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="build 並 push 題目 container image 到私有 registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--path", default=None,
                        help="單一題目目錄，或要遞迴掃描的目錄（預設 challenges/）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只印會做什麼，不實際呼叫 docker")
    parser.add_argument("--no-push", action="store_true",
                        help="只 build 不 push")
    parser.add_argument("--include-examples", action="store_true",
                        help="一併處理 challenges/examples/（預設略過）")
    args = parser.parse_args()

    config = load_config()
    root = Path(args.path).resolve() if args.path else (REPO_ROOT / "challenges")
    if not root.exists():
        log_error(f"路徑不存在：{root}")
        return 1

    challenges = discover_challenges(root)
    if not args.include_examples:
        challenges = [c for c in challenges if "examples" not in c.parts]

    if not challenges:
        log_warning("找不到任何題目（缺少 public.yml？）")
        return 0

    has_registry = bool(cs.registry(config))
    push = not args.no_push
    log_info(f"registry：{cs.registry(config) or '（未設，只 build 不 push）'}")
    log_info(f"找到 {len(challenges)} 個題目{'（dry-run）' if args.dry_run else ''}\n")

    built, skipped, failed = 0, 0, 0

    for chal_dir in challenges:
        title = _rel(chal_dir)
        try:
            public = load_public(chal_dir)
        except yaml.YAMLError as e:
            log_error(f"{title}：YAML 解析失敗 — {e}")
            failed += 1
            continue

        reason = skip_reason(public)
        if reason:
            log_info(f"⏭️  略過 {title}：{reason}")
            skipped += 1
            continue

        plan = plan_challenge(chal_dir, config)
        log_step(f"{title} → {plan.ref}")
        try:
            build_one(plan, dry_run=args.dry_run, push=push, has_registry=has_registry)
            log_success(f"{title} 完成")
            built += 1
        except RuntimeError as e:
            log_error(f"{title} — {e}")
            failed += 1

    print(f"\n完成：{built} build / {skipped} 略過 / {failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
