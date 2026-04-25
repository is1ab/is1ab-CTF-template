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
    
    def validate_inputs(self, category, name, difficulty):
        """驗證輸入參數"""
        # 驗證分類
        valid_categories = ['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general']
        if category not in valid_categories:
            print(f"❌ Invalid category: {category}")
            print(f"💡 Valid categories: {', '.join(valid_categories)}")
            return False
        
        # 驗證題目名稱
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            print(f"❌ Invalid challenge name: {name}")
            print("💡 Name should only contain letters, numbers, underscores, and hyphens")
            return False
        
        # 驗證難度
        valid_difficulties = ['baby', 'easy', 'middle', 'hard', 'impossible']
        if difficulty not in valid_difficulties:
            print(f"❌ Invalid difficulty: {difficulty}")
            print(f"💡 Valid difficulties: {', '.join(valid_difficulties)}")
            return False
        
        return True
    
    def create_challenge(self, category, name, difficulty, author='', challenge_type=None):
        """創建新題目"""
        try:
            # author 解析順序：--author > git config user.name > team.default_author
            if not author:
                # 1. 試 git user.name
                try:
                    proc = subprocess.run(
                        ["git", "config", "--get", "user.name"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if proc.returncode == 0:
                        author = (proc.stdout or "").strip()
                except Exception:
                    author = ""
            if not author:
                # 2. 退回 config.yml 的 team.default_author
                if isinstance(self.config, dict):
                    author = self.config.get('team', {}).get('default_author', '') or ''
                    author = author.strip() if isinstance(author, str) else ''
            if not author:
                print("❌ 無法決定出題人。請以下列任一方式指定：")
                print("   • 命令列: --author \"YourName\"")
                print("   • git: git config user.name \"YourName\"")
                print("   • config.yml: team.default_author")
                return False

            # 輸入驗證
            if not self.validate_inputs(category, name, difficulty):
                return False

            print(f"🚀 Creating challenge: {category}/{name}")
            
            # 決定題目類型
            if not challenge_type:
                challenge_type = self.detect_challenge_type(category)
            
            # 建立目錄結構
            challenge_path = Path(f"challenges/{category}/{name}")
            if challenge_path.exists():
                print(f"❌ Error: Challenge {category}/{name} already exists")
                return False
                
            self.create_directory_structure(challenge_path, challenge_type)
            
            # 建立配置檔案 (創建 private.yml，後續由它生成 public.yml)
            private_config = self.create_private_config(
                name, category, difficulty, author, challenge_type
            )
            self.save_private_config(challenge_path, private_config)
            
            # 生成 public.yml (從 private.yml 移除敏感資訊)
            public_config = self.generate_public_from_private(private_config)
            self.save_public_config(challenge_path, public_config)
            
            # 建立模板檔案
            self.create_template_files(challenge_path, private_config, challenge_type)
            
            # Git 操作
            self.create_git_branch(category, name)
            
            print(f"✅ Challenge created at: {challenge_path}")
            self.print_next_steps(challenge_path, challenge_type)
            return True
            
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
            print("💡 Please check file permissions or run with appropriate privileges")
            return False
        except OSError as e:
            print(f"❌ File system error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error creating challenge: {e}")
            print("💡 Please check your input and try again")
            return False
        
    def detect_challenge_type(self, category):
        """根據分類決定題目類型"""
        if category in ['pwn', 'reverse']:
            return 'nc_challenge'  # nc 題目適合 pwn 和 reverse
        elif category in ['web']:
            return 'static_container'
        else:
            return 'static_attachment'
    
    def create_directory_structure(self, base_path, challenge_type):
        """建立標準目錄結構"""
        try:
            base_dirs = [
                'src',
                'writeup',
                'files',
                'writeup/screenshots'
            ]
            
            # 根據題目類型決定額外目錄
            if challenge_type == 'nc_challenge':
                base_dirs.extend([
                    'bin',
                    'docker'
                ])
            else:
                base_dirs.append('docker')
            
            # 建立主目錄
            base_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {base_path}")
            
            # 建立子目錄
            for dir_name in base_dirs:
                dir_path = base_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created subdirectory: {dir_path}")
                
        except PermissionError as e:
            print(f"❌ Permission denied creating directories: {e}")
            raise
        except OSError as e:
            print(f"❌ Error creating directory structure: {e}")
            raise
            
    def create_private_config(self, name, category, difficulty, author, challenge_type):
        """建立 private.yml 配置（包含敏感資訊如 flag）"""
        flag_prefix = self.config['project']['flag_prefix']
        config = {
            'title': name.replace('_', ' ').replace('-', ' ').title(),
            'author': author,
            'difficulty': difficulty,
            'category': category,
            'description': 'TODO: Add challenge description here',
            'challenge_type': challenge_type,
            'source_code_provided': False,  # 是否提供原始碼
            'files': [],
            'status': 'planning',
            'points': self.config['points'].get(difficulty, 100),
            'tags': [category],
            'created_at': datetime.now().isoformat(),
            # 敏感資訊 (僅在 private.yml 中)
            'flag': f'{flag_prefix}{{TODO_replace_with_actual_flag}}',
            'flag_description': 'TODO: 描述如何獲得這個 flag',
            'solution_steps': [
                'TODO: 第一步解題步驟',
                'TODO: 第二步解題步驟', 
                'TODO: 第三步解題步驟'
            ],
            'internal_notes': 'TODO: 內部開發筆記，測試要點等',
            'deploy_info': {
                'port': None,
                'url': None,
                'requires_build': True
            },
            # 多階段提示系統
            'hints': [
                {
                    'level': 1,
                    'cost': 0,
                    'content': 'TODO: 第一個免費提示 - 引導參賽者思考方向'
                },
                {
                    'level': 2, 
                    'cost': 10,
                    'content': 'TODO: 第二個提示 - 提供具體的技術線索'
                },
                {
                    'level': 3,
                    'cost': 25,
                    'content': 'TODO: 第三個提示 - 給出關鍵步驟或工具'
                }
            ]
        }
        
        # nc 題目特殊配置
        if challenge_type == 'nc_challenge':
            config['deploy_info'].update({
                'nc_port': 9999,
                'timeout': 60,
                'connection_type': 'nc'
            })
        
        return config
    
    def save_private_config(self, challenge_path, config):
        """儲存 private.yml"""
        try:
            config_file = challenge_path / 'private.yml'
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"📝 Created: {config_file}")
        except IOError as e:
            print(f"❌ Failed to save private.yml: {e}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ YAML formatting error: {e}")
            raise
    
    def generate_public_from_private(self, private_config):
        """從 private.yml 生成 public.yml (移除敏感資訊)"""
        public_config = private_config.copy()
        
        # 移除敏感資訊
        sensitive_fields = [
            'flag', 'flag_description', 'solution_steps', 'internal_notes',
        ]
        for field in sensitive_fields:
            public_config.pop(field, None)
        
        return public_config
        
    def save_public_config(self, challenge_path, config):
        """儲存 public.yml"""
        try:
            config_file = challenge_path / 'public.yml'
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            print(f"📝 Created: {config_file}")
        except IOError as e:
            print(f"❌ Failed to save public.yml: {e}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ YAML formatting error: {e}")
            raise
            
    def create_template_files(self, challenge_path, config, challenge_type):
        """建立模板檔案"""
        # README.md
        readme_content = self.generate_readme_template(config, challenge_type)
        with open(challenge_path / 'README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        # Docker files
        if challenge_type == 'nc_challenge':
            self.create_nc_docker_files(challenge_path, config)
        else:
            self.create_web_docker_files(challenge_path, config)
        
        # Writeup template
        writeup_content = self.generate_writeup_template(config)
        with open(challenge_path / 'writeup/solution.md', 'w', encoding='utf-8') as f:
            f.write(writeup_content)
        
        # 題目特定檔案
        if challenge_type == 'nc_challenge':
            self.create_nc_challenge_files(challenge_path, config)
            
    def create_nc_docker_files(self, challenge_path, config):
        """建立 nc 題目的 Docker 檔案"""
        # Dockerfile for nc challenge
        dockerfile_content = """FROM ubuntu:22.04

# 安裝基本工具
RUN apt-get update && apt-get install -y \\
    xinetd \\
    socat \\
    && rm -rf /var/lib/apt/lists/*

# 建立 ctf 用戶
RUN useradd -m -s /bin/bash ctf

# 設定工作目錄
WORKDIR /home/ctf

# 複製題目檔案
COPY bin/ ./
COPY start.sh ./
COPY run.sh ./

# 設定權限
RUN chmod +x start.sh run.sh
RUN chmod +x ./* 2>/dev/null || true
RUN chown -R root:ctf /home/ctf
RUN chmod -R 750 /home/ctf

# 暴露端口
EXPOSE 9999

# 設定啟動命令
CMD ["./start.sh"]
"""
        
        # docker-compose.yml for nc challenge
        challenge_name = config['title'].lower().replace(' ', '-')
        compose_content = f"""version: '3.8'

services:
  {challenge_name}:
    build: .
    ports:
      - "9999:9999"
    environment:
      - FLAG={self.config['project']['flag_prefix']}{{placeholder_flag}}
      - TIMEOUT=60
    volumes:
      - ./logs:/home/ctf/logs
    restart: unless-stopped
    networks:
      - ctf-network
    security_opt:
      - no-new-privileges:true
    read_only: false
    tmpfs:
      - /tmp

networks:
  ctf-network:
    driver: bridge
"""
        
        docker_path = challenge_path / 'docker'
        with open(docker_path / 'Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        with open(docker_path / 'docker-compose.yml', 'w') as f:
            f.write(compose_content)
            
    def create_nc_challenge_files(self, challenge_path, config):
        """建立 nc 題目特定檔案"""
        flag_prefix = self.config['project']['flag_prefix']
        
        # start.sh - 啟動腳本
        start_sh_content = f"""#!/bin/bash

# 設定 flag 檔案
echo "$FLAG" > /home/ctf/flag.txt
chown root:ctf /home/ctf/flag.txt
chmod 640 /home/ctf/flag.txt

# 使用 socat 啟動服務
echo "Starting challenge on port 9999..."
socat TCP-LISTEN:9999,reuseaddr,fork EXEC:"timeout 60 ./run.sh",su=ctf,pty,stderr
"""
        
        # run.sh - 執行腳本
        run_sh_content = f"""#!/bin/bash

# 切換到 ctf 用戶目錄
cd /home/ctf

# 執行題目程式 (請修改為你的程式)
echo "Welcome to {config['title']}!"
echo "Try to get the flag!"

# 執行你的程式 (範例)
# timeout 60 ./your_program

# 暫時的 shell (僅供測試，正式環境請移除)
/bin/bash
"""
        
        # 範例 C 程式
        example_c_content = f"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main() {{
    char buffer[64];
    char flag[100];
    FILE *fp;
    
    // 讀取 flag
    fp = fopen("flag.txt", "r");
    if (fp == NULL) {{
        printf("Error: Cannot read flag\\n");
        exit(1);
    }}
    fgets(flag, sizeof(flag), fp);
    fclose(fp);
    
    printf("Welcome to {config['title']}!\\n");
    printf("Enter your input: ");
    fflush(stdout);
    
    // 簡單的緩衝區溢位漏洞範例
    gets(buffer);
    
    printf("You entered: %s\\n", buffer);
    
    // TODO: 加入你的題目邏輯
    
    return 0;
}}
"""
        
        # Makefile
        makefile_content = """CC = gcc
CFLAGS = -fno-stack-protector -no-pie -fno-pic
TARGET = challenge
SRC = challenge.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)

