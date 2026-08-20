#!/usr/bin/env python3
# scripts/create-challenge.py

import os
import sys
import yaml
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
import challenge_schema as cs  # noqa: E402  單一真相：難度/建議分類詞彙

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
        # 分類：自由填寫（非建議值只提醒不擋，見 docs/challenge-schema.md 決策 8）
        suggested = cs.SUGGESTED_CATEGORIES
        if not category:
            print("❌ category 不可為空")
            return False
        if category not in suggested:
            print(f"💡 非建議分類 '{category}'（允許自由填寫；建議 {', '.join(suggested)}）")

        # 驗證題目名稱
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            print(f"❌ Invalid challenge name: {name}")
            print("💡 Name should only contain letters, numbers, underscores, and hyphens")
            return False

        # 難度：控制詞彙（medium→middle 別名由呼叫端正規化）
        valid_difficulties = cs.DIFFICULTIES
        if difficulty not in valid_difficulties:
            print(f"❌ Invalid difficulty: {difficulty}")
            print(f"💡 Valid difficulties: {', '.join(valid_difficulties)}")
            return False

        return True
    
    def create_challenge(self, category, name, difficulty, author='', deploy_type=None, connection_type=None):
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

            # 決定交付方式（deploy_type + connection_type）
            detected_dt, detected_conn = self.detect_deploy(category)
            if not deploy_type:
                deploy_type = detected_dt
                connection_type = detected_conn
            elif connection_type is None:
                connection_type = detected_conn if deploy_type == 'container' else ''

            # 建立目錄結構
            challenge_path = Path(f"challenges/{category}/{name}")
            if challenge_path.exists():
                print(f"❌ Error: Challenge {category}/{name} already exists")
                return False

            self.create_directory_structure(challenge_path, deploy_type, connection_type)

            # 建立配置檔案 (創建 private.yml，後續由它生成 public.yml)
            private_config = self.create_private_config(
                name, category, difficulty, author, deploy_type, connection_type
            )
            self.save_private_config(challenge_path, private_config)

            # 生成 public.yml (從 private.yml 移除敏感資訊)
            public_config = self.generate_public_from_private(private_config)
            self.save_public_config(challenge_path, public_config)

            # 建立模板檔案
            self.create_template_files(challenge_path, private_config, deploy_type, connection_type)

            # Git 操作
            self.create_git_branch(category, name)

            print(f"✅ Challenge created at: {challenge_path}")
            self.print_next_steps(challenge_path, deploy_type, connection_type)
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
        
    def detect_deploy(self, category):
        """依分類推測 (deploy_type, connection_type)。作者可用 --deploy-type 覆蓋。"""
        if category == 'pwn':
            return ('container', 'nc')       # pwn 多為 nc 服務
        if category == 'web':
            return ('container', 'http')     # web 為 http 服務
        return ('attachment', '')            # reverse/crypto/forensic/misc/osint 多為附件
    
    @staticmethod
    def _is_nc(deploy_type, connection_type):
        return deploy_type == 'container' and (connection_type or '') == 'nc'

    def create_directory_structure(self, base_path, deploy_type, connection_type):
        """建立標準目錄結構"""
        try:
            base_dirs = [
                'src',
                'solution',
                'writeup',
                'files',
                'writeup/screenshots'
            ]

            # nc 服務題多附預編 binary → 加 bin/
            if self._is_nc(deploy_type, connection_type):
                base_dirs.extend([
                    'bin',
                    'docker'
                ])
            elif deploy_type == 'container':
                base_dirs.append('docker')
            # attachment / none 不需要 docker/
            
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
            
    def create_private_config(self, name, category, difficulty, author, deploy_type, connection_type):
        """建立 private.yml 配置（含敏感 flag）。新 canonical schema，見 docs/challenge-schema.md。"""
        flag_prefix = self.config['project']['flag_prefix']

        deploy_info = {'requires_build': deploy_type == 'container'}
        if deploy_type == 'container':
            if self._is_nc(deploy_type, connection_type):
                deploy_info.update({'connection_type': 'nc', 'nc_port': 9999, 'timeout': 60})
            else:
                deploy_info.update({'connection_type': connection_type or 'http', 'port': 8080})

        config = {
            'title': name.replace('_', ' ').replace('-', ' ').title(),
            'author': author,
            'difficulty': difficulty,
            'category': category,
            'description': 'TODO: Add challenge description here',
            'deploy_type': deploy_type,          # attachment | container | none
            'source_code_provided': False,
            'files': [],
            'status': 'planning',
            'points': self.config['points'].get(difficulty, 100),
            'tags': [category],
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'hints': [
                {'level': 1, 'cost': 0, 'content': 'TODO: 第一個免費提示 - 引導參賽者思考方向'},
            ],
            # ---- 敏感（僅 private.yml）----
            'flag': f'{flag_prefix}{{TODO_replace_with_actual_flag}}',
            'flag_load': 'static',     # static | dynamic
            'flag_scope': 'shared',    # shared | per_team
            'flag_match': 'exact',     # exact | regex
            'internal_notes': 'TODO: 內部開發筆記、測試要點。解題文件請寫 writeup/README.md',
        }
        if deploy_info:
            config['deploy_info'] = deploy_info
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
        
        # 移除敏感資訊（flag 三軸 + 內部筆記；hints/deploy_info 屬公開）
        sensitive_fields = [
            'flag', 'flag_load', 'flag_scope', 'flag_match', 'dynamic_flag',
            'internal_notes', 'testing',
            'flag_description', 'solution_steps',  # 舊欄位若殘留一併移除
        ]
        for field in sensitive_fields:
            public_config.pop(field, None)

        return public_config
        
    def save_public_config(self, challenge_path, config):
        """儲存 public.yml"""
        try:
            config_file = challenge_path / 'public.yml'
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"📝 Created: {config_file}")
        except IOError as e:
            print(f"❌ Failed to save public.yml: {e}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ YAML formatting error: {e}")
            raise
            
    def create_template_files(self, challenge_path, config, deploy_type, connection_type):
        """建立模板檔案"""
        is_nc = self._is_nc(deploy_type, connection_type)

        # README.md
        readme_content = self.generate_readme_template(config, deploy_type, connection_type)
        with open(challenge_path / 'README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)

        # Docker files（只有 container 類才產；attachment/none 不需要）
        if is_nc:
            self.create_nc_docker_files(challenge_path, config)
        elif deploy_type == 'container':
            self.create_web_docker_files(challenge_path, config)

        # Writeup template
        writeup_content = self.generate_writeup_template(config)
        with open(challenge_path / 'writeup/README.md', 'w', encoding='utf-8') as f:
            f.write(writeup_content)

        # 官方解 stub + 相依宣告（verify-solution 讀 solution/exploit.py）
        self.create_solution_template(challenge_path)

        # nc 題目特定檔案（範例 C + 腳本）
        if is_nc:
            self.create_nc_challenge_files(challenge_path, config)

    def create_solution_template(self, challenge_path):
        """建立 solution/exploit.py 契約 stub 與 requirements.txt 範本。

        exploit.py 契約見 scripts/verify-solution.py；相依寫在 requirements.txt，
        verify-solution 會用 uv 在隔離環境安裝，不污染專案 venv。
        """
        exploit_stub = '''#!/usr/bin/env python3
"""官方解 / exploit。

契約（見 scripts/verify-solution.py）：
- 接 --connection-info "nc <host> <port>"，也吃 HOST / PORT 環境變數
- 解出後把 flag **印在 stdout 最後一行**，交給 verify-solution 比對（不要自己比）
- 尚未實作時 exit 4（NOT_IMPLEMENTED），讓報表區分「沒寫」與「壞了」

第三方相依請寫在同目錄的 requirements.txt。
"""
import argparse
import os
import sys


def target() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection-info")
    args, _ = parser.parse_known_args()
    if args.connection_info:
        return args.connection_info
    return f"{os.getenv('HOST', 'localhost')}:{os.getenv('PORT', '8080')}"


def main() -> int:
    conn = target()
    # TODO: 在這裡實作解題，取得 flag
    # flag = ...
    # print(flag)   # flag 必須是 stdout 最後一行
    # return 0
    print(f"[!] exploit 尚未實作（target={conn}）", file=sys.stderr)
    return 4  # NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
'''
        exploit_path = challenge_path / 'solution' / 'exploit.py'
        with open(exploit_path, 'w', encoding='utf-8') as f:
            f.write(exploit_stub)
        try:
            exploit_path.chmod(0o755)
        except OSError:
            pass

        requirements_stub = (
            "# 解題腳本的第三方相依（一行一個）。\n"
            "# verify-solution 會用 uv 在隔離環境安裝，不會污染專案 venv。\n"
            "# 範例：\n"
            "# requests\n"
            "# pwntools\n"
        )
        with open(challenge_path / 'solution' / 'requirements.txt', 'w', encoding='utf-8') as f:
            f.write(requirements_stub)
            
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
            
    def generate_readme_template(self, config, deploy_type, connection_type):
        """生成 README 模板"""
        flag_prefix = self.config['project']['flag_prefix']
        is_nc = self._is_nc(deploy_type, connection_type)

        # 動態渲染提示（數量不固定）
        hints_md_lines = []
        for h in config.get('hints', []):
            cost = h.get('cost', 0)
            label = "免費" if not cost else f"消耗 {cost} 分"
            hints_md_lines.append(f"### 提示 {h.get('level', '?')}（{label}）\n{h.get('content', '')}")
        hints_md = "\n\n".join(hints_md_lines) or "（尚未撰寫提示）"

        # 根據交付方式調整內容
        if is_nc:
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
        elif deploy_type == 'container':
            connection_info = """
## 連線資訊
- **本地**: http://localhost:8080（正式站 port 由平台/frp 配發）
"""
            quick_start = """
## 🏃‍♂️ 快速開始

### 本地測試
```bash
cd docker/
docker-compose up -d
```
"""
        else:
            connection_info = "\n## 連線資訊\n- 附件題：檔案放 `files/`，無需連線\n"
            quick_start = "\n## 🏃‍♂️ 快速開始\n\n把提供給選手的檔案放到 `files/`。\n"
        
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

## 交付方式
- **deploy_type**: `{config['deploy_type']}`（attachment=只給檔案 / container=有服務 / none=純知識）
- **連線方式**: `{(config.get('deploy_info') or {}).get('connection_type', '—')}`（nc / http / https）

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

{hints_md}

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
    
    def print_next_steps(self, challenge_path, deploy_type, connection_type):
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

        if self._is_nc(deploy_type, connection_type):
            print(f"     → 編譯：cd {challenge_path}/src && make")
            print(f"     → 複製執行檔到 {challenge_path}/docker/bin/")
            print(f"     → 測試：cd {challenge_path}/docker && docker-compose up")
            print(f"     → 連線測試：nc localhost 9999")
        elif deploy_type == 'container':
            print(f"     → 如需 Docker：編輯 {challenge_path}/docker/")
            print(f"     → 測試：cd {challenge_path}/docker && docker-compose up")
        else:
            print(f"     → 附件放在 {challenge_path}/files/")

        print()
        print(f"  4. 驗證")
        print(f"     make validate ARGS=\"{challenge_path}\"")
        print(f"     make scan")
        print()
        print(f"  5. 提交 PR — 由團隊成員 review（拉 branch 解題、確認 flag 後 approve）")
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
                           help='Challenge category（自由填寫；建議 web/pwn/reverse/crypto/forensic/misc/osint/general）')
        parser.add_argument('name', help='Challenge name (use underscore for spaces)')
        parser.add_argument('difficulty',
                           choices=cs.DIFFICULTIES,
                           help='Challenge difficulty')
        parser.add_argument('--author', default='',
                           help='出題人（未填則使用 git user.name，再退回 config.yml team.default_author）')
        parser.add_argument('--deploy-type', dest='deploy_type',
                           choices=['attachment', 'container', 'none'],
                           help='交付方式（未指定則依分類自動推測）')
        parser.add_argument('--connection-type', dest='connection_type',
                           choices=['nc', 'http', 'https'],
                           help='container 題的連線方式（預設 pwn=nc / web=http）')
        parser.add_argument('--config', default='config.yml', help='Config file path')

        args = parser.parse_args()
        
        # 檢查配置檔案
        if not os.path.exists(args.config):
            print(f"⚠️  Config file {args.config} not found, using default settings")
        
        creator = ChallengeCreator(args.config)
        success = creator.create_challenge(
            args.category, args.name, args.difficulty, args.author,
            args.deploy_type, args.connection_type
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