#!/usr/bin/env python3
# scripts/update-readme.py

import yaml
import json
from pathlib import Path
from jinja2 import Template
from datetime import datetime
import argparse

class ReadmeUpdater:
    def __init__(self, config_path='config.yml'):
        self.load_config(config_path)
        self.challenges = {}
        self.stats = {}
        
    def load_config(self, config_path):
        """載入配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.config = {'project': {'name': 'is1ab-CTF'}}
            
    def collect_challenges(self):
        """收集所有題目資訊"""
        challenges_dir = Path('challenges')
        if not challenges_dir.exists():
            print("⚠️  No challenges directory found")
            return
            
        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category = category_dir.name
            self.challenges[category] = []
            
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                    
                public_yml = challenge_dir / 'public.yml'
                if public_yml.exists():
                    try:
                        with open(public_yml, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            data['folder_name'] = challenge_dir.name
                            data['path'] = str(challenge_dir)
                            self.challenges[category].append(data)
                    except Exception as e:
                        print(f"⚠️  Error reading {public_yml}: {e}")
                        
    def calculate_stats(self):
        """計算統計資訊"""
        total_challenges = 0
        status_counts = {'planning': 0, 'developing': 0, 'testing': 0, 'completed': 0, 'deployed': 0}
        category_counts = {}
        difficulty_counts = {'baby': 0, 'easy': 0, 'middle': 0, 'hard': 0, 'impossible': 0}
        type_counts = {'static_attachment': 0, 'static_container': 0, 'dynamic_attachment': 0, 'dynamic_container': 0, 'nc_challenge': 0}
        source_code_counts = {'provided': 0, 'not_provided': 0}
        
        for category, challenges in self.challenges.items():
            category_counts[category] = len(challenges)
            total_challenges += len(challenges)
            
            for challenge in challenges:
                status = challenge.get('status', 'planning')
                difficulty = challenge.get('difficulty', 'easy')
                challenge_type = challenge.get('challenge_type', 'static_attachment')
                source_code_provided = challenge.get('source_code_provided', False)
                
                if status in status_counts:
                    status_counts[status] += 1
                if difficulty in difficulty_counts:
                    difficulty_counts[difficulty] += 1
                if challenge_type in type_counts:
                    type_counts[challenge_type] += 1
                
                if source_code_provided:
                    source_code_counts['provided'] += 1
                else:
                    source_code_counts['not_provided'] += 1
                    
        self.stats = {
            'total_challenges': total_challenges,
            'status_counts': status_counts,
            'category_counts': category_counts,
            'difficulty_counts': difficulty_counts,
            'type_counts': type_counts,
            'source_code_counts': source_code_counts,
            'last_updated': datetime.now().isoformat()
        }
        
    def generate_progress_table(self):
        """生成進度表格"""
        categories = ['general', 'web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc']
        
        # 找出最大題目數量
        max_challenges = 0
        for cat in categories:
            if cat in self.challenges:
                max_challenges = max(max_challenges, len(self.challenges[cat]))
        
        # 至少顯示 6 個欄位 (A-F)
        max_challenges = max(max_challenges, 6)
        
        # 生成表格標題
        headers = ['分類'] + [chr(65 + i) for i in range(max_challenges)]
        
        # 生成表格行
        table_rows = []
        for category in categories:
            row = [category.title()]
            challenges = self.challenges.get(category, [])
            
            for i in range(max_challenges):
                if i < len(challenges):
                    status = challenges[i].get('status', 'planning')
                    challenge_type = challenges[i].get('challenge_type', 'static_attachment')
                    icon = self.get_status_icon(status, challenge_type)
                    # 添加標題資訊
                    title = challenges[i].get('title', f'Challenge {chr(65 + i)}')
                    row.append(f"{icon}")
                else:
                    row.append('❌')
            
            table_rows.append(row)
            
        return headers, table_rows
        
    def get_status_icon(self, status, challenge_type=None):
        """取得狀態圖示"""
        status_icons = {
            'planning': '📝',
            'developing': '🔨',
            'testing': '🧪',
            'completed': '✅',
            'deployed': '🚀'
        }
        
        # 根據題目類型添加額外標示
        type_indicators = {
            'nc_challenge': '🔌',
            'static_container': '🐳',
            'dynamic_container': '🔄',
            'static_attachment': '📎',
            'dynamic_attachment': '📋'
        }
        
        base_icon = status_icons.get(status, '❓')
        type_icon = type_indicators.get(challenge_type, '')
        
        return f"{base_icon}{type_icon}" if type_icon else base_icon
        
    def generate_team_assignments(self):
        """生成團隊任務分配"""
        assignments = {}
        
        for category, challenges in self.challenges.items():
            for challenge in challenges:
                author = challenge.get('author', 'Unknown')
                if author not in assignments:
                    assignments[author] = []
                    
                assignments[author].append({
                    'category': category,
                    'title': challenge.get('title', 'Untitled'),
                    'status': challenge.get('status', 'planning'),
                    'difficulty': challenge.get('difficulty', 'easy'),
                    'challenge_type': challenge.get('challenge_type', 'static_attachment'),
                    'source_code_provided': challenge.get('source_code_provided', False)
                })
                
        return assignments
        
    def update_readme(self, template_path='templates/README.md.j2'):
        """更新 README.md"""
        if not Path(template_path).exists():
            # 使用內建模板
            template_content = self.get_default_template()
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
        template = Template(template_content)
        
        headers, table_rows = self.generate_progress_table()
        team_assignments = self.generate_team_assignments()
        
        readme_content = template.render(
            config=self.config,
            challenges=self.challenges,
            stats=self.stats,
            table_headers=headers,
            table_rows=table_rows,
            team_assignments=team_assignments,
            last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        print("✅ README.md updated successfully")
        
    def get_default_template(self):
        """預設 README 模板"""
        return """# {{ config.project.name }}