.PHONY: all clean
"""
        
        # 寫入檔案
        with open(challenge_path / 'docker/start.sh', 'w') as f:
            f.write(start_sh_content)
        with open(challenge_path / 'docker/run.sh', 'w') as f:
            f.write(run_sh_content)
        with open(challenge_path / 'src/challenge.c', 'w') as f:
            f.write(example_c_content)
        with open(challenge_path / 'src/Makefile', 'w') as f:
            f.write(makefile_content)
            
    def create_web_docker_files(self, challenge_path, config):
        """建立 Web 題目的 Docker 檔案"""
        # Dockerfile
        dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

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
            
    def generate_readme_template(self, config, challenge_type):
        """生成 README 模板"""
        flag_prefix = self.config['project']['flag_prefix']
        
        # 根據題目類型調整內容
        if challenge_type == 'nc_challenge':
            connection_info = f"""
## 連線資訊
- **本地測試**: `nc localhost 9999`
- **遠端連線**: `nc {config['deploy_info'].get('url', 'TBD')} 9999`
- **連線逾時**: {config['deploy_info'].get('timeout', 60)} 秒
"""
            quick_start = """
## 🏃‍♂️ 快速開始

### 本地測試
```bash
cd docker/
docker-compose up -d
nc localhost 9999
```

