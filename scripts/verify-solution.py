#!/usr/bin/env python3
"""
驗題：把題目跑起來，執行官方解，並比對取回的 flag
========================================================

為什麼要比對 flag 而不是只看 exit code
--------------------------------------
只檢查 exit code 抓不到「腳本成功執行、但 flag 本身是錯的」這一類 bug——
UMass CTF 2021 的 warandpieces 就是 flag 編碼錯誤（兩個數字用了同一個顏色），
腳本跑得好好的。

更重要的是它抓 **flag drift**：private.yml 寫的 flag 與實際烘進 image 的
flag 不一致。本 repo 的結構允許這個 bug 發生，而在此之前沒有任何東西在檢查。
做法是把 private.yml 的 flag 由環境變數注入容器，再比對解題腳本取回的值——
若 image 無視 ${FLAG} 自己寫死一份，比對就會失敗。

解題腳本的介面契約
------------------
- 位置：solution/exploit.py（或 solve.py / solve.sh / exploit.sh）
- 參數：--connection-info "nc <host> <port>"（對齊 ctfcli，維持可攜性）
        另支援 HOST / PORT 環境變數作為 fallback
- 輸出：**把取得的 flag 印在 stdout 最後一行**。不要自己比對，交給本腳本比對。
- 離開碼：0 成功／4 尚未實作（NOT_IMPLEMENTED）／其他 失敗

離開碼
------
    0  通過
    1  失敗（flag 不符、腳本失敗、服務起不來）
    2  設定或環境錯誤
    4  解題腳本尚未實作（讓「沒寫 exploit」與「題目壞了」在報表上可區分）
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    print("❌ 需要 pyyaml：uv sync", file=sys.stderr)
    sys.exit(2)


EXIT_PASS, EXIT_FAIL, EXIT_ERROR, EXIT_NOT_IMPLEMENTED = 0, 1, 2, 4

SOLUTION_CANDIDATES = [
    "solution/exploit.py",
    "solution/solve.py",
    "solution/exploit.sh",
    "solution/solve.sh",
]

# 這些題型沒有服務，解題腳本直接對附件operate
NO_SERVICE_TYPES = {"static_attachment", "dynamic_attachment"}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_solution(chal_dir: Path) -> Optional[Path]:
    for candidate in SOLUTION_CANDIDATES:
        path = chal_dir / candidate
        if path.exists():
            return path
    return None


def resolve_port(public: dict) -> Optional[int]:
    deploy = public.get("deploy_info") or {}
    for key in ("nc_port", "port"):
        value = deploy.get(key)
        if isinstance(value, int):
            return value
    return None


def wait_for_port(port: int, timeout: int = 60) -> bool:
    """輪詢等待服務真的開始 listen，不要用 sleep 猜"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


def compose_cmd(chal_dir: Path) -> Optional[list[str]]:
    compose_file = chal_dir / "docker" / "docker-compose.yml"
    if not compose_file.exists():
        compose_file = chal_dir / "docker-compose.yml"
    if not compose_file.exists():
        return None
    if not shutil.which("docker"):
        return None
    return ["docker", "compose", "-f", str(compose_file)]


def run_solution(
    solution: Path, connection_info: Optional[str], timeout: int
) -> tuple[int, str]:
    if solution.suffix == ".py":
        cmd = [sys.executable, str(solution)]
    else:
        cmd = ["bash", str(solution)]

    env = dict(os.environ)
    if connection_info:
        cmd += ["--connection-info", connection_info]
        parts = connection_info.split()
        if len(parts) >= 3:
            env["HOST"], env["PORT"] = parts[1], parts[2]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(solution.parent.parent),
            env=env,
        )
    except subprocess.TimeoutExpired:
        log(f"❌ 解題腳本逾時（{timeout}s）")
        return EXIT_FAIL, ""

    if proc.stderr.strip():
        log("--- 解題腳本 stderr ---")
        log(proc.stderr.strip()[-2000:])

    return proc.returncode, proc.stdout


def extract_flag(stdout: str) -> Optional[str]:
    """取 stdout 最後一個非空白行"""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return lines[-1] if lines else None


def compare_flag(found: str, private: dict) -> tuple[bool, str]:
    expected = private.get("flag")
    flag_type = (private.get("flag_type") or "static").lower()

    if flag_type == "dynamic":
        return True, "動態 flag，僅要求解題腳本成功（不比對內容）"
    if not expected:
        return False, "private.yml 沒有 flag，無法比對"

    if flag_type == "regex":
        try:
            if re.fullmatch(str(expected), found):
                return True, "符合 regex"
            return False, f"不符合 regex：{expected}"
        except re.error as e:
            return False, f"private.yml 的 flag 不是合法 regex：{e}"

    if found == str(expected):
        return True, "與 private.yml 相符"
    return False, "與 private.yml 不符（flag drift：題目烘進 image 的 flag 與 private.yml 不同）"


