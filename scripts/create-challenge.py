#!/usr/bin/env python3
# scripts/create-challenge.py

import os
import sys
import yaml
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

class ChallengeCreator:
    def __init__(self, config_path='config.yml'):
        self.load_config(config_path)
        
    def load_config(self, config_path):
        """載入專案配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.config = self.get_default_config()
            
    def get_default_config(self):
        """預設配置"""
        return {
            'project': {
                'name': 'is1ab-CTF',
                'flag_prefix': 'is1abCTF'
            },
            'points': {
                'baby': 50,
                'easy': 100,
                'middle': 200,
                'hard': 300,
                'impossible': 500
            }
        }
    
    def create_challenge(self, category, name, difficulty, author='GZTime'):
        """創建新題目"""
        print(f"🚀 Creating challenge: {category}/{name}")
        
        # 建立目錄結構
        challenge_path = Path(f"challenges/{category}/{name}")
        self.create_directory_structure(challenge_path)
        
        # 建立配置檔案
        public_config = self.create_public_config(name, category, difficulty, author)
        self.save_public_config(challenge_path, public_config)
        
        # 建立模板檔案
        self.create_template_files(challenge_path, public_config)
        
        # Git 操作
        self.create_git_branch(category, name)
        
        print(f"✅ Challenge created at: {challenge_path}")
        print(f"📝 Next steps:")
        print(f"   1. Edit {challenge_path}/public.yml")
        print(f"   2. Develop your challenge in {challenge_path}/src/")
        print(f"   3. Add writeup in {challenge_path}/writeup/")
        print(f"   4. Test with Docker: cd {challenge_path}/docker && docker-compose up")
        print(f"   5. Create PR when ready")
        
    def create_directory_structure(self, base_path):
        """建立標準目錄結構"""
        directories = [
            'src',
            'docker', 
            'writeup',
            'files',
            'writeup/screenshots'
        ]
        
        for dir_name in directories:
            (base_path / dir_name).mkdir(parents=True, exist_ok=True)
            
    def create_public_config(self, name, category, difficulty, author):
        """建立 public.yml 配置"""
        return {
            'title': name.replace('_', ' ').replace('-', ' ').title(),
            'author': author,
            'difficulty': difficulty,
            'category': category,
            'description': 'TODO: Add challenge description here',
            'challenge_type': 'static_container',
            'files': [],
            'status': 'planning',
            'points': self.config['points'].get(difficulty, 100),
            'tags': [category],
            'created_at': datetime.now().isoformat(),
            'deploy_info': {
                'port': None,
                'url': None,
                'requires_build': True
            }
        }
        
    def save_public_config(self, challenge_path, config):
        """儲存 public.yml"""
        config_file = challenge_path / 'public.yml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
    def create_template_files(self, challenge_path, config):
        """建立模板檔案"""
        # README.md
        readme_content = self.generate_readme_template(config)
        with open(challenge_path / 'README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        # Docker files
        self.create_docker_files(challenge_path, config)
        
        # Writeup template
        writeup_content = self.generate_writeup_template(config)
        with open(challenge_path / 'writeup/solution.md', 'w', encoding='utf-8') as f:
            f.write(writeup_content)
            
    def generate_readme_template(self, config):
        """生成 README 模板"""
        flag_prefix = self.config['project']['flag_prefix']
        
        template = f"""# {config['title']}

**Author:** {config['author']}  
**Difficulty:** {config['difficulty']}  
**Category:** {config['category']}

---

{config['description']}

## Flag 格式
```
flag: {flag_prefix}{{...}}
```

## 題目類型
- [{'x' if config['challenge_type'] == 'static_attachment' else ' '}] **靜態附件**: 共用附件，任意 flag
- [{'x' if config['challenge_type'] == 'static_container' else ' '}] **靜態容器**: 共用容器，任意 flag  
- [{'x' if config['challenge_type'] == 'dynamic_attachment' else ' '}] **動態附件**: 依照隊伍分配附件
- [{'x' if config['challenge_type'] == 'dynamic_container' else ' '}] **動態容器**: 自動生成 flag，每隊唯一

## 提供的檔案
{chr(10).join(f'- `{file}` - 檔案描述' for file in config['files']) if config['files'] else '- 無'}

---

## 🏃‍♂️ 快速開始

### 本地測試
```bash
cd docker/
docker-compose up -d
```

### 訪問方式
- **本地**: http://localhost:8080
- **遠端**: {config['deploy_info']['url'] or 'TBD'}

## 🔧 開發資訊

- **狀態**: {config['status']}
- **分數**: {config['points']}
- **標籤**: {', '.join(config['tags'])}
- **建立時間**: {config['created_at'][:10]}

## 🔍 解題思路 (僅內部可見)

<details>
<summary>點擊展開解題提示</summary>