### 編譯題目
```bash
cd src/
make
cp challenge ../docker/bin/
```
"""
        else:
            connection_info = f"""
## 連線資訊
- **本地**: http://localhost:8080
- **遠端**: {config['deploy_info']['url'] or 'TBD'}
"""
            quick_start = """
## 🏃‍♂️ 快速開始

### 本地測試
```bash
cd docker/
docker-compose up -d
```
"""
        
        template = f"""# {config['title']}

**Author:** {config['author']}  
**Difficulty:** {config['difficulty']}  
**Category:** {config['category']}

---

{config['description']}

## Flag 格式
```
flag: {flag_prefix}{{fake_flag_example}}
```

## 題目類型
- [{'x' if config['challenge_type'] == 'static_attachment' else ' '}] **靜態附件**: 共用附件，任意 flag
- [{'x' if config['challenge_type'] == 'static_container' else ' '}] **靜態容器**: 共用容器，任意 flag  
- [{'x' if config['challenge_type'] == 'dynamic_attachment' else ' '}] **動態附件**: 依照隊伍分配附件
- [{'x' if config['challenge_type'] == 'dynamic_container' else ' '}] **動態容器**: 自動生成 flag，每隊唯一
- [{'x' if config['challenge_type'] == 'nc_challenge' else ' '}] **NC 題目**: 透過 netcat 連線的題目