def verify(chal_dir: Path, timeout: int, keep: bool) -> int:
    public = load_yaml(chal_dir / "public.yml")
    private = load_yaml(chal_dir / "private.yml")

    if not public:
        log(f"❌ 找不到 public.yml：{chal_dir}")
        return EXIT_ERROR

    title = public.get("title", chal_dir.name)
    challenge_type = public.get("challenge_type", "")
    log(f"\n=== 驗題：{title}（{challenge_type}）===")

    if (public.get("healthcheck") or {}).get("enabled") is False:
        log("⏭️  public.yml 明確關閉 healthcheck，略過")
        return EXIT_PASS

    solution = find_solution(chal_dir)
    if not solution:
        log(f"⚠️  找不到解題腳本（{' / '.join(SOLUTION_CANDIDATES)}）")
        return EXIT_NOT_IMPLEMENTED

    needs_service = challenge_type not in NO_SERVICE_TYPES
    compose = compose_cmd(chal_dir) if needs_service else None
    port = resolve_port(public)
    connection_info = None
    env = dict(os.environ)

    if compose:
        if port is None:
            log("❌ 需要服務但 public.yml 的 deploy_info 沒有 port / nc_port")
            return EXIT_ERROR

        # 由 private.yml 注入 flag。若 image 無視 ${FLAG} 自己寫死一份，
        # 後續比對就會失敗——這正是 flag drift 的偵測點。
        if private.get("flag"):
            env["FLAG"] = str(private["flag"])

        log(f"🐳 啟動容器…（port {port}）")
        up = subprocess.run(compose + ["up", "-d", "--build"],
                            capture_output=True, text=True, env=env)
        if up.returncode != 0:
            log("❌ docker compose up 失敗")
            log(up.stderr.strip()[-2000:])
            return EXIT_FAIL

        try:
            if not wait_for_port(port):
                log(f"❌ 服務在 60 秒內沒有 listen port {port}")
                logs = subprocess.run(compose + ["logs", "--tail", "50"],
                                      capture_output=True, text=True)
                log(logs.stdout[-2000:])
                return EXIT_FAIL

            connection_info = f"nc 127.0.0.1 {port}"
            log(f"✅ 服務就緒，執行解題腳本：{solution.relative_to(chal_dir)}")
            code, stdout = run_solution(solution, connection_info, timeout)
        finally:
            if keep:
                log(f"ℹ️  --keep：容器保留中，手動清理：{' '.join(compose)} down -v")
            else:
                subprocess.run(compose + ["down", "-v"],
                               capture_output=True, text=True)
    else:
        if needs_service:
            log("ℹ️  沒有 docker compose，改為直接執行解題腳本")
        log(f"▶️  執行解題腳本：{solution.relative_to(chal_dir)}")
        code, stdout = run_solution(solution, None, timeout)

    if code == EXIT_NOT_IMPLEMENTED:
        log("⚠️  解題腳本回報尚未實作（exit 4）")
        return EXIT_NOT_IMPLEMENTED
    if code != 0:
        log(f"❌ 解題腳本失敗（exit {code}）")
        return EXIT_FAIL

    found = extract_flag(stdout)
    if not found:
        log("❌ 解題腳本沒有輸出任何內容；契約要求把 flag 印在 stdout 最後一行")
        return EXIT_FAIL

    ok, reason = compare_flag(found, private)
    if ok:
        log(f"✅ 通過（{reason}）")
        return EXIT_PASS

    log(f"❌ flag 比對失敗：{reason}")
    log(f"   取回長度 {len(found)} 字元；內容不列印以免寫進 CI log")
    return EXIT_FAIL


def main() -> int:
    parser = argparse.ArgumentParser(description="驗題：跑起題目、執行官方解、比對 flag")
    parser.add_argument("path", help="題目目錄，或包含多個題目的目錄")
    parser.add_argument("--timeout", type=int, default=120, help="解題腳本逾時秒數（預設 120）")
    parser.add_argument("--keep", action="store_true", help="結束後保留容器以便除錯")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        log(f"❌ 路徑不存在：{root}")
        return EXIT_ERROR

    if (root / "public.yml").exists():
        targets = [root]
    else:
        targets = sorted(p.parent for p in root.rglob("public.yml"))

    if not targets:
        log("找不到任何題目（缺少 public.yml？）")
        return EXIT_ERROR

    results: dict[int, list[str]] = {EXIT_PASS: [], EXIT_FAIL: [],
                                     EXIT_ERROR: [], EXIT_NOT_IMPLEMENTED: []}
    for chal_dir in targets:
        code = verify(chal_dir, args.timeout, args.keep)
        results.setdefault(code, []).append(chal_dir.name)

    log("\n" + "=" * 50)
    log(f"通過 {len(results[EXIT_PASS])} / "
        f"失敗 {len(results[EXIT_FAIL])} / "
        f"未實作 {len(results[EXIT_NOT_IMPLEMENTED])} / "
        f"錯誤 {len(results[EXIT_ERROR])}")
    for label, code in (("失敗", EXIT_FAIL), ("未實作", EXIT_NOT_IMPLEMENTED), ("錯誤", EXIT_ERROR)):
        if results[code]:
            log(f"  {label}：{', '.join(results[code])}")

    if results[EXIT_FAIL] or results[EXIT_ERROR]:
        return EXIT_FAIL
    if results[EXIT_NOT_IMPLEMENTED]:
        return EXIT_NOT_IMPLEMENTED
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
