#!/usr/bin/env python3
"""
IS1AB CTF Template - 現代化 Web 介面
整合版本：使用 Flask + Jinja2 + Bulma CSS
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
import subprocess
import time

# 讓 scripts/setup_helpers.py 可被 import
import sys as _sys
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPTS_DIR))

# Flask 相關套件
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from flask_assets import Bundle, Environment
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# 應用程式配置
app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = "is1ab-ctf-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# 配置目錄
BASE_DIR = Path(__file__).parent.parent
CHALLENGES_DIR = BASE_DIR / "challenges"
CONFIG_FILE = BASE_DIR / "config.yml"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# 創建必要的目錄
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

# 設定模板目錄
app.template_folder = str(TEMPLATES_DIR)
app.static_folder = str(STATIC_DIR)

# 配置 Flask-Assets
assets = Environment(app)
assets.url = app.static_url_path

# CSS Bundle - 包含 Bulma 和自定義樣式
css_bundle = Bundle("css/custom.css", output="css/bundle.css", filters="cssmin")
assets.register("css_all", css_bundle)

# JS Bundle
js_bundle = Bundle("js/main.js", output="js/bundle.js", filters="jsmin")
assets.register("js_all", js_bundle)


class CTFManager:
    """CTF 管理核心類別"""

    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """載入配置檔案"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
                raw_config = yaml.safe_load(config_file)

            # 適配配置結構
            project = raw_config.get("project", {}) or {}
            team = raw_config.get("team", {}) or {}
            reviewers = team.get("reviewers") or []
            if isinstance(reviewers, list):
                reviewers = [r for r in reviewers if r and str(r).strip()]
            else:
                reviewers = []

            authors = team.get("authors") or []
            if isinstance(authors, list):
                authors = [a for a in authors if a and str(a).strip()]
            else:
                authors = []

            # team.members（新 schema）
            raw_members = team.get("members") or []
            members: List[Dict[str, str]] = []
            seen_usernames: set = set()
            if isinstance(raw_members, list):
                for entry in raw_members:
                    if not isinstance(entry, dict):
                        continue
                    username = str(entry.get("github_username") or "").strip()
                    if not username or username in seen_usernames:
                        continue
                    seen_usernames.add(username)
                    members.append({
                        "github_username": username,
                        "display_name": str(entry.get("display_name") or username).strip(),
                        "specialty": str(entry.get("specialty") or "").strip(),
                    })

            # Backward compat: 若 members 為空但舊欄位有值，自動遷移
            if not members:
                default_author = (team.get("default_author") or "").strip()
                migrate_pool = list(reviewers) + list(authors)
                if default_author:
                    migrate_pool.append(default_author)
                for username in migrate_pool:
                    username = str(username).strip()
                    if not username or username in seen_usernames:
                        continue
                    seen_usernames.add(username)
                    members.append({
                        "github_username": username,
                        "display_name": username,
                        "specialty": "",
                    })

            event = raw_config.get("event", {}) or {}

            config = {
                "competition_name": project.get("name", "IS1AB CTF"),
                "organization": project.get("organization", "IS1AB"),
                "description": project.get("description", "IS1AB CTF Competition"),
                "year": project.get("year", ""),
                "project_flag_prefix": (project.get("flag_prefix") or "").strip(),
                "event": {
                    "start_date": (event.get("start_date") or "").strip(),
                    "end_date": (event.get("end_date") or "").strip(),
                    "authoring_deadline": (event.get("authoring_deadline") or "").strip(),
                    "review_deadline": (event.get("review_deadline") or "").strip(),
                    "freeze_deadline": (event.get("freeze_deadline") or "").strip(),
                },
                "deployment": raw_config.get("deployment", {}) or {},
                "platform": raw_config.get("platform", {}) or {},
                "categories": ["web", "pwn", "crypto", "misc", "reverse", "forensic"],
                "difficulties": ["baby", "easy", "middle", "hard", "impossible"],
                "challenge_quota": raw_config.get("challenge_quota", {}),
                "points": raw_config.get("points", {}),
                "default_author": (team.get("default_author") or "").strip(),
                "reviewers": reviewers,
                "authors": authors,
                "members": members,
            }

            # 從 challenge_quota 提取類別
            if (
                "challenge_quota" in raw_config
                and "by_category" in raw_config["challenge_quota"]
            ):
                config["categories"] = list(
                    raw_config["challenge_quota"]["by_category"].keys()
                )

            # 從 points 提取難度
            if "points" in raw_config:
                config["difficulties"] = list(raw_config["points"].keys())

            return config

        except FileNotFoundError:
            return {
                "competition_name": "IS1AB CTF",
                "organization": "IS1AB",
                "description": "IS1AB CTF Competition",
                "categories": ["web", "pwn", "crypto", "misc", "reverse"],
                "difficulties": ["baby", "easy", "middle", "hard"],
                "default_author": "",
                "reviewers": [],
                "authors": [],
                "members": [],
                "project_flag_prefix": "",
                "year": "",
                "event": {
                    "start_date": "",
                    "end_date": "",
                    "authoring_deadline": "",
                    "review_deadline": "",
                    "freeze_deadline": "",
                },
                "deployment": {},
                "platform": {},
            }

    def guess_git_author(self) -> str:
        """從 git config 推測作者名稱（user.name），失敗則回傳空字串。"""
        try:
            proc = subprocess.run(
                ["git", "config", "--get", "user.name"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                return (proc.stdout or "").strip()
        except Exception:
            return ""
        return ""

    def get_setup_missing_items(self) -> List[str]:
        """檢查全新專案初始化是否已完成。回傳缺少的項目描述清單。"""
        missing: List[str] = []

        quota = self.config.get("challenge_quota") or {}
        by_category = (quota.get("by_category") or {}) if isinstance(quota, dict) else {}
        by_difficulty = (quota.get("by_difficulty") or {}) if isinstance(quota, dict) else {}
        total_target = quota.get("total_target") if isinstance(quota, dict) else None

        if not isinstance(by_category, dict) or not by_category:
            missing.append("題目類型 / 分類配額（challenge_quota.by_category）")
        if not isinstance(by_difficulty, dict) or not by_difficulty:
            missing.append("難度配額（challenge_quota.by_difficulty）")
        if not total_target:
            missing.append("總題目數目標（challenge_quota.total_target）")

        if not (self.config.get("default_author") or "").strip():
            missing.append("預設出題人（team.default_author）")
        reviewers = self.config.get("reviewers") or []
        if not isinstance(reviewers, list) or len(reviewers) == 0:
            missing.append("驗題人清單（team.reviewers）")

        event = self.config.get("event") or {}
        if not (event.get("start_date") or "").strip():
            missing.append("舉辦開始時間（event.start_date）")
        if not (event.get("end_date") or "").strip():
            missing.append("舉辦結束時間（event.end_date）")
        if not (event.get("authoring_deadline") or "").strip():
            missing.append("出題截止（event.authoring_deadline）")
        if not (event.get("review_deadline") or "").strip():
            missing.append("驗題截止（event.review_deadline）")
        if not (event.get("freeze_deadline") or "").strip():
            missing.append("凍結截止（event.freeze_deadline）")

        return missing

    def is_setup_complete(self) -> bool:
        return len(self.get_setup_missing_items()) == 0

    def compute_step_status(self) -> Dict[str, str]:
        """為 wizard 5 步驟計算進度條狀態。

        回傳 dict： step_name → "pending" | "done"
        """
        statuses: Dict[str, str] = {}

        # Step 1: project
        project_name = (self.config.get("competition_name") or "").strip()
        flag_prefix = (self.config.get("project_flag_prefix") or "").strip()
        statuses["project"] = "done" if (project_name and flag_prefix) else "pending"

        # Step 2: team
        members = self.config.get("members") or []
        statuses["team"] = "done" if any(
            (m.get("github_username") or "").strip() for m in members
        ) else "pending"

        # Step 3: event
        event = self.config.get("event") or {}
        statuses["event"] = "done" if (
            event.get("start_date", "").strip() and event.get("end_date", "").strip()
        ) else "pending"

        # Step 4: quota
        quota = self.config.get("challenge_quota") or {}
        by_category = quota.get("by_category") or {}
        total_target = quota.get("total_target") or 0
        statuses["quota"] = "done" if (
            total_target and any(v > 0 for v in by_category.values())
        ) else "pending"

        # Step 5: finalize（.github 兩檔案存在 + 偵測到的冗餘欄位 = 0）
        gh_dir = BASE_DIR / ".github"
        pr_tmpl = gh_dir / "PULL_REQUEST_TEMPLATE.md"
        codeowners = gh_dir / "CODEOWNERS"
        if pr_tmpl.exists() and codeowners.exists():
            try:
                from setup_helpers import detect_legacy_validation_fields
                legacy_count = len(detect_legacy_validation_fields(CHALLENGES_DIR))
            except Exception:
                legacy_count = 0
            statuses["finalize"] = "done" if legacy_count == 0 else "pending"
        else:
            statuses["finalize"] = "pending"

        return statuses

    def save_setup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新 config.yml 的初始化欄位（僅限必要區塊）。"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
                raw_config = yaml.safe_load(config_file) or {}
        except FileNotFoundError:
            raw_config = {}

        if not isinstance(raw_config, dict):
            raw_config = {}

        raw_config.setdefault("project", {})
        raw_config.setdefault("team", {})
        raw_config.setdefault("challenge_quota", {})
        raw_config.setdefault("event", {})

        project = raw_config.get("project") or {}
        team = raw_config.get("team") or {}
        quota = raw_config.get("challenge_quota") or {}
        event = raw_config.get("event") or {}

        project["name"] = (data.get("project_name") or project.get("name") or "").strip()
        project["organization"] = (data.get("organization") or project.get("organization") or "").strip()
        project["description"] = (data.get("description") or project.get("description") or "").strip()
        year = (data.get("year") or project.get("year") or "").strip()
        if year:
            project["year"] = int(year) if str(year).isdigit() else year

        team["default_author"] = (data.get("default_author") or "").strip()
        reviewers_raw = data.get("reviewers") or ""
        reviewers = [r.strip() for r in str(reviewers_raw).split(",") if r.strip()]
        team["reviewers"] = reviewers

        authors_raw = data.get("authors") or ""
        authors = [a.strip() for a in str(authors_raw).split(",") if a.strip()]
        team["authors"] = authors

        def _parse_quota_map(text: str) -> Dict[str, int]:
            result: Dict[str, int] = {}
            for pair in [p.strip() for p in str(text or "").split(",") if p.strip()]:
                if ":" not in pair:
                    continue
                k, v = pair.split(":", 1)
                k = k.strip()
                v = v.strip()
                if not k:
                    continue
                try:
                    result[k] = int(v)
                except ValueError:
                    continue
            return result

        by_category_text = data.get("by_category") or ""
        by_difficulty_text = data.get("by_difficulty") or ""
        if by_category_text:
            quota["by_category"] = _parse_quota_map(by_category_text)
        if by_difficulty_text:
            quota["by_difficulty"] = _parse_quota_map(by_difficulty_text)
        total_target = (data.get("total_target") or "").strip()
        if total_target:
            try:
                quota["total_target"] = int(total_target)
            except ValueError:
                pass

        event["start_date"] = (data.get("start_date") or "").strip()
        event["end_date"] = (data.get("end_date") or "").strip()
        event["authoring_deadline"] = (data.get("authoring_deadline") or "").strip()
        event["review_deadline"] = (data.get("review_deadline") or "").strip()
        event["freeze_deadline"] = (data.get("freeze_deadline") or "").strip()

        raw_config["project"] = project
        raw_config["team"] = team
        raw_config["challenge_quota"] = quota
        raw_config["event"] = event

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(
                raw_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        self.config = self.load_config()
        remaining = self.get_setup_missing_items()
        if remaining:
            return {
                "status": "error",
                "message": "初始化設定尚未完整，仍缺少: " + "、".join(remaining),
            }
        return {"status": "success", "message": "初始化設定完成"}

    VALID_SETUP_STEPS = {"project", "team", "event", "quota"}

    def save_setup_step(self, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """寫入單一 wizard 步驟的欄位至 config.yml。"""
        if step not in self.VALID_SETUP_STEPS:
            return {
                "status": "error",
                "message": f"無效步驟: {step}（合法: {sorted(self.VALID_SETUP_STEPS)}）",
            }

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}

        raw.setdefault("project", {})
        raw.setdefault("team", {})
        raw.setdefault("event", {})
        raw.setdefault("challenge_quota", {})

        if step == "project":
            project = raw["project"]
            project["name"] = (data.get("project_name") or project.get("name") or "").strip()
            project["organization"] = (data.get("organization") or project.get("organization") or "").strip()
            project["description"] = (data.get("description") or project.get("description") or "").strip()
            project["flag_prefix"] = (data.get("flag_prefix") or project.get("flag_prefix") or "").strip()
            year = (data.get("year") or "").strip()
            if year:
                project["year"] = int(year) if year.isdigit() else year
            raw.setdefault("platform", {})
            raw.setdefault("deployment", {})
            for k in ("gzctf_url", "ctfd_url", "zipline_url"):
                if k in data:
                    raw["platform"][k] = (data.get(k) or "").strip()
            for k in ("host", "docker_registry"):
                if k in data:
                    raw["deployment"][k] = (data.get(k) or "").strip()

        elif step == "team":
            team = raw["team"]
            team["default_author"] = (data.get("default_author") or "").strip()
            members_raw = data.get("members") or []
            cleaned: List[Dict[str, str]] = []
            seen: set = set()
            for entry in members_raw:
                if not isinstance(entry, dict):
                    continue
                username = str(entry.get("github_username") or "").strip()
                if not username or username in seen:
                    continue
                seen.add(username)
                cleaned.append({
                    "github_username": username,
                    "display_name": str(entry.get("display_name") or username).strip(),
                    "specialty": str(entry.get("specialty") or "").strip(),
                })
            team["members"] = cleaned

        elif step == "event":
            event = raw["event"]
            for k in ("start_date", "end_date", "authoring_deadline", "review_deadline", "freeze_deadline"):
                event[k] = (data.get(k) or "").strip()

        elif step == "quota":
            quota = raw["challenge_quota"]
            quota["by_category"] = {
                str(k).strip(): int(v)
                for k, v in (data.get("by_category") or {}).items()
                if str(k).strip() and str(v).isdigit()
            }
            quota["by_difficulty"] = {
                str(k).strip(): int(v)
                for k, v in (data.get("by_difficulty") or {}).items()
                if str(k).strip() and str(v).isdigit()
            }
            tt = (data.get("total_target") or "").strip()
            if tt and tt.isdigit():
                quota["total_target"] = int(tt)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self.config = self.load_config()
        return {"status": "success", "message": f"已儲存 {step} 設定"}

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """以白名單方式更新 config.yml 指定區塊。"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
                raw_config = yaml.safe_load(config_file) or {}
        except FileNotFoundError:
            raw_config = {}

        if not isinstance(raw_config, dict):
            raw_config = {}

        raw_config.setdefault("team", {})
        raw_config.setdefault("event", {})
        raw_config.setdefault("points", {})
        raw_config.setdefault("challenge_quota", {})
        raw_config.setdefault("deployment", {})
        raw_config.setdefault("platform", {})

        team = raw_config.get("team") or {}
        event = raw_config.get("event") or {}
        points = raw_config.get("points") or {}
        quota = raw_config.get("challenge_quota") or {}
        deployment = raw_config.get("deployment") or {}
        platform = raw_config.get("platform") or {}

        if "team" in patch:
            team_patch = patch.get("team") or {}
            if "default_author" in team_patch:
                team["default_author"] = (team_patch.get("default_author") or "").strip()
            if "reviewers" in team_patch:
                reviewers = team_patch.get("reviewers") or []
                if isinstance(reviewers, str):
                    reviewers = [r.strip() for r in reviewers.split(",") if r.strip()]
                if isinstance(reviewers, list):
                    team["reviewers"] = [str(r).strip() for r in reviewers if str(r).strip()]
            if "authors" in team_patch:
                authors = team_patch.get("authors") or []
                if isinstance(authors, str):
                    authors = [a.strip() for a in authors.split(",") if a.strip()]
                if isinstance(authors, list):
                    team["authors"] = [str(a).strip() for a in authors if str(a).strip()]

        if "event" in patch:
            event_patch = patch.get("event") or {}
            for k in [
                "start_date",
                "end_date",
                "authoring_deadline",
                "review_deadline",
                "freeze_deadline",
            ]:
                if k in event_patch:
                    event[k] = (event_patch.get(k) or "").strip()

        if "points" in patch:
            pts_patch = patch.get("points") or {}
            new_points: Dict[str, int] = {}
            for k, v in pts_patch.items():
                key = str(k).strip()
                if not key:
                    continue
                try:
                    new_points[key] = int(v)
                except (ValueError, TypeError):
                    continue
            if not new_points:
                return {"status": "error", "message": "分數設定不可為空，請至少提供一個難度分數"}
            raw_config["points"] = new_points

        if "challenge_quota" in patch:
            quota_patch = patch.get("challenge_quota") or {}
            quota.setdefault("by_category", {})
            quota.setdefault("by_difficulty", {})
            for map_key in ["by_category", "by_difficulty"]:
                if map_key in quota_patch:
                    incoming = quota_patch.get(map_key) or {}
                    if isinstance(incoming, str):
                        # 支援 "web:6, pwn:6" 格式
                        parsed: Dict[str, int] = {}
                        for pair in [p.strip() for p in incoming.split(",") if p.strip()]:
                            if ":" not in pair:
                                continue
                            kk, vv = pair.split(":", 1)
                            kk = kk.strip()
                            vv = vv.strip()
                            if not kk:
                                continue
                            try:
                                parsed[kk] = int(vv)
                            except ValueError:
                                continue
                        incoming = parsed
                    if isinstance(incoming, dict):
                        cleaned: Dict[str, int] = {}
                        for kk, vv in incoming.items():
                            kks = str(kk).strip()
                            if not kks:
                                continue
                            try:
                                cleaned[kks] = int(vv)
                            except (ValueError, TypeError):
                                continue
                        quota[map_key] = cleaned
            if "total_target" in quota_patch:
                try:
                    quota["total_target"] = int(quota_patch.get("total_target"))
                except (ValueError, TypeError):
                    pass

        if "deployment" in patch:
            dep_patch = patch.get("deployment") or {}
            for k in ["host", "port_range", "docker_registry", "ssh_user"]:
                if k in dep_patch:
                    deployment[k] = (dep_patch.get(k) or "").strip()

        if "platform" in patch:
            plat_patch = patch.get("platform") or {}
            for k in ["gzctf_url", "ctfd_url", "zipline_url"]:
                if k in plat_patch:
                    platform[k] = (plat_patch.get(k) or "").strip()

        raw_config["team"] = team
        raw_config["event"] = event
        raw_config["challenge_quota"] = quota
        raw_config["deployment"] = deployment
        raw_config["platform"] = platform
        if "points" not in raw_config:
            raw_config["points"] = points

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(
                raw_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        self.config = self.load_config()
        return {"status": "success", "message": "設定已更新"}

    def get_challenges_with_quota(self) -> Dict[str, Any]:
        """獲取挑戰列表並包含配額信息"""
        challenges = self.get_challenges()

        # 按類別統計已出題目
        by_category = {}
        for category in self.config.get("categories", []):
            category_challenges = [
                c for c in challenges if c.get("category") == category
            ]
            quota = (
                self.config.get("challenge_quota", {})
                .get("by_category", {})
                .get(category, 0)
            )
            by_category[category] = {
                "published": category_challenges,
                "published_count": len(category_challenges),
                "quota": quota,
                "remaining": max(0, quota - len(category_challenges)),
            }

        # 按難度統計已出題目
        by_difficulty = {}
        for difficulty in self.config.get("difficulties", []):
            difficulty_challenges = [
                c for c in challenges if c.get("difficulty") == difficulty
            ]
            quota = (
                self.config.get("challenge_quota", {})
                .get("by_difficulty", {})
                .get(difficulty, 0)
            )
            by_difficulty[difficulty] = {
                "published": difficulty_challenges,
                "published_count": len(difficulty_challenges),
                "quota": quota,
                "remaining": max(0, quota - len(difficulty_challenges)),
            }

        return {
            "challenges": challenges,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "total_published": len(challenges),
            "total_quota": self.config.get("challenge_quota", {}).get(
                "total_target", 0
            ),
        }

    def get_challenges(self) -> List[Dict[str, Any]]:
        """獲取挑戰列表"""
        challenges = []

        try:
            for category_dir in CHALLENGES_DIR.iterdir():
                if not category_dir.is_dir():
                    continue

                category = category_dir.name
                for challenge_dir in category_dir.iterdir():
                    if not challenge_dir.is_dir():
                        continue

                    public_yml = challenge_dir / "public.yml"
                    if public_yml.exists():
                        try:
                            with open(public_yml, "r", encoding="utf-8") as yml_file:
                                challenge_data = yaml.safe_load(yml_file)

                            challenge_data.update(
                                {
                                    "category": category,
                                    "name": challenge_dir.name,
                                    "path": str(challenge_dir),
                                }
                            )
                            challenges.append(challenge_data)
                        except Exception as load_error:
                            print(f"載入挑戰失敗 {challenge_dir}: {load_error}")

        except Exception as list_error:
            print(f"載入挑戰列表失敗: {list_error}")

        return challenges

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資料"""
        challenges = self.get_challenges()

        stats = {
            "total_challenges": len(challenges),
            "by_category": {},
            "by_difficulty": {},
            "total_points": 0,
        }

        for challenge in challenges:
            category = challenge.get("category", "unknown")
            difficulty = challenge.get("difficulty", "unknown")
            points = challenge.get("points", 0)

            # 確保 points 是整數類型
            try:
                points = int(points) if points else 0
            except (ValueError, TypeError):
                points = 0

            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            stats["by_difficulty"][difficulty] = (
                stats["by_difficulty"].get(difficulty, 0) + 1
            )
            stats["total_points"] += points

        return stats

    def get_validation_queue(self) -> List[Dict[str, Any]]:
        """待驗題清單：僅包含已標記 validation_status 且非 approved 的題目（新流程）。"""
        pending: List[Dict[str, Any]] = []
        for challenge in self.get_challenges():
            status = challenge.get("validation_status")
            if status is None:
                continue
            if status != "approved":
                pending.append(challenge)
        pending.sort(
            key=lambda c: (c.get("category", ""), c.get("name", "")),
        )
        return pending

    def review_challenge(
        self,
        category: str,
        name: str,
        action: str,
        actor: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """更新驗題狀態（寫入 private.yml 並同步 public.yml）。"""
        valid_actions = {"approve", "reject", "pending"}
        if action not in valid_actions:
            return {
                "status": "error",
                "message": f"無效動作，請使用: {', '.join(sorted(valid_actions))}",
            }
        if not actor.strip():
            return {"status": "error", "message": "請提供驗題人識別（actor）"}

        challenge_path = CHALLENGES_DIR / category / name
        private_yml_path = challenge_path / "private.yml"
        if not private_yml_path.exists():
            return {"status": "error", "message": "題目不存在或缺少 private.yml"}

        with open(private_yml_path, "r", encoding="utf-8") as file:
            updated_config = yaml.safe_load(file) or {}

        status_map = {
            "approve": "approved",
            "reject": "rejected",
            "pending": "pending",
        }
        updated_config["validation_status"] = status_map[action]
        prev_notes = updated_config.get("internal_validation_notes") or ""
        timestamp = datetime.now().isoformat()
        line = f"[{timestamp}] {actor.strip()}: {action} — {notes.strip()}"
        updated_config["internal_validation_notes"] = (
            (prev_notes + "\n" if prev_notes else "") + line
        ).strip()
        updated_config["updated_at"] = timestamp

        with open(private_yml_path, "w", encoding="utf-8") as file:
            yaml.dump(
                updated_config,
                file,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        public_config = {
            k: v
            for k, v in updated_config.items()
            if not k.startswith(("flag", "solution_", "internal_", "testing"))
        }
        if "hints" in public_config:
            public_config["hints"] = [
                {"level": h["level"], "cost": h["cost"]}
                for h in public_config.get("hints", [])
                if isinstance(h, dict)
            ]
        public_yml_path = challenge_path / "public.yml"
        with open(public_yml_path, "w", encoding="utf-8") as file:
            yaml.dump(
                public_config,
                file,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return {
            "status": "success",
            "message": f"驗題狀態已更新為 {updated_config['validation_status']}",
            "data": {
                "validation_status": updated_config["validation_status"],
            },
        }

    def _append_internal_log(
        self,
        category: str,
        name: str,
        line: str,
    ) -> None:
        challenge_path = CHALLENGES_DIR / category / name
        private_yml_path = challenge_path / "private.yml"
        if not private_yml_path.exists():
            raise FileNotFoundError("題目不存在或缺少 private.yml")
        with open(private_yml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        prev = cfg.get("internal_validation_notes") or ""
        cfg["internal_validation_notes"] = ((prev + "\n" if prev else "") + line).strip()
        cfg["updated_at"] = datetime.now().isoformat()
        with open(private_yml_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def run_scan_secrets(self, category: str, name: str) -> Dict[str, Any]:
        """對單一題目執行敏感資料掃描（scan-secrets.py）。"""
        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return {"status": "error", "message": "題目不存在"}

        cmd = [
            "python",
            str(BASE_DIR / "scripts" / "scan-secrets.py"),
            "--path",
            str(challenge_path),
            "--verbose",
        ]
        started = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        elapsed_ms = int((time.time() - started) * 1000)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        status = "success" if proc.returncode == 0 else "error"
        line = f"[{datetime.now().isoformat()}] scan-secrets exit={proc.returncode} elapsed_ms={elapsed_ms}"
        self._append_internal_log(category, name, line)
        return {
            "status": status,
            "message": "掃描完成" if status == "success" else "掃描失敗",
            "data": {
                "exit_code": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "output": output.strip(),
            },
        }

    def run_build_public(self, category: str, name: str, force: bool = True) -> Dict[str, Any]:
        """對單一題目執行 public-release 建置（build.sh）。"""
        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return {"status": "error", "message": "題目不存在"}

        cmd = [
            str(BASE_DIR / "scripts" / "build.sh"),
            "--challenge",
            str(challenge_path),
        ]
        if force:
            cmd.append("--force")

        started = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        elapsed_ms = int((time.time() - started) * 1000)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        status = "success" if proc.returncode == 0 else "error"
        line = f"[{datetime.now().isoformat()}] build.sh exit={proc.returncode} elapsed_ms={elapsed_ms}"
        self._append_internal_log(category, name, line)
        return {
            "status": status,
            "message": "建置完成" if status == "success" else "建置失敗",
            "data": {
                "exit_code": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "output": output.strip(),
            },
        }

    def run_build_all_public(self, force: bool = True) -> Dict[str, Any]:
        """建置所有題目到 public-release（build.sh）。"""
        cmd = [str(BASE_DIR / "scripts" / "build.sh")]
        if force:
            cmd.append("--force")

        started = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        elapsed_ms = int((time.time() - started) * 1000)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

        status = "success" if proc.returncode == 0 else "error"
        return {
            "status": status,
            "message": "建置完成" if status == "success" else "建置失敗",
            "data": {
                "exit_code": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "output": output.strip(),
            },
        }

    def run_sync_to_public(self) -> Dict[str, Any]:
        """同步 ready_for_release 題目到 public-release（sync-to-public.py）。"""
        cmd = [
            "python",
            str(BASE_DIR / "scripts" / "sync-to-public.py"),
            "--config",
            str(BASE_DIR / "config.yml"),
        ]
        started = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        elapsed_ms = int((time.time() - started) * 1000)
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        status = "success" if proc.returncode == 0 else "error"
        return {
            "status": status,
            "message": "同步完成" if status == "success" else "同步失敗",
            "data": {
                "exit_code": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "output": output.strip(),
            },
        }

    def create_challenge(self, challenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """創建新挑戰"""
        try:
            # 提取必要參數
            name = challenge_data.get("name", "").strip()
            category = challenge_data.get("category", "").strip()
            difficulty = challenge_data.get("difficulty", "easy").strip()
            author = (challenge_data.get("author") or "").strip()
            reviewer = (challenge_data.get("reviewer") or "").strip()
            description = challenge_data.get("description", "").strip()
            challenge_type = challenge_data.get(
                "challenge_type", "static_container"
            ).strip()

            valid_categories = list(self.config.get("categories", [])) or [
                "web",
                "pwn",
                "reverse",
                "crypto",
                "forensic",
                "misc",
            ]

            # 基本驗證
            if not name or not category:
                return {"status": "error", "message": "題目名稱和分類不能為空"}

            # 出題人：可填寫；若空白則使用 config 的 team.default_author，再不行就抓 git user.name
            if not author:
                author = (self.config.get("default_author") or "").strip()
            if not author:
                author = self.guess_git_author()
            if not author:
                return {
                    "status": "error",
                    "message": "請填寫出題人，或在專案根目錄 config.yml 設定 team.default_author / team.authors，或先設定 git user.name",
                }

            if not reviewer:
                return {
                    "status": "error",
                    "message": "請填寫驗題人（或從建議名單選取）；亦可在 config.yml 的 team.reviewers 建立建議驗題人清單",
                }

            # 驗證名稱格式
            if not name.replace("_", "").replace("-", "").isalnum():
                return {
                    "status": "error",
                    "message": "題目名稱只能包含字母、數字、底線和連字號",
                }

            # 驗證分類
            if category not in valid_categories:
                return {
                    "status": "error",
                    "message": f"無效的分類，有效分類: {', '.join(valid_categories)}",
                }

            # 驗證難度
            valid_difficulties = ["baby", "easy", "middle", "hard", "impossible"]
            if difficulty not in valid_difficulties:
                return {
                    "status": "error",
                    "message": f"無效的難度，有效難度: {', '.join(valid_difficulties)}",
                }

            # 創建題目目錄
            challenge_path = CHALLENGES_DIR / category / name
            if challenge_path.exists():
                return {"status": "error", "message": f"題目 {category}/{name} 已存在"}

            # 創建目錄結構
            challenge_path.mkdir(parents=True, exist_ok=True)

            # 創建子目錄
            subdirs = ["src", "files", "writeup"]
            if challenge_type in ["static_container", "dynamic_container"]:
                subdirs.extend(["docker", "bin"])

            for subdir in subdirs:
                (challenge_path / subdir).mkdir(exist_ok=True)

            # 創建 private.yml 配置
            private_config = {
                "title": challenge_data.get("title", name),
                "author": author,
                "reviewer": reviewer,
                "validation_status": "pending",
                "internal_validation_notes": "",
                "difficulty": difficulty,
                "category": category,
                "description": description,
                "challenge_type": challenge_type,
                "source_code_provided": challenge_data.get(
                    "source_code_provided", False
                ),
                "files": challenge_data.get("files", []),
                "status": challenge_data.get("status", "developing"),
                "points": challenge_data.get(
                    "points", self.config.get("points", {}).get(difficulty, 100)
                ),
                "tags": challenge_data.get("tags", [category, difficulty]),
                "created_at": datetime.now().isoformat(),
                "deploy_info": {
                    "port": challenge_data.get("deploy_info", {}).get("port", 8080),
                    "url": challenge_data.get("deploy_info", {}).get("url", ""),
                    "requires_build": challenge_data.get("deploy_info", {}).get(
                        "requires_build", True
                    ),
                    "resources": challenge_data.get("deploy_info", {}).get(
                        "resources", {"memory": "256Mi", "cpu": "100m"}
                    ),
                },
                "hints": challenge_data.get(
                    "hints",
                    [{"level": 1, "cost": 0, "content": "第一個提示，通常是免費的。"}],
                ),
                "flag": challenge_data.get("flag", f"is1abCTF{{{name}_example_flag}}"),
                "flag_description": challenge_data.get(
                    "flag_description", "Flag 位置的描述"
                ),
                "solution_steps": challenge_data.get(
                    "solution_steps",
                    [
                        "第一步：分析題目",
                        "第二步：找出漏洞",
                        "第三步：利用漏洞獲取 flag",
                    ],
                ),
                "internal_notes": challenge_data.get(
                    "internal_notes", f"開發筆記：{name} 題目"
                ),
                "learning_objectives": challenge_data.get(
                    "learning_objectives", ["學習相關技術概念"]
                ),
                "required_skills": challenge_data.get(
                    "required_skills", ["基礎技能要求"]
                ),
                "testing": challenge_data.get(
                    "testing",
                    {
                        "test_cases": [],
                        "verified_solutions": [],
                        "last_tested": "",
                        "tested_by": "",
                        "test_result": "pending",
                    },
                ),
            }

            # 保存 private.yml
            private_yml_path = challenge_path / "private.yml"
            with open(private_yml_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    private_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            # 創建 public.yml (移除敏感資訊)
            public_config = {
                k: v
                for k, v in private_config.items()
                if not k.startswith(("flag", "solution_", "internal_", "testing"))
            }

            # 移除敏感的 hints 內容
            if "hints" in public_config:
                public_config["hints"] = [
                    {"level": hint["level"], "cost": hint["cost"]}
                    for hint in public_config["hints"]
                ]

            public_yml_path = challenge_path / "public.yml"
            with open(public_yml_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    public_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            # 創建 README.md
            readme_content = f"""# {name}

**分類**: {category}  
**難度**: {difficulty}  
**作者**: {author}  
**分數**: {private_config["points"]}

## 題目描述

{description or "請填寫題目描述"}

## 檔案結構

```
{name}/
├── public.yml          # 公開配置
├── private.yml         # 完整配置 (包含 flag 等敏感資訊)
├── README.md          # 此檔案
├── src/               # 原始碼
├── files/             # 提供給參賽者的檔案
├── writeup/           # 解題文檔
{"├── docker/           # Docker 相關檔案" if challenge_type in ["static_container", "dynamic_container"] else ""}
{"└── bin/              # 編譯後的執行檔" if challenge_type in ["static_container", "dynamic_container"] else ""}
```

## 開發狀態

- [x] 創建基本結構
- [ ] 實作題目邏輯
- [ ] 撰寫 Docker 配置
- [ ] 測試題目功能
- [ ] 撰寫解題文檔
- [ ] 準備部署檔案

## 備註

請在 `private.yml` 中完善題目配置，並在 `src/` 目錄中實作題目邏輯。
"""

            readme_path = challenge_path / "README.md"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

            # 如果是容器類型，創建基本的 Docker 檔案
            if challenge_type in ["static_container", "dynamic_container"]:
                docker_dir = challenge_path / "docker"

                # 創建 Dockerfile
                dockerfile_content = """FROM ubuntu:20.04

# 設定工作目錄
WORKDIR /app

# 安裝基本套件
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# 複製應用程式檔案
COPY src/ /app/

# 設定執行權限
RUN chmod +x /app/*

# 暴露端口
EXPOSE 8080

# 啟動應用程式
CMD ["./start.sh"]
"""

                with open(docker_dir / "Dockerfile", "w", encoding="utf-8") as f:
                    f.write(dockerfile_content)

                # 創建 docker-compose.yml
                compose_content = f"""version: '3.8'

services:
  {name}:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLAG=is1abCTF{{{name}_example_flag}}
    restart: unless-stopped
    mem_limit: 256m
    cpus: 0.1
"""

                with open(
                    docker_dir / "docker-compose.yml", "w", encoding="utf-8"
                ) as f:
                    f.write(compose_content)

                # 創建啟動腳本
                start_script = """#!/bin/bash

echo "Starting challenge..."
# 在這裡添加您的應用程式啟動邏輯

# 例如：
# python3 app.py
# 或
# ./challenge_binary

# 保持容器運行
tail -f /dev/null
"""

                start_path = challenge_path / "src" / "start.sh"
                with open(start_path, "w", encoding="utf-8") as f:
                    f.write(start_script)

            return {
                "status": "success",
                "message": f"題目 {category}/{name} 創建成功",
                "data": {
                    "name": name,
                    "category": category,
                    "difficulty": difficulty,
                    "path": str(challenge_path),
                    "challenge_type": challenge_type,
                },
            }

        except Exception as create_error:
            return {"status": "error", "message": f"創建題目失敗: {str(create_error)}"}

    def update_challenge(
        self, category: str, name: str, challenge_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新現有題目"""
        try:
            challenge_path = CHALLENGES_DIR / category / name
            if not challenge_path.exists():
                return {"status": "error", "message": "題目不存在"}

            private_yml_path = challenge_path / "private.yml"
            if not private_yml_path.exists():
                return {"status": "error", "message": "題目配置檔案不存在"}

            # 讀取現有配置
            with open(private_yml_path, "r", encoding="utf-8") as file:
                existing_config = yaml.safe_load(file)

            # 更新配置
            updated_config = existing_config.copy()

            # 更新基本欄位
            updatable_fields = [
                "title",
                "author",
                "reviewer",
                "validation_status",
                "internal_validation_notes",
                "difficulty",
                "description",
                "challenge_type",
                "source_code_provided",
                "files",
                "status",
                "points",
                "tags",
                "flag",
                "flag_description",
                "solution_steps",
                "internal_notes",
                "learning_objectives",
                "required_skills",
            ]

            for field in updatable_fields:
                if field in challenge_data:
                    updated_config[field] = challenge_data[field]

            # 處理提示
            if "hints" in challenge_data:
                updated_config["hints"] = challenge_data["hints"]

            # 處理部署資訊
            if "deploy_info" in challenge_data:
                if "deploy_info" not in updated_config:
                    updated_config["deploy_info"] = {}
                updated_config["deploy_info"].update(challenge_data["deploy_info"])

            # 更新時間戳
            updated_config["updated_at"] = datetime.now().isoformat()

            # 保存 private.yml
            with open(private_yml_path, "w", encoding="utf-8") as file:
                yaml.dump(
                    updated_config,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            # 更新 public.yml
            public_config = {
                k: v
                for k, v in updated_config.items()
                if not k.startswith(("flag", "solution_", "internal_", "testing"))
            }

            # 移除敏感的 hints 內容
            if "hints" in public_config:
                public_config["hints"] = [
                    {"level": hint["level"], "cost": hint["cost"]}
                    for hint in public_config["hints"]
                ]

            public_yml_path = challenge_path / "public.yml"
            with open(public_yml_path, "w", encoding="utf-8") as file:
                yaml.dump(
                    public_config,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            return {
                "status": "success",
                "message": f"題目 {category}/{name} 更新成功",
                "data": updated_config,
            }

        except Exception as update_error:
            return {"status": "error", "message": f"更新題目失敗: {str(update_error)}"}

    def validate_challenge(self, challenge_path: str) -> Dict[str, Any]:
        """驗證挑戰"""
        try:
            # 這裡可以整合驗證挑戰的邏輯
            return {"status": "success", "data": {"valid": True}}

        except Exception as validate_error:
            return {"status": "error", "message": f"驗證失敗: {str(validate_error)}"}


# 創建 CTF 管理器實例
ctf_manager = CTFManager()


# ===== 路由定義 =====


@app.route("/")
def dashboard():
    """儀表板首頁"""
    stats = ctf_manager.get_stats()
    challenge_data = ctf_manager.get_challenges_with_quota()
    return render_template(
        "dashboard.html",
        config=ctf_manager.config,
        stats=stats,
        challenges=challenge_data["challenges"],
        challenge_quota=challenge_data,
    )


@app.route("/challenges")
def challenges_list():
    """挑戰列表頁面"""
    challenges = ctf_manager.get_challenges()
    return render_template(
        "challenges.html", config=ctf_manager.config, challenges=challenges
    )


@app.route("/create")
def create_challenge_form():
    """創建挑戰表單頁面"""
    if not ctf_manager.is_setup_complete():
        return render_template(
            "setup.html",
            config=ctf_manager.config,
            missing=ctf_manager.get_setup_missing_items(),
        )
    return render_template("create_challenge.html", config=ctf_manager.config)


@app.route("/validation")
def validation_queue():
    """驗題佇列：待驗題 / 已拒絕之題目"""
    if not ctf_manager.is_setup_complete():
        return render_template(
            "setup.html",
            config=ctf_manager.config,
            missing=ctf_manager.get_setup_missing_items(),
        )
    queue = ctf_manager.get_validation_queue()
    return render_template(
        "validation.html",
        config=ctf_manager.config,
        queue=queue,
    )


SETUP_STEPS = ["project", "team", "event", "quota", "finalize"]


@app.route("/setup")
def setup_root():
    from flask import redirect, url_for
    return redirect(url_for("setup_step", step="project"))


@app.route("/setup/<step>", methods=["GET"])
def setup_step(step: str):
    from flask import abort
    if step not in SETUP_STEPS:
        abort(404)
    statuses = ctf_manager.compute_step_status()
    return render_template(
        f"setup/{step}.html",
        step=step,
        steps=SETUP_STEPS,
        statuses=statuses,
        config=ctf_manager.config,
    )


@app.route("/setup/<step>", methods=["POST"])
def setup_step_save(step: str):
    from flask import abort, jsonify
    if step not in SETUP_STEPS:
        abort(404)
    data = request.get_json(silent=True) or request.form.to_dict(flat=False)
    if step == "finalize":
        return jsonify(_handle_setup_finalize(data))
    if isinstance(data, dict):
        flat = {}
        for k, v in data.items():
            flat[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
        data = flat
    result = ctf_manager.save_setup_step(step, data or {})
    return jsonify(result)


def _handle_setup_finalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Step 5: 產生 .github/ 模板 + 清理冗餘欄位（依 data 中的 flag）。"""
    from setup_helpers import (
        cleanup_legacy_validation_fields,
        generate_branch_protection_doc,
        generate_codeowners,
        generate_pr_template,
    )

    config = ctf_manager.config
    raw_for_doc = {"project": {
        "organization": config.get("organization", ""),
        "name": config.get("competition_name", ""),
    }}
    actions: List[str] = []

    if data.get("generate_pr_template"):
        path = BASE_DIR / ".github" / "PULL_REQUEST_TEMPLATE.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_pr_template(config), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("generate_codeowners"):
        path = BASE_DIR / ".github" / "CODEOWNERS"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_codeowners(config), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("generate_branch_protection_doc"):
        path = BASE_DIR / ".github" / "branch-protection.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_branch_protection_doc(raw_for_doc), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("cleanup_legacy"):
        report = cleanup_legacy_validation_fields(CHALLENGES_DIR, dry_run=False)
        actions.append(f"清理 {len(report.files_changed)} 個含冗餘欄位的檔案")

    return {"status": "success", "actions": actions}


@app.route("/challenges/<category>/<name>")
def challenge_detail(category: str, name: str):
    """挑戰詳細資訊頁面"""
    try:
        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return render_template(
                "error.html", error_code=404, error_message="題目不存在"
            ), 404

        # 讀取配置檔案
        private_yml_path = challenge_path / "private.yml"
        public_yml_path = challenge_path / "public.yml"

        challenge_data = {}
        if private_yml_path.exists():
            with open(private_yml_path, "r", encoding="utf-8") as f:
                challenge_data = yaml.safe_load(f)
        elif public_yml_path.exists():
            with open(public_yml_path, "r", encoding="utf-8") as f:
                challenge_data = yaml.safe_load(f)
        else:
            return render_template(
                "error.html", error_code=404, error_message="題目配置檔案不存在"
            ), 404

        challenge_data["path"] = str(challenge_path)
        challenge_data["name"] = name
        challenge_data["category"] = category
        return render_template(
            "challenge_detail.html", config=ctf_manager.config, challenge=challenge_data
        )

    except Exception as e:
        return render_template(
            "error.html", error_code=500, error_message=f"讀取題目失敗: {str(e)}"
        ), 500


@app.route("/challenges/<category>/<name>/edit")
def edit_challenge_form(category: str, name: str):
    """編輯挑戰表單頁面"""
    try:
        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return render_template(
                "error.html", error_code=404, error_message="題目不存在"
            ), 404

        # 讀取配置檔案
        private_yml_path = challenge_path / "private.yml"

        if not private_yml_path.exists():
            return render_template(
                "error.html", error_code=404, error_message="題目配置檔案不存在"
            ), 404

        with open(private_yml_path, "r", encoding="utf-8") as f:
            challenge_data = yaml.safe_load(f)

        challenge_data["path"] = str(challenge_path)
        challenge_data["name"] = name
        challenge_data["category"] = category
        return render_template(
            "edit_challenge.html", config=ctf_manager.config, challenge=challenge_data
        )

    except Exception as e:
        return render_template(
            "error.html", error_code=500, error_message=f"讀取題目失敗: {str(e)}"
        ), 500


@app.route("/settings")
def settings():
    """設定頁面"""
    return render_template("settings.html", config=ctf_manager.config)


# ===== API 路由 =====


@app.route("/api/stats")
def api_stats():
    """獲取統計資料 API"""
    try:
        stats = ctf_manager.get_stats()
        return jsonify({"status": "success", "data": stats})
    except Exception as stats_error:
        return jsonify({"status": "error", "message": str(stats_error)}), 500


@app.route("/api/challenges")
def api_challenges():
    """獲取挑戰列表 API"""
    try:
        challenges = ctf_manager.get_challenges()
        return jsonify({"status": "success", "data": challenges})
    except Exception as challenges_error:
        return jsonify({"status": "error", "message": str(challenges_error)}), 500


@app.route(
    "/api/challenges/<string:category>/<string:name>/review",
    methods=["POST"],
)
def api_review_challenge(category: str, name: str):
    """更新驗題狀態（通過 / 退回 / 標示待驗）"""
    try:
        body = request.get_json() or {}
        action = (body.get("action") or "").strip().lower()
        actor = (body.get("actor") or body.get("reviewer") or "").strip()
        notes = (body.get("notes") or "").strip()
        result = ctf_manager.review_challenge(category, name, action, actor, notes)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/challenges/<string:category>/<string:name>/scan", methods=["POST"])
def api_scan_challenge(category: str, name: str):
    """對單一題目執行敏感資料掃描。"""
    try:
        result = ctf_manager.run_scan_secrets(category, name)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/challenges/<string:category>/<string:name>/build", methods=["POST"])
def api_build_challenge(category: str, name: str):
    """對單一題目執行 public-release 建置。"""
    try:
        body = request.get_json() or {}
        force = bool(body.get("force", True))
        result = ctf_manager.run_build_public(category, name, force=force)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/public-release/build", methods=["POST"])
def api_build_public_release():
    """建置所有題目到 public-release。"""
    try:
        body = request.get_json() or {}
        force = bool(body.get("force", True))
        result = ctf_manager.run_build_all_public(force=force)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/public-release/sync", methods=["POST"])
def api_sync_public_release():
    """同步 ready_for_release 題目到 public-release（不推送遠端）。"""
    try:
        result = ctf_manager.run_sync_to_public()
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/challenges", methods=["POST"])
def api_create_challenge():
    """創建挑戰 API"""
    try:
        challenge_data = request.get_json()
        if not challenge_data:
            raise BadRequest("無效的請求資料")

        result = ctf_manager.create_challenge(challenge_data)

        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as create_error:
        return jsonify({"status": "error", "message": str(create_error)}), 500


@app.route("/api/challenges/<category>/<name>", methods=["GET"])
def api_get_challenge(category: str, name: str):
    """獲取單個題目詳細資訊 API"""
    try:
        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return jsonify({"status": "error", "message": "題目不存在"}), 404

        # 讀取配置檔案
        private_yml_path = challenge_path / "private.yml"
        public_yml_path = challenge_path / "public.yml"

        challenge_data = {}
        if private_yml_path.exists():
            with open(private_yml_path, "r", encoding="utf-8") as f:
                challenge_data = yaml.safe_load(f)
        elif public_yml_path.exists():
            with open(public_yml_path, "r", encoding="utf-8") as f:
                challenge_data = yaml.safe_load(f)
        else:
            return jsonify({"status": "error", "message": "題目配置檔案不存在"}), 404

        challenge_data["path"] = str(challenge_path)
        return jsonify({"status": "success", "data": challenge_data})

    except Exception as e:
        return jsonify({"status": "error", "message": f"讀取題目失敗: {str(e)}"}), 500


@app.route("/api/challenges/<category>/<name>", methods=["PUT"])
def api_update_challenge(category: str, name: str):
    """更新挑戰 API"""
    try:
        challenge_data = request.get_json()
        if not challenge_data:
            raise BadRequest("無效的請求資料")

        result = ctf_manager.update_challenge(category, name, challenge_data)

        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as update_error:
        return jsonify({"status": "error", "message": str(update_error)}), 500


@app.route("/api/challenges/<category>/<name>", methods=["DELETE"])
def api_delete_challenge(category: str, name: str):
    """刪除挑戰 API"""
    try:
        import shutil

        challenge_path = CHALLENGES_DIR / category / name
        if not challenge_path.exists():
            return jsonify({"status": "error", "message": "題目不存在"}), 404

        # 刪除整個挑戰目錄
        shutil.rmtree(challenge_path)

        return jsonify({"status": "success", "message": "挑戰刪除成功"})

    except Exception as delete_error:
        return jsonify(
            {"status": "error", "message": f"刪除挑戰失敗: {str(delete_error)}"}
        ), 500


@app.route("/api/challenges/<category>/<name>/files", methods=["GET"])
def api_list_challenge_files(category: str, name: str):
    """API: 列出挑戰檔案"""
    try:
        challenge_dir = CHALLENGES_DIR / category / name
        if not challenge_dir.exists():
            return jsonify({"status": "error", "message": "挑戰不存在"}), 404

        files_dir = challenge_dir / "files"
        files = []

        if files_dir.exists():
            for file_path in files_dir.iterdir():
                if file_path.is_file():
                    files.append(
                        {
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat(),
                        }
                    )

        return jsonify({"status": "success", "data": files})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/challenges/<category>/<name>/files/<filename>", methods=["GET"])
def api_download_challenge_file(category: str, name: str, filename: str):
    """API: 下載挑戰檔案"""
    try:
        challenge_dir = CHALLENGES_DIR / category / name
        files_dir = challenge_dir / "files"
        file_path = files_dir / filename

        if not file_path.exists() or not file_path.is_file():
            return jsonify({"status": "error", "message": "檔案不存在"}), 404

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/challenges/<path:challenge_path>/validate", methods=["POST"])
def api_validate_challenge(challenge_path: str):
    """驗證挑戰 API"""
    try:
        result = ctf_manager.validate_challenge(challenge_path)

        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as validate_error:
        return jsonify({"status": "error", "message": str(validate_error)}), 500


@app.route("/api/config")
def api_config():
    """獲取配置 API"""
    return jsonify({"status": "success", "data": ctf_manager.config})


@app.route("/api/setup", methods=["POST"])
def api_setup():
    """寫入初始化設定到 config.yml"""
    try:
        body = request.get_json() or {}
        result = ctf_manager.save_setup(body)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/git-user")
def api_git_user():
    """取得本機 git user.name（用於建題時快速填入出題人）。"""
    try:
        name = ctf_manager.guess_git_author()
        return jsonify({"status": "success", "data": {"user_name": name}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    """更新 config.yml（分數/配額/團隊/時間等）。"""
    try:
        body = request.get_json() or {}
        result = ctf_manager.update_config(body)
        if result["status"] == "success":
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===== 靜態檔案服務 =====


@app.route("/static/<path:filename>")
def static_files(filename):
    """提供靜態檔案"""
    return send_from_directory(STATIC_DIR, filename)


# ===== 錯誤處理 =====


@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return render_template(
        "404.html",
        config=ctf_manager.config,
        error_code=404,
        error_message="頁面不存在",
    ), 404


@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return render_template(
        "500.html",
        config=ctf_manager.config,
        error_code=500,
        error_message="內部伺服器錯誤",
    ), 500


if __name__ == "__main__":
    print("🚀 啟動 IS1AB CTF Template Web Interface")
    print("📍 URL: http://localhost:8004")
    print("🎨 使用 Jinja2 + Bulma CSS 框架")

    # 開發模式運行
    app.run(host="0.0.0.0", port=8004, debug=True, threaded=True)
