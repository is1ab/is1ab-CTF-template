#!/usr/bin/env python3
"""
準備公開發布腳本
協助準備 CTF 比賽的公開發布流程
"""

import argparse
import yaml
import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

class PublicReleasePreparator:
    def __init__(self, config_path="config.yml"):
        """初始化發布準備器"""
        self.config = self.load_config(config_path)
        self.root_path = Path.cwd()
        
    def load_config(self, config_path):
        """載入配置檔案"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def validate_all_challenges(self):
        """驗證所有題目是否準備好發布"""
        print("🔍 驗證所有題目...")
        
        challenges_dir = Path("challenges")
        validation_results = []
        
        for challenge_dir in challenges_dir.rglob("*/"):
            if (challenge_dir / "public.yml").exists():
                result = self.validate_challenge(challenge_dir)
                validation_results.append(result)
        
        return validation_results
    
    def validate_challenge(self, challenge_path):
        """驗證單個題目"""
        challenge_path = Path(challenge_path)
        result = {
            'path': str(challenge_path),
            'name': challenge_path.name,
            'category': challenge_path.parent.name,
            'valid': False,
            'issues': [],
            'ready_for_release': False
        }
        
        # 檢查必要檔案
        required_files = ['public.yml']
        for file_name in required_files:
            file_path = challenge_path / file_name
            if not file_path.exists():
                result['issues'].append(f"缺少必要檔案：{file_name}")
                return result
        
        # 載入 public.yml
        try:
            with open(challenge_path / "public.yml", 'r', encoding='utf-8') as f:
                public_config = yaml.safe_load(f)
        except Exception as e:
            result['issues'].append(f"public.yml 格式錯誤：{e}")
            return result
        
        # 檢查必要欄位
        required_fields = ['title', 'category', 'difficulty', 'author', 'description']
        for field in required_fields:
            if not public_config.get(field):
                result['issues'].append(f"public.yml 缺少必要欄位：{field}")
        
        # 檢查 allowed_files
        allowed_files = public_config.get('allowed_files', [])
        if allowed_files:
            for file_pattern in allowed_files:
                matched_files = list(challenge_path.glob(file_pattern))
                if not matched_files:
                    result['issues'].append(f"找不到允許的檔案：{file_pattern}")
        
        # 檢查敏感資料
        sensitive_files = ['flag.txt', 'solution.py', 'writeup.md', 'private.yml']
        for sensitive_file in sensitive_files:
            if (challenge_path / sensitive_file).exists():
                if sensitive_file in allowed_files:
                    result['issues'].append(f"敏感檔案被標記為允許：{sensitive_file}")
        
        # 設置結果
        result['valid'] = len(result['issues']) == 0
        result['ready_for_release'] = public_config.get('ready_for_release', False)
        
        return result
    
    def generate_release_report(self, validation_results):
        """生成發布報告"""
        print("📊 生成發布報告...")
        
        total_challenges = len(validation_results)
        valid_challenges = sum(1 for r in validation_results if r['valid'])
        ready_challenges = sum(1 for r in validation_results if r['ready_for_release'])
        
        # 按分類統計
        categories = {}
        for result in validation_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'valid': 0, 'ready': 0}
            
            categories[category]['total'] += 1
            if result['valid']:
                categories[category]['valid'] += 1
            if result['ready_for_release']:
                categories[category]['ready'] += 1
        
        # 生成報告
        report_content = f"""# CTF 公開發布準備報告

📅 **生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 總體統計

- 📁 **總題目數**: {total_challenges}
- ✅ **有效題目**: {valid_challenges}/{total_challenges} ({valid_challenges/total_challenges*100:.1f}%)
- 🚀 **準備發布**: {ready_challenges}/{total_challenges} ({ready_challenges/total_challenges*100:.1f}%)

## 📋 分類統計

| 分類 | 總數 | 有效 | 準備發布 | 進度 |
|------|------|------|----------|------|"""

        for category, stats in sorted(categories.items()):
            progress_bar = "🟢" * stats['ready'] + "🟡" * (stats['valid'] - stats['ready']) + "🔴" * (stats['total'] - stats['valid'])
            report_content += f"\n| {category} | {stats['total']} | {stats['valid']} | {stats['ready']} | {progress_bar} |"
        
        report_content += f"""

## 📝 詳細問題列表

"""
        
        # 列出有問題的題目
        problem_challenges = [r for r in validation_results if not r['valid'] or not r['ready_for_release']]
        
        if problem_challenges:
            for result in problem_challenges:
                status = "❌ 無效" if not result['valid'] else "⚠️ 未準備"
                report_content += f"### {status} {result['path']}\n\n"
                
                if result['issues']:
                    for issue in result['issues']:
                        report_content += f"- ❌ {issue}\n"
                
                if result['valid'] and not result['ready_for_release']:
                    report_content += "- ⚠️ 尚未標記為準備發布 (ready_for_release: false)\n"
                
                report_content += "\n"
        else:
            report_content += "🎉 **所有題目都已準備好發布！**\n"
        
        report_content += f"""
## 🛠️ 建議行動

"""
        
        if problem_challenges:
            report_content += """1. 🔧 **修復問題題目**
   - 補完缺少的檔案和欄位
   - 確認敏感資料不會被洩露
   - 測試題目功能正常

2. ✅ **標記準備發布**
   - 在 public.yml 中設置 `ready_for_release: true`
   - 確認 allowed_files 列表正確

3. 🔄 **重新驗證**
   - 執行 `uv run scripts/prepare-public-release.py --validate`
   - 確認所有問題已解決
