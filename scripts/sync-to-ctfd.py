#!/usr/bin/env python3
"""
同步題目到 CTFd
================

把 challenges/ 底下的 public.yml / private.yml 推送到 CTFd。

設計原則
--------
1. **template repo 是唯一來源**，CTFd 只是部署目標。不要在 CTFd 後台改題目，
   改了下次同步就會被蓋掉。
2. **staging 寬鬆、production 嚴格**。staging 讓出題人隨時推上去實測；
   production 需要 ready_for_release 且狀態不在排除清單中。
3. **production 一律建成隱藏**。開賽時再由管理員統一開啟，
   避免同步腳本不小心提前公開題目。
4. **不列印 flag**。dry-run 與一般輸出都只顯示長度與類型。

用法
----
    # 先設好目標環境（建議放 .env，不要 commit）
    export CTFD_STAGING_URL=http://staging.example.com
    export CTFD_STAGING_TOKEN=ctfd_xxxxx

    # 推單一題目到 staging
    ./scripts/sync-to-ctfd.py --target staging --path challenges/web/my_chall

    # 先看會做什麼，不實際送出
    ./scripts/sync-to-ctfd.py --target staging --all --dry-run

    # 推所有通過檢查的題目到正式站
    ./scripts/sync-to-ctfd.py --target production --all

環境變數
--------
    CTFD_STAGING_URL / CTFD_STAGING_TOKEN
    CTFD_PRODUCTION_URL / CTFD_PRODUCTION_TOKEN
    （production 的 URL 若未設，會退回讀 config.yml 的 platform.ctfd_url）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Tuple

import challenge_schema as cs

try:
    import yaml
except ImportError:  # pragma: no cover
    print("❌ 需要 pyyaml：uv sync 或 pip install pyyaml", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent

# 這些狀態的題目不會推到 production（與 config.yml 的 public_release.exclude 同義）
DEFAULT_EXCLUDED_STATUSES = ["planning", "developing"]

# challenge_type → 是否為容器類（容器類的 flag 由 instancer 發，不在 CTFd 建靜態 flag）
CONTAINER_TYPES = {"static_container", "dynamic_container", "nc_challenge"}
DYNAMIC_TYPES = {"dynamic_container", "dynamic_attachment"}



# --------------------------------------------------------------------------- #
# 設定載入
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    """讀取 repo 根目錄的 config.yml"""
    config_path = REPO_ROOT / "config.yml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_target(target: str, config: dict) -> tuple[str, str]:
    """決定要推到哪個 CTFd，回傳 (base_url, token)"""
    prefix = f"CTFD_{target.upper()}"
    url = os.environ.get(f"{prefix}_URL", "").strip()
    token = os.environ.get(f"{prefix}_TOKEN", "").strip()

    if not url and target == "production":
        url = (config.get("platform", {}) or {}).get("ctfd_url", "").strip()

    if not url:
        sys.exit(
            f"❌ 找不到 {target} 的 CTFd URL。\n"
            f"   請設定環境變數 {prefix}_URL"
            + ("，或填好 config.yml 的 platform.ctfd_url" if target == "production" else "")
        )
    if not token:
        sys.exit(f"❌ 找不到 {target} 的 API token。請設定環境變數 {prefix}_TOKEN")

    return url.rstrip("/"), token


# --------------------------------------------------------------------------- #
# CTFd API client（只用標準庫，避免替專案增加依賴）
# --------------------------------------------------------------------------- #

class CTFdClient:
    def __init__(self, base_url: str, token: str, dry_run: bool = False):
        self.base_url = base_url
        self.token = token
        self.dry_run = dry_run

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"{method} {path} → HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"{method} {path} → 連線失敗: {e.reason}") from e

        if not body:
            return None
        parsed = json.loads(body)
        if isinstance(parsed, dict) and parsed.get("success") is False:
            raise RuntimeError(f"{method} {path} → API 回報失敗: {parsed.get('errors')}")
        return parsed

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, payload: dict) -> Any:
        if self.dry_run:
            return {"data": {"id": "<dry-run>"}}
        return self._request("POST", path, payload)

    def patch(self, path: str, payload: dict) -> Any:
        if self.dry_run:
            return {"data": {"id": "<dry-run>"}}
        return self._request("PATCH", path, payload)

    def delete(self, path: str) -> Any:
        if self.dry_run:
            return None
        return self._request("DELETE", path)

    def find_challenge_by_name(self, name: str) -> Optional[dict]:
        """以題目名稱查詢既有題目（用 admin view 才看得到隱藏題）"""
        query = urllib.parse.urlencode({"view": "admin"})
        result = self.get(f"/challenges?{query}")
        for chal in (result or {}).get("data", []):
            if chal.get("name") == name:
                return chal
        return None

    def check_auth(self) -> None:
        """確認 token 有效且具備管理權限"""
        try:
            self.get("/users/me")
        except RuntimeError as e:
            sys.exit(f"❌ CTFd 認證失敗：{e}")


# --------------------------------------------------------------------------- #
# 題目載入與檢查
# --------------------------------------------------------------------------- #

def discover_challenges(path: Path) -> list[Path]:
    """找出所有含 public.yml 的題目目錄"""
    if (path / "public.yml").exists():
        return [path]
    return sorted(p.parent for p in path.rglob("public.yml"))


def load_challenge(chal_dir: Path) -> tuple[dict, dict]:
    """讀取 public.yml 與（可選的）private.yml"""
    with open(chal_dir / "public.yml", "r", encoding="utf-8") as f:
        public = yaml.safe_load(f) or {}

    private: dict = {}
    private_path = chal_dir / "private.yml"
    if private_path.exists():
        with open(private_path, "r", encoding="utf-8") as f:
            private = yaml.safe_load(f) or {}

    return public, private


def gate(public: dict, private: dict, target: str, config: dict) -> list[str]:
    """回傳阻擋同步的原因；空清單代表通過"""
    problems: list[str] = []

    for field in ("title", "category", "description"):
        if not public.get(field):
            problems.append(f"public.yml 缺少必要欄位：{field}")

    if target != "production":
        return problems

    # 以下只在 production 檢查
    if not public.get("ready_for_release"):
        problems.append("ready_for_release 不是 true")

    excluded = (
        ((config.get("public_release", {}) or {}).get("exclude", {}) or {})
        .get("statuses", DEFAULT_EXCLUDED_STATUSES)
    )
    status = public.get("status")
    if status in excluded:
        problems.append(f"status 為 {status}（在排除清單中）")

    needs_flag = cs.needs_static_flag(private)
    if needs_flag and not private.get("flag"):
        problems.append("非動態題但 private.yml 沒有 flag")

    return problems


def resolve_points(public: dict, config: dict) -> int:
    """points 優先取 public.yml，沒有就用 config.yml 的難度對照表"""
    if isinstance(public.get("points"), int):
        return public["points"]
    difficulty = public.get("difficulty", "")
    points_map = config.get("points", {}) or {}
    return int(points_map.get(difficulty, 100))


def resolve_flag(private: dict) -> List[Tuple[str, str]]:
    """
    回傳要在 CTFd 建立的 flag 清單 [(content, ctfd_flag_type), ...]。

    依 private.yml 的 flag 三軸（見 docs/challenge-schema.md）判斷：

      - flag_load=dynamic 或 flag_scope=per_team → 不建靜態 flag（由插件發放時驗證），回 []
      - flag_match=regex → CTFd flag type=regex，`flag` 欄位本身即正規表達式
      - 否則             → CTFd flag type=static，精確比對
      - `flag` 可為單一字串或陣列（多個可接受答案）

    ⚠️ 不讀 `flag_format`（那是「flag 長什麼樣子」的註記，不是答案）。
    """
    load, scope, match = cs.flag_axes(private)
    if load == "dynamic" or scope == "per_team":
        return []
    flags = private.get("flag")
    if not flags:
        return []
    flags = flags if isinstance(flags, list) else [flags]
    ftype = cs.ctfd_flag_type(private)
    return [(str(f), ftype) for f in flags if f]


def check_flag_format(private: dict) -> Optional[str]:
    """flag 與 flag_format 不符時回傳警告字串（僅提示，不阻擋同步）"""
    import re

    flag = private.get("flag")
    fmt = private.get("flag_format")
    if not flag or not fmt or (private.get("flag_type") or "").lower() == "dynamic":
        return None
    try:
        if not re.fullmatch(str(fmt), str(flag)):
            return f"flag 不符合 flag_format（{fmt}）"
    except re.error:
        return f"flag_format 不是合法的正規表達式（{fmt}）"
    return None


# --------------------------------------------------------------------------- #
# 同步
# --------------------------------------------------------------------------- #

def build_description(public: dict) -> str:
    """組出送給 CTFd 的題目描述，附上作者與連線資訊"""
    parts = [str(public.get("description", "")).rstrip()]

    deploy = public.get("deploy_info", {}) or {}
    url = deploy.get("url")
    if url:
        parts.append(f"\n連線資訊：{url}")

    author = public.get("author")
    if author:
        parts.append(f"\n\n> 出題者：{author}")

    return "\n".join(p for p in parts if p)


def k3s_payload(public: dict, private: dict, config: dict, slug: str) -> dict:
    """把 container 題的 deploy_info + flag 三軸轉成 k3s_challenges 插件的建題欄位。

    只送「有值 / 需覆蓋」的欄位，其餘留給插件預設（image 為必填一定送）。
    對接契約見 docs/challenge-schema.md「container 題 → k3s」。

    slug 用題目目錄名（與 build-images 一致），確保 image tag 兩邊算得出同一個。
    """
    deploy = public.get("deploy_info") or {}
    payload: dict[str, Any] = {
        "image": cs.image_ref(config, cs.category(public), slug, cs.image_version(public)),
    }

    # port：nc 題用 nc_port，其餘用 port；都沒填就交給插件預設（1337）
    port = deploy.get("nc_port") if cs.is_nc(public) else deploy.get("port")
    if isinstance(port, int):
        payload["port"] = port

    # protocol：http/https → "http"，其餘（含 nc/pwn）→ "tcp"
    payload["protocol"] = "http" if cs.connection_type(public) in ("http", "https") else "tcp"

    # 資源限制：deploy_info.resources 有填才送，缺則用插件預設
    resources = deploy.get("resources") or {}
    if resources.get("memory"):
        payload["memory"] = str(resources["memory"])
    if resources.get("cpu"):
        payload["cpu"] = str(resources["cpu"])

    # flag_format：用 config 的 project.flag_prefix 前綴組出「前綴{答案}」樣式
    prefix = str(((config.get("project") or {}).get("flag_prefix") or "")).strip()
    if prefix:
        payload["flag_format"] = f"{prefix}{{%s}}"

    # flag_mode 必須跟插件 attempt() 與開 instance 時的注入對齊，否則 flag 對不上：
    #   • dynamic / per_team → 插件每 instance 用 flag_format 生成 flag 並注入 pod，
    #     attempt() 只比對該 instance 的 flag；sync 不建 CTFd 靜態 flag（resolve_flag 回 []）。
    #     注入用 file+env（同時給 flag_path 檔與 FLAG env），配合 template 的 ENV FLAG 慣例，
    #     題目讀檔或讀環境變數都拿得到——只給 file 會讓讀 env 的題目拿到空值。
    #   • static + shared → pod 不注入、flag 由 image 內建；attempt() 比對 CTFd 靜態 flag，
    #     而該靜態 flag 由 sync 的 resolve_flag/sync_flag 依 private.flag 建立。兩邊一致。
    load, scope, _ = cs.flag_axes(private)
    if load == "dynamic" or scope == "per_team":
        payload["flag_mode"] = "dynamic"
        payload["flag_delivery"] = "file+env"
    else:
        payload["flag_mode"] = "static"

    # --- deploy_info → 更多 k3s 欄位（全部只在 deploy_info 有填時才送，缺則用插件預設）---
    # sidecars：list（如自建的 bot/db 服務，image 名慣例是 {slug}-{service}）。
    #   插件的 sidecars 欄位收 JSON 字串（收到後 .strip() 再 json.loads），故這裡先 json.dumps。
    sidecars = deploy.get("sidecars")
    if isinstance(sidecars, list) and sidecars:
        payload["sidecars"] = json.dumps(sidecars)

    # allow_egress：bool（key 存在才送，讓作者能明確開或關對外連線）
    if "allow_egress" in deploy:
        payload["allow_egress"] = bool(deploy["allow_egress"])

    # ttl_minutes / max_renews：int（有填才送；排除 bool 誤填，因 bool 也是 int 子類）
    ttl = deploy.get("ttl_minutes")
    if isinstance(ttl, int) and not isinstance(ttl, bool):
        payload["ttl_minutes"] = ttl
    renews = deploy.get("max_renews")
    if isinstance(renews, int) and not isinstance(renews, bool):
        payload["max_renews"] = renews

    # run_as_user：k3s 用 PSA restricted + runAsNonRoot，pod 一定要有「數字 UID」才驗得過
    # 非 root（image 用 `USER 名字` 會讓 pod 起不來：CreateContainerConfigError）。所以這裡
    # **一律送**數字 UID，預設 1000（對齊 Dockerfile.template 釘的 uid 1000）；作者可用
    # deploy_info.run_as_user 覆蓋。這樣就算題目 image 忘了用數字 USER，pod 仍以 uid 1000 跑。
    ruid = deploy.get("run_as_user")
    payload["run_as_user"] = ruid if (isinstance(ruid, int) and not isinstance(ruid, bool)) else 1000

    return payload


def sync_challenge(
    client: CTFdClient,
    chal_dir: Path,
    public: dict,
    private: dict,
    config: dict,
    target: str,
) -> str:
    name = public["title"]
    existing = client.find_challenge_by_name(name)

    payload = {
        "name": name,
        "category": public.get("category", "misc"),
        "description": build_description(public),
        "value": resolve_points(public, config),
        "type": "standard",
        # staging 直接可見方便實測；production 一律建成隱藏，開賽時再統一開啟
        "state": "visible" if target == "staging" else "hidden",
    }

    # container 題 → 建成 k3s 型別並指向 registry 上的 image；
    # attachment/none 維持 standard。adapter 先併入，`ctfd:` 之後再 merge，
    # 讓作者能以 ctfd: 覆蓋任何 adapter 算出來的欄位。
    if cs.deploy_type(public) == "container":
        payload["type"] = "k3s"
        payload.update(k3s_payload(public, private, config, cs.slugify(chal_dir.name)))

    # public.yml 的 `ctfd:` 區塊原樣轉發給 CTFd API，本腳本不解讀內容。
    #
    # 這是刻意的解耦：不同的 CTFd 插件有不同的欄位（CTFd-Whale 用
    # docker_image/redirect_port，我們的用 slug/service_port…），
    # 若在這裡翻譯，template 就得反過來認識每一個插件。原樣轉發之後，
    # 換插件或換平台都不必動這支腳本，而且不使用 template 的題目
    # 也能在 CTFd 後台以完全相同的欄位手動建立。
    extra = public.get("ctfd") or {}
    if not isinstance(extra, dict):
        raise ValueError("public.yml 的 ctfd: 必須是一組鍵值")
    payload.update(extra)

    if existing:
        chal_id = existing["id"]
        # 已存在的題目不覆寫 state，避免把管理員手動開啟的題目改回隱藏
        payload.pop("state", None)
        # 型別與識別碼類欄位不可在既有題目上變更（插件那側也會擋），
        # 這裡先拿掉避免每次同步都收到無意義的 400
        for immutable in ("type", "slug"):
            payload.pop(immutable, None)
        client.patch(f"/challenges/{chal_id}", payload)
        action = "更新"
    else:
        created = client.post("/challenges", payload)
        chal_id = created["data"]["id"]
        action = "建立"

    sync_flag(client, chal_id, public, private)
    sync_hints(client, chal_id, public)
    sync_tags(client, chal_id, public)

    return f"{action} #{chal_id}"


def sync_flag(client: CTFdClient, chal_id: Any, public: dict, private: dict) -> None:
    # 動態/每隊 flag 由 instancer / 動態附件插件在發放時產生並驗證，
    # 不能在 CTFd 建靜態 flag，否則所有人共用同一個答案。resolve_flag 已據 flag 三軸判斷。
    resolved = resolve_flag(private)
    if not resolved:
        return

    if client.dry_run or chal_id == "<dry-run>":
        return

    # 先清掉既有 flag，避免舊 flag 殘留造成多個答案都能過
    existing = client.get(f"/challenges/{chal_id}/flags") or {}
    for flag in existing.get("data", []):
        client.delete(f"/flags/{flag['id']}")

    for content, flag_type in resolved:
        client.post("/flags", {"challenge": chal_id, "content": content, "type": flag_type})


def sync_hints(client: CTFdClient, chal_id: Any, public: dict) -> None:
    hints = public.get("hints") or []
    if not hints or client.dry_run or chal_id == "<dry-run>":
        return

    existing = client.get(f"/challenges/{chal_id}/hints") or {}
    for hint in existing.get("data", []):
        client.delete(f"/hints/{hint['id']}")

    # 依 level 排序，並讓高階提示以前一階為前置條件
    ordered = sorted(hints, key=lambda h: h.get("level", 0))
    previous_id = None
    for hint in ordered:
        content = str(hint.get("content", "")).strip()
        if not content:
            continue
        payload: dict[str, Any] = {
            "challenge_id": chal_id,
            "content": content,
            "cost": int(hint.get("cost", 0)),
        }
        if previous_id is not None:
            payload["requirements"] = {"prerequisites": [previous_id]}
        created = client.post("/hints", payload)
        previous_id = created["data"]["id"]


def sync_tags(client: CTFdClient, chal_id: Any, public: dict) -> None:
    tags = [t for t in (public.get("tags") or []) if t and not str(t).startswith("${")]
    if not tags or client.dry_run or chal_id == "<dry-run>":
        return

    existing = client.get(f"/challenges/{chal_id}/tags") or {}
    for tag in existing.get("data", []):
        client.delete(f"/tags/{tag['id']}")

    for tag in tags:
        client.post("/tags", {"challenge_id": chal_id, "value": str(tag)})


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _rel(path: Path) -> str:
    """相對於 repo 顯示；--path 指向 repo 外時退回絕對路徑而非拋例外。"""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def describe(chal_dir: Path, public: dict, private: dict, config: dict) -> str:
    kind = cs.kind(public)
    load, scope, _ = cs.flag_axes(private)
    resolved = resolve_flag(private)
    if load == "dynamic" or scope == "per_team":
        flag_note = "動態/每隊（由插件發放）"
    elif resolved:
        ftype = resolved[0][1]
        flag_note = f"{ftype}，{len(resolved)} 個" if len(resolved) > 1 else f"{ftype}，{len(resolved[0][0])} 字元"
    else:
        flag_note = "無"

    extra = public.get("ctfd") or {}
    slug_line = ""
    if extra:
        shown = ", ".join(f"{k}={v}" for k, v in list(extra.items())[:4])
        more = "…" if len(extra) > 4 else ""
        slug_line = f"    ctfd     : {shown}{more}\n"

    image_line = ""
    if cs.deploy_type(public) == "container":
        ref = cs.image_ref(config, cs.category(public), cs.slugify(chal_dir.name), cs.image_version(public))
        image_line = f"    image    : {ref}（type=k3s）\n"

    return (
        f"  {public.get('title', chal_dir.name)}\n"
        f"    路徑     : {_rel(chal_dir)}\n"
        f"{slug_line}"
        f"{image_line}"
        f"    分類/難度: {public.get('category', '—')} / {public.get('difficulty', '—')}\n"
        f"    交付     : {kind}\n"
        f"    分數     : {resolve_points(public, config)}\n"
        f"    Flag     : {flag_note}\n"
        f"    提示     : {len(public.get('hints') or [])} 則"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把題目從 template repo 同步到 CTFd",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target", choices=["staging", "production"], default="staging",
                        help="同步目標（預設 staging）")
    parser.add_argument("--path", default=None,
                        help="單一題目目錄，或要遞迴掃描的目錄")
    parser.add_argument("--all", action="store_true",
                        help="同步 challenges/ 底下所有題目")
    parser.add_argument("--dry-run", action="store_true",
                        help="只顯示會做什麼，不實際送出")
    parser.add_argument("--include-examples", action="store_true",
                        help="一併同步 challenges/examples/（預設略過）")
    args = parser.parse_args()

    if not args.path and not args.all:
        parser.error("請指定 --path 或 --all")

    config = load_config()
    root = Path(args.path).resolve() if args.path else (REPO_ROOT / "challenges")
    if not root.exists():
        sys.exit(f"❌ 路徑不存在：{root}")

    challenges = discover_challenges(root)
    if not args.include_examples:
        challenges = [c for c in challenges if "examples" not in c.parts]

    if not challenges:
        print("找不到任何題目（缺少 public.yml？）")
        return 0

    print(f"目標：{args.target}{'（dry-run）' if args.dry_run else ''}")
    print(f"找到 {len(challenges)} 個題目\n")

    client: Optional[CTFdClient] = None
    if not args.dry_run:
        base_url, token = resolve_target(args.target, config)
        client = CTFdClient(base_url, token)
        client.check_auth()
        print(f"已連線：{base_url}\n")
    else:
        client = CTFdClient("http://dry-run.invalid", "dry-run", dry_run=True)

    synced, skipped, failed = 0, 0, 0

    for chal_dir in challenges:
        try:
            public, private = load_challenge(chal_dir)
        except yaml.YAMLError as e:
            print(f"❌ {chal_dir.name}：YAML 解析失敗 — {e}")
            failed += 1
            continue

        problems = gate(public, private, args.target, config)
        if problems:
            print(f"⏭️  略過 {public.get('title', chal_dir.name)}")
            for problem in problems:
                print(f"      · {problem}")
            skipped += 1
            continue

        warning = check_flag_format(private)
        if warning:
            print(f"⚠️  {public.get('title', chal_dir.name)} — {warning}")

        if args.dry_run:
            print(f"📋 會同步：")
            print(describe(chal_dir, public, private, config))
            print()
            synced += 1
            continue

        try:
            result = sync_challenge(client, chal_dir, public, private, config, args.target)
            print(f"✅ {public['title']} — {result}")
            synced += 1
        except RuntimeError as e:
            print(f"❌ {public.get('title', chal_dir.name)} — {e}")
            failed += 1

    print(f"\n完成：{synced} 同步 / {skipped} 略過 / {failed} 失敗")

    if args.target == "production" and synced and not args.dry_run:
        print("\n⚠️  新建立的題目都是隱藏狀態，開賽時請到 CTFd 後台統一開啟。")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
