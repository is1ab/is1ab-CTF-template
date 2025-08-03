#!/usr/bin/env python3
"""
IS1AB CTF Template - 現代化 Web 介面
整合版本：使用 Flask + Jinja2 + Bulma CSS
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

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
            # 提取必要參數
            name = challenge_data.get("name", "").strip()
            category = challenge_data.get("category", "").strip()
            difficulty = challenge_data.get("difficulty", "easy").strip()
            author = challenge_data.get("author", "IS1AB").strip()
            description = challenge_data.get("description", "").strip()
            challenge_type = challenge_data.get(
                "challenge_type", "static_container"
            ).strip()

            # 基本驗證
            if not name or not category:
                return {"status": "error", "message": "題目名稱和分類不能為空"}

            # 驗證名稱格式
            if not name.replace("_", "").replace("-", "").isalnum():
                return {
                    "status": "error",
                    "message": "題目名稱只能包含字母、數字、底線和連字號",
                }

            # 驗證分類
            valid_categories = ["web", "pwn", "reverse", "crypto", "forensic", "misc"]
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
    return render_template("create_challenge.html", config=ctf_manager.config)


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
