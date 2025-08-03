#!/usr/bin/env python3
"""
IS1AB CTF Template - 現代化 Web 介面
整合版本：使用 Flask + Jinja2 + Bulma CSS
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml

# Flask 相關套件
from flask import Flask, jsonify, render_template, request, send_from_directory
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
            config = {
                "competition_name": raw_config.get("project", {}).get(
                    "name", "IS1AB CTF"
                ),
                "organization": raw_config.get("project", {}).get(
                    "organization", "IS1AB"
                ),
                "description": raw_config.get("project", {}).get(
                    "description", "IS1AB CTF Competition"
                ),
                "categories": ["web", "pwn", "crypto", "misc", "reverse", "forensic"],
                "difficulties": ["baby", "easy", "middle", "hard", "impossible"],
                "challenge_quota": raw_config.get("challenge_quota", {}),
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
            }

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

            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            stats["by_difficulty"][difficulty] = (
                stats["by_difficulty"].get(difficulty, 0) + 1
            )
            stats["total_points"] += points

        return stats

    def create_challenge(self, challenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """創建新挑戰"""
        try:
            # 這裡可以整合創建挑戰的邏輯
            return {
                "status": "success",
                "message": "挑戰創建成功",
                "data": challenge_data,
            }

        except Exception as create_error:
            return {"status": "error", "message": f"創建挑戰失敗: {str(create_error)}"}

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
    return render_template("create_challenge.html", config=ctf_manager.config)


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
