#!/usr/bin/env python3
"""
同步到公開倉庫腳本
用於將私有開發倉庫的安全內容同步到公開發布倉庫
"""

import argparse
import yaml
import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

class PublicSync:
    def __init__(self, config_path="config.yml"):
        """初始化同步器"""
        self.config = self.load_config(config_path)
        self.public_dir = Path("public-release")
        self.challenges_dir = Path("challenges")
        
    def load_config(self, config_path):
        """載入配置檔案"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def prepare_public_directory(self):
        """準備公開發布目錄"""
        print("📁 準備公開發布目錄...")
        
        # 清理並重新建立公開目錄
        if self.public_dir.exists():
            shutil.rmtree(self.public_dir)
        self.public_dir.mkdir(exist_ok=True)
        
        # 建立基本目錄結構
        for subdir in ['challenges', 'docs', 'attachments', 'writeups']:
            (self.public_dir / subdir).mkdir(exist_ok=True)
        
        print("✅ 公開目錄已準備完成")
    
    def sync_challenge(self, challenge_path):
        """同步單個題目到公開倉庫"""
        challenge_path = Path(challenge_path)
        public_yml_path = challenge_path / "public.yml"
        
        if not public_yml_path.exists():
            print(f"⚠️  跳過 {challenge_path}：沒有 public.yml")
            return False
        
        # 載入 public.yml
        with open(public_yml_path, 'r', encoding='utf-8') as f:
            public_config = yaml.safe_load(f)
        
        # 檢查是否準備好發布
        if not public_config.get('ready_for_release', False):
            print(f"⚠️  跳過 {challenge_path}：尚未準備好發布")
            return False
        
        print(f"📦 同步題目: {challenge_path}")
        
        # 計算相對路徑
        relative_path = challenge_path.relative_to(self.challenges_dir.parent)
        public_challenge_path = self.public_dir / relative_path
        public_challenge_path.mkdir(parents=True, exist_ok=True)
        
        # 同步允許的檔案
        self.sync_allowed_files(challenge_path, public_challenge_path, public_config)
        
        # 生成公開的題目描述
        self.generate_public_readme(challenge_path, public_challenge_path, public_config)
        
        return True
    
    def sync_allowed_files(self, source_path, target_path, public_config):
        """同步允許的檔案"""
        allowed_files = public_config.get('allowed_files', [])
        
        for file_pattern in allowed_files:
            # 使用 glob 匹配檔案
            for file_path in source_path.glob(file_pattern):
                if file_path.is_file():
                    # 計算相對路徑
                    relative_file = file_path.relative_to(source_path)
                    target_file = target_path / relative_file
                    
                    # 建立目標目錄
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 複製檔案
                    shutil.copy2(file_path, target_file)
                    print(f"  📄 複製: {relative_file}")
    
    def generate_public_readme(self, source_path, target_path, public_config):
        """生成公開的題目 README"""
        readme_content = f"""# {public_config.get('title', '題目名稱')}

## 📋 題目資訊

- **分類**: {public_config.get('category', 'N/A')}
- **難度**: {public_config.get('difficulty', 'N/A')}
- **作者**: {public_config.get('author', 'CTF Team')}
- **分數**: {public_config.get('points', 'N/A')}

## 📝 題目描述

{public_config.get('description', '題目描述待補充')}

## 📎 附件檔案

"""
        
        # 列出附件檔案
        allowed_files = public_config.get('allowed_files', [])
        if allowed_files:
            for file_pattern in allowed_files:
                for file_path in source_path.glob(file_pattern):
                    if file_path.is_file():
                        relative_file = file_path.relative_to(source_path)
                        readme_content += f"- [{relative_file.name}](./{relative_file})\n"
        else:
            readme_content += "*無附件檔案*\n"
        
        # 添加 Flag 格式說明
        flag_prefix = self.config.get('project', {}).get('flag_prefix', 'CTF')
        readme_content += f"""
## 🏁 Flag 格式

```
{flag_prefix}{{...}}
```

## 🏆 解題思路

*比賽結束後將提供 Writeup*