"""
        else:
            report_content += """1. 🚀 **執行發布**
   - 執行 `uv run scripts/sync-to-public.py`
   - 推送到公開倉庫

2. 📢 **公告發布**
   - 更新比賽平台
   - 通知參賽者
"""
        
        report_content += f"""
## 📞 聯絡資訊

如有問題請聯絡：
- 📧 技術支援：[tech-support@example.com]
- 💬 內部討論：[Discord/Slack]

---
🤖 此報告由 prepare-public-release.py 自動生成
"""
        
        # 寫入報告檔案
        report_path = Path("release-report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 發布報告已生成：{report_path}")
        return report_path
    
    def setup_public_repository(self, repo_url):
        """設置公開倉庫"""
        print(f"🔧 設置公開倉庫：{repo_url}")
        
        public_dir = Path("public-release")
        
        if public_dir.exists():
            print("⚠️  公開目錄已存在，將會覆蓋")
            response = input("繼續嗎？(y/N): ")
            if response.lower() != 'y':
                print("❌ 操作已取消")
                return
            
            shutil.rmtree(public_dir)
        
        # 克隆空的公開倉庫
        try:
            subprocess.run(['git', 'clone', repo_url, str(public_dir)], check=True)
            print(f"✅ 公開倉庫已克隆到 {public_dir}")
        except subprocess.CalledProcessError:
            print("⚠️  無法克隆倉庫，建立空目錄")
            public_dir.mkdir()
            
            os.chdir(public_dir)
            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
            os.chdir('..')
    
    def create_github_pages_config(self):
        """建立 GitHub Pages 配置"""
        print("📄 建立 GitHub Pages 配置...")
        
        public_dir = Path("public-release")
        
        # 建立 _config.yml
        config_content = f"""title: {self.config.get('project', {}).get('name', 'CTF Competition')}
description: {self.config.get('project', {}).get('description', 'CTF Competition Challenges')}

theme: minima

markdown: kramdown
highlighter: rouge

plugins:
  - jekyll-feed
  - jekyll-sitemap
  - jekyll-seo-tag

exclude:
  - .git/
  - .gitignore
  - README.md

collections:
  challenges:
    output: true
    permalink: /:collection/:name/

defaults:
  - scope:
      path: ""
      type: "challenges"
    values:
      layout: "challenge"
"""
        
        with open(public_dir / "_config.yml", 'w') as f:
            f.write(config_content)
        
        # 建立基本 layout
        layouts_dir = public_dir / "_layouts"
        layouts_dir.mkdir(exist_ok=True)
        
        challenge_layout = """---
layout: default
---

<h1>{{ page.title }}</h1>

<div class="challenge-meta">
  <span class="category">{{ page.category }}</span>
  <span class="difficulty">{{ page.difficulty }}</span>
  <span class="points">{{ page.points }} points</span>
</div>

{{ content }}
"""
        
        with open(layouts_dir / "challenge.html", 'w') as f:
            f.write(challenge_layout)
        
        print("✅ GitHub Pages 配置已建立")
    
    def run_preparation(self, public_repo_url=None):
        """執行完整準備流程"""
        print("🚀 開始準備公開發布...")
        
        # 1. 驗證所有題目
        validation_results = self.validate_all_challenges()
        
        # 2. 生成發布報告
        report_path = self.generate_release_report(validation_results)
        
        # 3. 檢查是否可以發布
        ready_count = sum(1 for r in validation_results if r['ready_for_release'])
        total_count = len(validation_results)
        
        print(f"\n📊 準備狀況：{ready_count}/{total_count} 個題目準備好發布")
        
        if ready_count == 0:
            print("❌ 沒有題目準備好發布，請先修復問題")
            return False
        
        # 4. 設置公開倉庫（如果提供）
        if public_repo_url:
            self.setup_public_repository(public_repo_url)
            self.create_github_pages_config()
        
        print(f"✅ 準備完成！請查看發布報告：{report_path}")
        
        if ready_count < total_count:
            print(f"⚠️  還有 {total_count - ready_count} 個題目未準備好")
        
        print("\n🔄 下一步：")
        print("1. 修復報告中提到的問題")
        print("2. 執行 uv run scripts/sync-to-public.py 進行發布")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='準備公開發布')
    parser.add_argument('--config', default='config.yml',
                       help='配置檔案路徑 (預設: config.yml)')
    parser.add_argument('--public-repo', 
                       help='公開倉庫 URL (例如: git@github.com:org/2024-ctf-public.git)')
    parser.add_argument('--validate-only', action='store_true',
                       help='只執行驗證，不進行其他準備工作')
    parser.add_argument('--challenge', 
                       help='驗證特定題目 (例如: challenges/web/example)')
    
    args = parser.parse_args()
    
    preparator = PublicReleasePreparator(args.config)
    
    if args.challenge:
        # 驗證特定題目
        challenge_path = Path(args.challenge)
        if not challenge_path.exists():
            print(f"❌ 題目路徑不存在：{challenge_path}")
            return
        
        result = preparator.validate_challenge(challenge_path)
        
        print(f"📁 題目：{result['path']}")
        print(f"📂 分類：{result['category']}")
        print(f"✅ 有效：{'是' if result['valid'] else '否'}")
        print(f"🚀 準備發布：{'是' if result['ready_for_release'] else '否'}")
        
        if result['issues']:
            print("\n❌ 發現問題：")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("\n✅ 沒有發現問題")
            
    elif args.validate_only:
        # 只執行驗證
        validation_results = preparator.validate_all_challenges()
        preparator.generate_release_report(validation_results)
    else:
        # 執行完整準備
        preparator.run_preparation(args.public_repo)

if __name__ == "__main__":
    main()