1. TODO: 第一步提示
2. TODO: 第二步提示  
3. TODO: 第三步提示

**實際 Flag**: `{flag_prefix}{{TODO_actual_flag_here}}`

</details>

## 📁 檔案說明

- `src/`: 完整源碼
- `docker/`: Docker 部署檔案
- `files/`: 提供給參賽者的檔案
- `writeup/`: 官方詳細解答

## ⚠️ 注意事項

- TODO: 添加特殊注意事項
- TODO: 安全考量
- TODO: 效能考量

---
**最後更新**: {datetime.now().strftime('%Y-%m-%d')}  
**測試狀態**: ❌ 待測試
"""
        return template
        
    def create_docker_files(self, challenge_path, config):
        """建立 Docker 檔案"""
        # Dockerfile
        dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 設定權限
RUN chmod +x *.sh 2>/dev/null || true

# 暴露端口
EXPOSE 80

# 啟動命令
CMD ["python", "app.py"]
"""
        
        # docker-compose.yml
        compose_content = f"""version: '3.8'

services:
  {config['title'].lower().replace(' ', '-')}:
    build: .
    ports:
      - "8080:80"
    environment:
      - FLAG={self.config['project']['flag_prefix']}{{placeholder_flag}}
      - DEBUG=false
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - ctf-network

networks:
  ctf-network:
    driver: bridge
"""
        
        # requirements.txt
        requirements_content = """flask==2.3.3
gunicorn==21.2.0
"""
        
        docker_path = challenge_path / 'docker'
        with open(docker_path / 'Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        with open(docker_path / 'docker-compose.yml', 'w') as f:
            f.write(compose_content)
        with open(docker_path / 'requirements.txt', 'w') as f:
            f.write(requirements_content)
            
    def generate_writeup_template(self, config):
        """生成 Writeup 模板"""
        return f"""# {config['title']} - Writeup

## 題目資訊
- **分類**: {config['category']}
- **難度**: {config['difficulty']}
- **分數**: {config['points']}

## 題目描述

{config['description']}

## 解題步驟

### 第一步：分析題目

TODO: 描述分析過程

### 第二步：找出漏洞

TODO: 描述漏洞發現過程

### 第三步：構造 Payload

TODO: 描述 exploit 構造

```python
# exploit.py
# TODO: 添加自動化腳本
```

### 第四步：獲取 Flag

TODO: 描述最終獲取 flag 的過程

## Flag

```
{self.config['project']['flag_prefix']}{{TODO_actual_flag}}
```

## 學習重點

- TODO: 列出學習重點
- TODO: 相關技術

## 參考資料

- [參考連結1](https://example.com)
- [參考連結2](https://example.com)
"""
        
    def create_git_branch(self, category, name):
        """建立 Git 分支"""
        branch_name = f"challenge/{category}/{name}"
        
        try:
            # 建立並切換到新分支
            subprocess.run(['git', 'checkout', '-b', branch_name], 
                         check=True, capture_output=True)
            
            # 添加檔案
            subprocess.run(['git', 'add', f'challenges/{category}/{name}/'], 
                         check=True, capture_output=True)
            
            print(f"📝 Created branch: {branch_name}")
            print(f"💡 Use: git commit -m 'feat({category}): add {name} challenge'")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git operation failed: {e}")
            print("📝 Please manually create branch and commit")

def main():
    parser = argparse.ArgumentParser(description='Create new CTF challenge')
    parser.add_argument('category', 
                       choices=['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general'],
                       help='Challenge category')
    parser.add_argument('name', help='Challenge name (use underscore for spaces)')
    parser.add_argument('difficulty', 
                       choices=['baby', 'easy', 'middle', 'hard', 'impossible'],
                       help='Challenge difficulty')
    parser.add_argument('--author', default='GZTime', help='Challenge author')
    parser.add_argument('--config', default='config.yml', help='Config file path')
    
    args = parser.parse_args()
    
    creator = ChallengeCreator(args.config)
    creator.create_challenge(args.category, args.name, args.difficulty, args.author)

if __name__ == "__main__":
    main()

---

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
        
        for category, challenges in self.challenges.items():
            category_counts[category] = len(challenges)
            total_challenges += len(challenges)
            
            for challenge in challenges:
                status = challenge.get('status', 'planning')
                difficulty = challenge.get('difficulty', 'easy')
                
                if status in status_counts:
                    status_counts[status] += 1
                if difficulty in difficulty_counts:
                    difficulty_counts[difficulty] += 1
                    
        self.stats = {
            'total_challenges': total_challenges,
            'status_counts': status_counts,
            'category_counts': category_counts,
            'difficulty_counts': difficulty_counts,
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
                    icon = self.get_status_icon(status)
                    # 添加標題資訊
                    title = challenges[i].get('title', f'Challenge {chr(65 + i)}')
                    row.append(f"{icon}")
                else:
                    row.append('❌')
            
            table_rows.append(row)
            
        return headers, table_rows
        
    def get_status_icon(self, status):
        """取得狀態圖示"""
        icons = {
            'planning': '📝',
            'developing': '🔨',
            'testing': '🧪',
            'completed': '✅',
            'deployed': '🚀'
        }
        return icons.get(status, '❓')
        
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
                    'difficulty': challenge.get('difficulty', 'easy')
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

### 個人任務分配
{% for author, tasks in team_assignments.items() %}
#### {{ author }}
{% for task in tasks -%}
- **{{ task.category|title }}/{{ task.title }}**: {{ task.status }} ({{ task.difficulty }})
{% endfor %}
{% endfor %}

---
**最後更新**: {{ last_updated }}  
**總題目數**: {{ stats.total_challenges }}
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

---

#!/usr/bin/env python3
# scripts/validate-challenge.py

import yaml
import sys
from pathlib import Path
import argparse
import subprocess
import json

class ChallengeValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_challenge(self, challenge_path):
        """驗證單個題目"""
        challenge_path = Path(challenge_path)
        
        if not challenge_path.exists():
            self.errors.append(f"Challenge path does not exist: {challenge_path}")
            return False
            
        print(f"🔍 Validating challenge: {challenge_path}")
        
        # 驗證目錄結構
        self.validate_directory_structure(challenge_path)
        
        # 驗證 public.yml
        self.validate_public_yml(challenge_path)
        
        # 驗證 Docker 檔案
        self.validate_docker_files(challenge_path)
        
        # 驗證敏感資料
        self.check_sensitive_data(challenge_path)
        
        return len(self.errors) == 0
        
    def validate_directory_structure(self, challenge_path):
        """驗證目錄結構"""
        required_dirs = ['src', 'docker', 'writeup', 'files']
        required_files = ['README.md', 'public.yml']
        
        for dir_name in required_dirs:
            dir_path = challenge_path / dir_name
            if not dir_path.exists():
                self.warnings.append(f"Missing directory: {dir_path}")
                
        for file_name in required_files:
            file_path = challenge_path / file_name
            if not file_path.exists():
                self.errors.append(f"Missing required file: {file_path}")
                
    def validate_public_yml(self, challenge_path):
        """驗證 public.yml 格式"""
        public_yml = challenge_path / 'public.yml'
        
        if not public_yml.exists():
            return
            
        try:
            with open(public_yml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # 必要欄位檢查
            required_fields = ['title', 'author', 'difficulty', 'category', 'description']
            for field in required_fields:
                if field not in data:
                    self.errors.append(f"Missing required field in public.yml: {field}")
                elif not data[field] or data[field] == f"TODO: Add {field}":
                    self.warnings.append(f"Field '{field}' needs to be updated in public.yml")
                    
            # 值驗證
            valid_difficulties = ['baby', 'easy', 'middle', 'hard', 'impossible']
            if data.get('difficulty') not in valid_difficulties:
                self.errors.append(f"Invalid difficulty: {data.get('difficulty')}")
                
            valid_categories = ['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general']
            if data.get('category') not in valid_categories:
                self.errors.append(f"Invalid category: {data.get('category')}")
                
            valid_statuses = ['planning', 'developing', 'testing', 'completed', 'deployed']
            if data.get('status') not in valid_statuses:
                self.warnings.append(f"Invalid status: {data.get('status')}")
                
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in public.yml: {e}")
        except Exception as e:
            self.errors.append(f"Error reading public.yml: {e}")
            
    def validate_docker_files(self, challenge_path):
        """驗證 Docker 檔案"""
        docker_dir = challenge_path / 'docker'
        
        if not docker_dir.exists():
            return
            
        dockerfile = docker_dir / 'Dockerfile'
        compose_file = docker_dir / 'docker-compose.yml'
        
        if dockerfile.exists():
            self.validate_dockerfile(dockerfile)
            
        if compose_file.exists():
            self.validate_compose_file(compose_file)
            
    def validate_dockerfile(self, dockerfile_path):
        """驗證 Dockerfile"""
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                
            # 基本檢查
            if 'FROM' not in content:
                self.errors.append("Dockerfile missing FROM instruction")
                
            if 'EXPOSE' not in content:
                self.warnings.append("Dockerfile should include EXPOSE instruction")
                
            # 安全性檢查
            if 'root' in content.lower() and 'user' not in content.lower():
                self.warnings.append("Consider using non-root user in Dockerfile")
                
        except Exception as e:
            self.errors.append(f"Error reading Dockerfile: {e}")
            
    def validate_compose_file(self, compose_path):
        """驗證 docker-compose.yml"""
        try:
            with open(compose_path, 'r') as f:
                data = yaml.safe_load(f)
                
            if 'services' not in data:
                self.errors.append("docker-compose.yml missing services section")
                return
                
            for service_name, service_config in data['services'].items():
                # 檢查端口配置
                if 'ports' in service_config:
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str) and ':' in port_mapping:
                            host_port = port_mapping.split(':')[0]
                            if host_port.isdigit() and int(host_port) < 1024:
                                self.warnings.append(f"Service {service_name} uses privileged port {host_port}")
                                
                # 檢查環境變數
                if 'environment' in service_config:
                    env_vars = service_config['environment']
                    if isinstance(env_vars, list):
                        for env_var in env_vars:
                            if 'FLAG=' in env_var and 'placeholder' not in env_var:
                                self.warnings.append("Hardcoded flag found in docker-compose.yml")
                                
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in docker-compose.yml: {e}")
        except Exception as e:
            self.errors.append(f"Error reading docker-compose.yml: {e}")
            
    def check_sensitive_data(self, challenge_path):
        """檢查敏感資料"""
        sensitive_patterns = [
            r'is1ab[Cc][Tt][Ff]\{[^}]+\}',  # Flag pattern
            r'password\s*[:=]\s*["\']?[^"\s\']+',  # Password
            r'secret\s*[:=]\s*["\']?[^"\s\']+',    # Secret
            r'token\s*[:=]\s*["\']?[^"\s\']+',     # Token
        ]
        
        # 檢查特定檔案
        files_to_check = [
            'README.md',
            'public.yml',
            'docker/docker-compose.yml'
        ]
        
        for file_name in files_to_check:
            file_path = challenge_path / file_name
            if file_path.exists():
                self.check_file_for_sensitive_data(file_path, sensitive_patterns)
                
    def check_file_for_sensitive_data(self, file_path, patterns):
        """檢查檔案中的敏感資料"""
        import re
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    if 'placeholder' not in content.lower():
                        self.warnings.append(f"Potential sensitive data in {file_path}: {matches[0][:20]}...")
                        
        except Exception as e:
            self.warnings.append(f"Could not check {file_path}: {e}")
            
    def validate_all_challenges(self):
        """驗證所有題目"""
        challenges_dir = Path('challenges')
        if not challenges_dir.exists():
            print("❌ No challenges directory found")
            return False
            
        all_valid = True
        
        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                    
                # 重置錯誤列表
                self.errors = []
                self.warnings = []
                
                if not self.validate_challenge(challenge_dir):
                    all_valid = False
                    
                self.print_results(challenge_dir)
                
        return all_valid
        
    def print_results(self, challenge_path):
        """列印驗證結果"""
        if not self.errors and not self.warnings:
            print(f"✅ {challenge_path.name}: All checks passed")
            return
            
        print(f"\n📋 Validation results for {challenge_path.name}:")
        
        if self.errors:
            print("❌ Errors:")
            for error in self.errors:
                print(f"   - {error}")
                
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
                
        print()

def main():
    parser = argparse.ArgumentParser(description='Validate CTF challenges')
    parser.add_argument('path', nargs='?', help='Path to specific challenge (optional)')
    parser.add_argument('--all', action='store_true', help='Validate all challenges')
    parser.add_argument('--pr', type=int, help='PR number to validate')
    
    args = parser.parse_args()
    
    validator = ChallengeValidator()
    
    if args.pr:
        # 取得 PR 變更的檔案
        try:
            result = subprocess.run(['git', 'diff', '--name-only', f'origin/main...HEAD'], 
                                  capture_output=True, text=True, check=True)
            changed_files = result.stdout.strip().split('\n')
            
            # 找出變更的 challenge 目錄
            challenge_dirs = set()
            for file_path in changed_files:
                if file_path.startswith('challenges/'):
                    parts = Path(file_path).parts
                    if len(parts) >= 3:  # challenges/category/name/...
                        challenge_dir = Path(parts[0]) / parts[1] / parts[2]
                        challenge_dirs.add(challenge_dir)
                        
            if not challenge_dirs:
                print("✅ No challenges to validate")
                return
                
            all_valid = True
            for challenge_dir in challenge_dirs:
                validator.errors = []
                validator.warnings = []
                if not validator.validate_challenge(challenge_dir):
                    all_valid = False
                validator.print_results(challenge_dir)
                
            sys.exit(0 if all_valid else 1)
            
        except subprocess.CalledProcessError:
            print("❌ Could not get PR diff")
            sys.exit(1)
            
    elif args.all:
        success = validator.validate_all_challenges()
        sys.exit(0 if success else 1)
        
    elif args.path:
        validator.errors = []
        validator.warnings = []
        success = validator.validate_challenge(args.path)
        validator.print_results(Path(args.path))
        sys.exit(0 if success else 1)
        
    else:
        print("Please specify --all, --pr <number>, or a specific challenge path")
        sys.exit(1)

if __name__ == "__main__":
    main()