---
📅 發布時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # 寫入 README
        with open(target_path / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def generate_public_summary(self):
        """生成公開倉庫的總體 README"""
        project_info = self.config.get('project', {})
        
        readme_content = f"""# {project_info.get('name', 'CTF Competition')}

🚀 **{project_info.get('organization', 'Organization')} CTF {project_info.get('year', datetime.now().year)}** - 公開題目與附件

## 📋 比賽資訊

- **比賽名稱**: {project_info.get('name', 'CTF Competition')}
- **主辦單位**: {project_info.get('organization', 'Organization')}
- **比賽年份**: {project_info.get('year', datetime.now().year)}
- **Flag 格式**: `{project_info.get('flag_prefix', 'CTF')}{{...}}`

## 📁 題目列表

"""
        
        # 掃描公開題目並生成列表
        challenges_by_category = {}
        
        for challenge_dir in (self.public_dir / "challenges").rglob("*/"):
            if (challenge_dir / "README.md").exists():
                parts = challenge_dir.relative_to(self.public_dir / "challenges").parts
                if len(parts) >= 2:
                    category = parts[0]
                    challenge_name = parts[1]
                    
                    if category not in challenges_by_category:
                        challenges_by_category[category] = []
                    
                    challenges_by_category[category].append({
                        'name': challenge_name,
                        'path': f"challenges/{category}/{challenge_name}"
                    })
        
        # 生成分類列表
        for category, challenges in sorted(challenges_by_category.items()):
            readme_content += f"### {category.title()} ({len(challenges)} 題)\n\n"
            
            for challenge in sorted(challenges, key=lambda x: x['name']):
                readme_content += f"- [{challenge['name']}]({challenge['path']}/)\n"
            
            readme_content += "\n"
        
        readme_content += f"""## 🏆 Writeups

比賽結束後，優秀的 Writeup 將會發布在 [writeups](writeups/) 目錄中。

## 📞 聯絡資訊

- 🌐 **官方網站**: [比賽平台連結]
- 📧 **聯絡信箱**: [聯絡信箱]
- 💬 **討論群組**: [Discord/Telegram]

## 📄 授權條款

本倉庫內容遵循 MIT License 授權條款。

---
📅 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
🤖 此檔案由 sync-to-public.py 自動生成
"""
        
        # 寫入公開 README
        with open(self.public_dir / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def sync_all_challenges(self):
        """同步所有準備好的題目"""
        print("🔄 開始同步所有題目...")
        
        synced_count = 0
        total_count = 0
        
        # 遍歷所有題目目錄
        for challenge_dir in self.challenges_dir.rglob("*/"):
            if (challenge_dir / "public.yml").exists():
                total_count += 1
                if self.sync_challenge(challenge_dir):
                    synced_count += 1
        
        print(f"✅ 同步完成：{synced_count}/{total_count} 個題目")
        return synced_count, total_count
    
    def create_git_repo(self, public_repo_url=None):
        """在公開目錄中初始化 Git 倉庫"""
        print("🔧 初始化公開倉庫...")
        
        os.chdir(self.public_dir)
        
        # 初始化 Git 倉庫
        subprocess.run(['git', 'init'], check=True)
        
        # 建立 .gitignore
        gitignore_content = """# 系統檔案
.DS_Store
Thumbs.db

# 編輯器
.vscode/
.idea/

# 臨時檔案
*.tmp
*.log
"""
        
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        
        # 添加所有檔案
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', '🎉 Initial public release'], check=True)
        
        # 設置遠程倉庫
        if public_repo_url:
            subprocess.run(['git', 'remote', 'add', 'origin', public_repo_url], check=True)
            print(f"✅ 遠程倉庫已設置：{public_repo_url}")
        
        # 回到原目錄
        os.chdir('..')
        
        print("✅ 公開倉庫初始化完成")
    
    def run_full_sync(self, public_repo_url=None, commit_message=None):
        """執行完整同步流程"""
        print("🚀 開始完整同步流程...")
        
        # 1. 準備公開目錄
        self.prepare_public_directory()
        
        # 2. 同步所有題目
        synced_count, total_count = self.sync_all_challenges()
        
        # 3. 生成總體 README
        self.generate_public_summary()
        
        # 4. 初始化 Git 倉庫
        self.create_git_repo(public_repo_url)
        
        print(f"🎉 同步完成！同步了 {synced_count}/{total_count} 個題目")
        print(f"📁 公開檔案位於：{self.public_dir.absolute()}")
        
        if public_repo_url:
            print(f"🌐 準備推送到：{public_repo_url}")
            print("執行以下命令推送到遠程倉庫：")
            print(f"cd {self.public_dir}")
            print("git push -u origin main")

def main():
    parser = argparse.ArgumentParser(description='同步到公開倉庫')
    parser.add_argument('--config', default='config.yml',
                       help='配置檔案路徑 (預設: config.yml)')
    parser.add_argument('--public-repo', 
                       help='公開倉庫 URL (例如: git@github.com:org/2024-ctf-public.git)')
    parser.add_argument('--challenge', 
                       help='同步特定題目 (例如: challenges/web/example)')
    parser.add_argument('--dry-run', action='store_true',
                       help='模擬執行，不實際建立檔案')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 模擬執行模式")
    
    sync = PublicSync(args.config)
    
    if args.challenge:
        # 同步特定題目
        challenge_path = Path(args.challenge)
        if not challenge_path.exists():
            print(f"❌ 題目路徑不存在：{challenge_path}")
            return
        
        sync.prepare_public_directory()
        success = sync.sync_challenge(challenge_path)
        
        if success:
            print(f"✅ 題目 {challenge_path} 同步完成")
        else:
            print(f"❌ 題目 {challenge_path} 同步失敗")
    else:
        # 執行完整同步
        sync.run_full_sync(args.public_repo)

if __name__ == "__main__":
    main()