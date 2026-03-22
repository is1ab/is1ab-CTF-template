#!/usr/bin/env python3
"""
專案初始化腳本
用於設置新的 CTF 專案環境
"""

import argparse
import yaml
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

def init_project(year, org_name, project_name=None):
    """初始化 CTF 專案"""
    
    if not project_name:
        project_name = f"{year}-{org_name}-CTF"
    
    print(f"🚀 初始化 CTF 專案: {project_name}")
    
    # 1. 更新 config.yml
    update_config(year, org_name, project_name)
    
    # 2. 初始化目錄結構
    setup_directory_structure()
    
    # 3. 設置 Git hooks
    setup_git_hooks()
    
    # 4. 建立初始文檔
    create_initial_docs(year, org_name, project_name)
    
    # 5. 設置 GitHub Actions
    setup_github_actions()
    
    print(f"✅ 專案初始化完成！")
    print(f"📁 專案路徑: {Path.cwd()}")
    print(f"🌐 建議接下來啟動 Web 介面: cd web-interface && python server.py")

def update_config(year, org_name, project_name):
    """更新配置檔案"""
    print("📝 更新配置檔案...")
    
    config_path = Path("config.yml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # 更新專案資訊
    config.setdefault('project', {})
    config['project'].update({
        'name': project_name,
        'year': year,
        'organization': org_name,
        'flag_prefix': f'{org_name}CTF',
        'description': f'{org_name} CTF {year} Competition',
        'created_at': datetime.now().isoformat()
    })
    
    # 確保有預設配額設定
    config.setdefault('challenge_quota', {
        'by_category': {
            'general': 2,
            'web': 6,
            'pwn': 6,
            'reverse': 4,
            'crypto': 4,
            'forensic': 3,
            'misc': 3
        },
        'by_difficulty': {
            'baby': 8,
            'easy': 10,
            'middle': 8,
            'hard': 4,
            'impossible': 2
        },
        'total_target': 32,
        'validation': {
            'category_sum_equals_total': True,
            'difficulty_sum_equals_total': True,
            'tolerance_percentage': 5
        }
    })
    
    # 更新團隊設定
    config.setdefault('team', {
        'default_author': 'CTF-Team',
        'reviewers': ['admin', 'senior-dev']
    })
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ 配置檔案已更新")

def setup_directory_structure():
    """設置目錄結構"""
    print("📁 建立目錄結構...")
    
    directories = [
        'challenges',
        'docs',
        'templates',
        'scripts',
        'web-interface',
        '.github/workflows',
        '.github/ISSUE_TEMPLATE',
        'docker',
        'public-release'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # 建立 .gitkeep 檔案以保持空目錄
        gitkeep = Path(directory) / '.gitkeep'
        if not any(Path(directory).iterdir()):
            gitkeep.touch()
    
    print("✅ 目錄結構已建立")

def setup_git_hooks():
    """設置 Git Hooks"""
    print("🔗 設置 Git Hooks...")
    
    hooks_dir = Path('.git/hooks')
    if not hooks_dir.exists():
        print("⚠️  Git 倉庫未初始化，跳過 Git Hooks 設置")
        return
    
    # Pre-commit hook
    pre_commit_hook = hooks_dir / 'pre-commit'
    pre_commit_content = """#!/bin/bash
# CTF 專案 pre-commit hook

echo "🔍 執行提交前檢查..."

# 檢查 Python 語法
python -m py_compile scripts/*.py 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Python 語法錯誤"
    exit 1
fi

echo "✅ 所有檢查通過"
"""
    
    with open(pre_commit_hook, 'w') as f:
        f.write(pre_commit_content)
    
    pre_commit_hook.chmod(0o755)
    print("✅ Git Hooks 已設置")

def create_initial_docs(year, org_name, project_name):
    """建立初始文檔"""
    print("📚 建立初始文檔...")
    
    # 更新 README.md
    readme_content = f"""# {project_name}

🚀 **{org_name} CTF {year}** - 使用 is1ab-CTF-template 建立的標準化 CTF 專案

## 📋 專案概覽

- **比賽名稱**: {org_name} CTF {year}
- **組織**: {org_name}
- **建立時間**: {datetime.now().strftime('%Y-%m-%d')}
- **Flag 格式**: `{org_name}CTF{{...}}`

## 🎯 目標配額

| 分類 | 目標數量 | 當前進度 |
|------|----------|----------|
| Web | 6 題 | 0/6 ⚪⚪⚪⚪⚪⚪ |
| Pwn | 6 題 | 0/6 ⚪⚪⚪⚪⚪⚪ |
| Reverse | 4 題 | 0/4 ⚪⚪⚪⚪ |
| Crypto | 4 題 | 0/4 ⚪⚪⚪⚪ |
| Forensic | 3 題 | 0/3 ⚪⚪⚪ |
| Misc | 3 題 | 0/3 ⚪⚪⚪ |

**總計**: 0/32 題 (0% 完成)

## 🚀 快速開始

```bash
# 安裝依賴
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# 啟動 Web 管理介面
cd web-interface
python server.py --host localhost --port 8000

# 創建第一個題目
uv run scripts/create-challenge.py web welcome baby --author YourName
```

## 📁 題目列表

### Web 安全 (0/6)
*尚未建立題目*

### 二進制漏洞利用 (0/6)  
*尚未建立題目*

### 逆向工程 (0/4)
*尚未建立題目*

### 密碼學 (0/4)
*尚未建立題目*

### 數位鑑識 (0/3)
*尚未建立題目*

### 雜項 (0/3)
*尚未建立題目*

## 🛠️ 開發指南

請參考以下文檔：
- [設置指南](docs/setup-guide.md)
- [題目開發指南](docs/challenge-development.md) 
- [貢獻指南](CONTRIBUTING.md)
- [部署指南](docs/deployment-guide.md)

## 📊 開發進度

*此部分將由 `update-readme.py` 自動維護*

---
最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 使用 [is1ab-CTF-template](https://github.com/your-org/is1ab-CTF-template) 建立
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ 文檔已建立")

def setup_github_actions():
    """設置 GitHub Actions"""
    print("⚙️ 設置 GitHub Actions...")
    
    # 建立 validate-pr.yml
    validate_pr_content = """name: 🔍 Validate Pull Request

on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'challenges/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: 🐍 Setup Python with uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: "requirements.txt"
      
      - name: 📦 Install dependencies
        run: |
          uv venv
          uv pip install -r requirements.txt
      
      - name: 🔍 Validate new challenges
        run: |
          git fetch origin main
          CHANGED_DIRS=$(git diff --name-only origin/main...HEAD | grep "challenges/" | cut -d'/' -f1-3 | sort -u)
          
          for dir in $CHANGED_DIRS; do
            if [ -d "$dir" ]; then
              echo "Validating $dir"
              uv run scripts/validate-challenge.py "$dir"
            fi
          done
      
"""
    
    with open('.github/workflows/validate-pr.yml', 'w') as f:
        f.write(validate_pr_content)
    
    # 建立 update-progress.yml
    update_progress_content = """name: 📊 Update Progress

on:
  push:
    branches: [main]
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  update:
    if: github.event.pull_request.merged == true || github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: 🐍 Setup Python with uv
        uses: astral-sh/setup-uv@v3
      
      - name: 📦 Install dependencies
        run: |
          uv venv
          uv pip install -r requirements.txt
      
      - name: 📊 Update README
        run: uv run scripts/update-readme.py
      
      - name: 💾 Commit changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: '🤖 Auto-update progress [skip ci]'
"""
    
    with open('.github/workflows/update-progress.yml', 'w') as f:
        f.write(update_progress_content)
    
    print("✅ GitHub Actions 已設置")

def main():
    parser = argparse.ArgumentParser(description='初始化 CTF 專案')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                       help='比賽年份 (預設: 當前年份)')
    parser.add_argument('--org', required=True,
                       help='組織名稱 (例如: is1ab)')
    parser.add_argument('--name', 
                       help='專案名稱 (預設: YEAR-ORG-CTF)')
    
    args = parser.parse_args()
    
    init_project(args.year, args.org, args.name)

if __name__ == "__main__":
    main()