About Top secret for first-year graduate student - {{ config.project.year or 'YYYY' }} 🥷  
Welcome Event!

## 📋 目錄
- [CTF 平台](#ctf-平台)
- [專案結構](#專案結構)
- [題目開發流程](#題目開發流程)
- [Docker 部署](#docker-部署)
- [題目進度追蹤](#題目進度追蹤)
- [提交規範](#提交規範)

## 🏆 CTF 平台
- **GZCTF** (新生盃/比賽用): {{ config.platform.gzctf_url or 'http://140.124.181.153:8080/' }}
- **CTFd** (練習/上課用): {{ config.platform.ctfd_url or 'http://140.124.181.153/' }}
- **文件分享** (大型附件): {{ config.platform.zipline_url or 'http://140.124.181.153:3000' }}

## 📊 題目進度追蹤

### 總體進度
- 📝 **規劃中**: {{ stats.status_counts.planning }} 題
- 🔨 **開發中**: {{ stats.status_counts.developing }} 題  
- 🧪 **測試中**: {{ stats.status_counts.testing }} 題
- ✅ **已完成**: {{ stats.status_counts.completed }} 題
- 🚀 **已部署**: {{ stats.status_counts.deployed }} 題

### 題目類型分布
- 📎 **靜態附件**: {{ stats.type_counts.static_attachment }} 題
- 🐳 **靜態容器**: {{ stats.type_counts.static_container }} 題
- 📋 **動態附件**: {{ stats.type_counts.dynamic_attachment }} 題
- 🔄 **動態容器**: {{ stats.type_counts.dynamic_container }} 題
- 🔌 **NC 題目**: {{ stats.type_counts.nc_challenge }} 題

### 難度分佈
- 🍼 **Baby**: {{ stats.difficulty_counts.baby }} 題
- ⭐ **Easy**: {{ stats.difficulty_counts.easy }} 題
- ⭐⭐ **Middle**: {{ stats.difficulty_counts.middle }} 題
- ⭐⭐⭐ **Hard**: {{ stats.difficulty_counts.hard }} 題
- 💀 **Impossible**: {{ stats.difficulty_counts.impossible }} 題

### 原始碼提供狀況
- 📄 **提供原始碼**: {{ stats.source_code_counts.provided }} 題
- 🔒 **不提供原始碼**: {{ stats.source_code_counts.not_provided }} 題

### 詳細進度表
| {{ table_headers | join(' | ') }} |
|{{ '---|' * table_headers|length }}
{% for row in table_rows -%}
| {{ row | join(' | ') }} |
{% endfor %}

**圖例**:
- ✅ 已完成並部署
- 🔨 開發/測試中  
- 📝 規劃中
- ❌ 尚未開始
- 🔌 NC 題目 | 🐳 容器 | 📎 附件

### 個人任務分配
{% for author, tasks in team_assignments.items() %}
#### {{ author }}
{% for task in tasks -%}
- **{{ task.category|title }}/{{ task.title }}**: {{ task.status }} ({{ task.difficulty }}) [{{ task.challenge_type }}] {'📄' if task.source_code_provided else '🔒'}
{% endfor %}
{% endfor %}

## 🚀 快速開始

### 創建新題目
```bash
# Web 題目
python scripts/create-challenge.py web sql_injection middle

# PWN 題目 (自動使用 nc 環境)
python scripts/create-challenge.py pwn buffer_overflow hard

# 指定題目類型
python scripts/create-challenge.py misc flag_checker easy --type nc_challenge
```

### 更新進度
```bash
# 更新 README
python scripts/update-readme.py

# 驗證題目
python scripts/validate-challenge.py challenges/web/example/
```

## 🔧 開發指南

### NC 題目開發流程
1. 創建題目: `python scripts/create-challenge.py pwn example_pwn hard`
2. 編輯源碼: `challenges/pwn/example_pwn/src/challenge.c`
3. 編譯程式: `cd challenges/pwn/example_pwn/src && make`
4. 複製執行檔: `cp challenge ../docker/bin/`
5. 修改執行腳本: 編輯 `docker/run.sh`
6. 測試部署: `cd docker && docker-compose up -d`
7. 測試連線: `nc localhost 9999`

### 容器題目開發流程
1. 創建題目: `python scripts/create-challenge.py web example_web middle`
2. 開發應用: 在 `src/` 目錄開發
3. 配置 Docker: 修改 `docker/` 下的檔案
4. 測試部署: `cd docker && docker-compose up -d`
5. 測試訪問: http://localhost:8080

## 📝 提交規範

### Git 分支命名
- `challenge/[category]/[name]` - 新題目開發
- `fix/[category]/[name]` - 問題修復
- `docs/[topic]` - 文檔更新

### Commit 訊息格式
```
feat(web): add sql injection challenge
fix(pwn): resolve buffer overflow issue
docs: update development guide
```

### PR 檢查清單
- [ ] 題目可正常執行
- [ ] Docker 建構成功
- [ ] README.md 完整
- [ ] Writeup 已完成
- [ ] 無敏感資料洩露

---
**最後更新**: {{ last_updated }}  
**總題目數**: {{ stats.total_challenges }}

**⭐ 如果這個專案對你有幫助，請給我們一個 Star！**
"""

    def export_json(self, output_path='progress.json'):
        """匯出 JSON 格式"""
        data = {
            'challenges': self.challenges,
            'stats': self.stats,
            'meta': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Progress exported to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Update README and progress')
    parser.add_argument('--config', default='config.yml', help='Config file path')
    parser.add_argument('--template', default='templates/README.md.j2', help='README template')
    parser.add_argument('--export-json', action='store_true', help='Export JSON format')
    
    args = parser.parse_args()
    
    updater = ReadmeUpdater(args.config)
    updater.collect_challenges()
    updater.calculate_stats()
    updater.update_readme(args.template)
    
    if args.export_json:
        updater.export_json()

if __name__ == "__main__":
    main()