## 提供的檔案
{chr(10).join(f'- `{file}` - 檔案描述' for file in config['files']) if config['files'] else '- 無'}

## 原始碼提供
- **是否提供原始碼**: {'✅ 是' if config.get('source_code_provided', False) else '❌ 否'}

{connection_info}

---

{quick_start}

## 🔧 開發資訊

- **狀態**: {config['status']}
- **分數**: {config['points']}
- **標籤**: {', '.join(config['tags'])}
- **建立時間**: {config['created_at'][:10]}

## 💡 題目提示

本題提供漸進式提示系統，幫助參賽者逐步解題：

### 提示 1 (免費)
{config['hints'][0]['content']}

### 提示 2 (消耗 {config['hints'][1]['cost']} 分)
{config['hints'][1]['content']}

### 提示 3 (消耗 {config['hints'][2]['cost']} 分)
{config['hints'][2]['content']}

---

## 🔍 解題思路 (僅內部可見)

<details>
<summary>點擊展開完整解答</summary>

**解題步驟**:
1. TODO: 第一步詳細分析
2. TODO: 第二步具體操作  
3. TODO: 第三步最終獲取

**實際 Flag**: 請見 `private.yml`

**解題腳本**: 參見 `writeup/exploit.py`

</details>

## 📁 檔案說明

- `src/`: 完整源碼
- `docker/`: Docker 部署檔案
- `bin/`: 編譯後的可執行檔案 (nc 題目)
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
{self.config['project']['flag_prefix']}{{fake_flag_placeholder}}
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
    
    def print_next_steps(self, challenge_path, challenge_type):
        """印出後續步驟"""
        # 從路徑提取 category 和 name
        parts = str(challenge_path).replace("\\", "/").split("/")
        category = parts[-2] if len(parts) >= 2 else "category"
        name = parts[-1] if len(parts) >= 1 else "name"

        print()
        print("=" * 60)
        print("📝 接下來你需要做的事情：")
        print("=" * 60)
        print()
        print(f"  1. 編輯 Flag（最重要！）")
        print(f"     編輯 {challenge_path}/private.yml")
        print(f"     → 找到 \"flag:\" 欄位，設定你的 flag 值")
        prefix = self.config.get('flag_prefix', 'FLAG_PREFIX')
        print(f"     → 格式：{prefix}" + "{你的flag內容}")
        print()
        print(f"  2. 填寫題目資訊")
        print(f"     編輯 {challenge_path}/public.yml")
        print(f"     → 修改 title、description、tags")
        print(f"     → ⚠️  不要在這裡放 flag！")
        print()
        print(f"  3. 實作題目")
        print(f"     → 原始碼放在 {challenge_path}/src/")

        if challenge_type == 'nc_challenge':
            print(f"     → 編譯：cd {challenge_path}/src && make")
            print(f"     → 複製執行檔到 {challenge_path}/docker/bin/")
            print(f"     → 測試：cd {challenge_path}/docker && docker-compose up")
            print(f"     → 連線測試：nc localhost 9999")
        elif challenge_type in ('static_container', 'dynamic_container'):
            print(f"     → 如需 Docker：編輯 {challenge_path}/docker/")
            print(f"     → 測試：cd {challenge_path}/docker && docker-compose up")
        else:
            print(f"     → 附件放在 {challenge_path}/files/")

        print()
        print(f"  4. 驗證與驗題")
        print(f"     make validate ARGS=\"{challenge_path}\"")
        print(f"     make scan")
        print(f"     啟動 Web UI 的「驗題」分頁，或維護 public.yml 的 validation_status / reviewer")
        print()
        print(f"  5. 提交")
        print(f"     git add {challenge_path}/")
        print(f"     git commit -m \"feat({category}): add {name} challenge\"")
        print(f"     git push origin challenge/{category}/{name}")
        print()
        print(f"  📖 完整教學：QUICKSTART.md")
        print(f"  ❓ 遇到問題：docs/troubleshooting.md")
        print()

def main():
    try:
        parser = argparse.ArgumentParser(description='Create new CTF challenge')
        parser.add_argument('category', 
                           choices=['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general'],
                           help='Challenge category')
        parser.add_argument('name', help='Challenge name (use underscore for spaces)')
        parser.add_argument('difficulty', 
                           choices=['baby', 'easy', 'middle', 'hard', 'impossible'],
                           help='Challenge difficulty')
        parser.add_argument('--author', default='',
                           help='出題人（未填則使用 git user.name，再退回 config.yml team.default_author）')
        parser.add_argument('--type', choices=['static_attachment', 'static_container', 'dynamic_attachment', 'dynamic_container', 'nc_challenge'],
                           help='Challenge type (auto-detect if not specified)')
        parser.add_argument('--config', default='config.yml', help='Config file path')
        
        args = parser.parse_args()
        
        # 檢查配置檔案
        if not os.path.exists(args.config):
            print(f"⚠️  Config file {args.config} not found, using default settings")
        
        creator = ChallengeCreator(args.config)
        success = creator.create_challenge(
            args.category, args.name, args.difficulty, args.author, args.type
        )
        
        if success:
            print("\n🎉 Challenge creation completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Challenge creation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Please check your input and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()