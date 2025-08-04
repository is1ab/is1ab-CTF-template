# IS1AB CTF 模板完整建立教學

## 🎯 概述
本教學將引導您正確使用 IS1AB CTF 模板建立完整的三階段 CTF 開發環境。

## 📋 前置需求
- Git 和 GitHub 帳號
- Python 3.8+ 和 uv 套件管理器
- Docker 和 Docker Compose
- 基本的命令列操作知識

## 🏗️ 三階段建立流程

### 階段 1：Template（模板階段）

#### 1.1 Fork 官方模板
```bash
# 在 GitHub 上 Fork https://github.com/is1ab/is1ab-CTF-template
# 或直接下載
git clone https://github.com/is1ab/is1ab-CTF-template.git
cd is1ab-CTF-template
```

#### 1.2 切換到 main 分支
```bash
git checkout main
```

### 階段 2：Private Repository（私有開發階段）

#### 2.1 創建私有 Repository
```bash
# 在 GitHub 上創建新的私有 repository
# 命名格式：{year}-{org-name}-CTF-private
# 例如：2024-is1ab-CTF-private
```

#### 2.2 推送模板到私有 Repository
```bash
git remote set-url origin https://github.com/your-org/2024-is1ab-CTF-private.git
git push -u origin main
```

#### 2.3 環境設置
```bash
# 安裝 Python 環境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安裝依賴
uv sync
```

#### 2.4 初始化專案配置
```bash
# 初始化專案資訊
uv run scripts/init-project.py --year 2024 --org your-org-name

# 編輯 config.yml 設定檔
```

#### 2.5 設定 config.yml
```yaml
project:
  name: "2024-is1ab-CTF"
  year: 2024
  organization: "is1ab"

platform:
  gzctf_url: "http://your-server:8080/"
  ctfd_url: "http://your-server/"
  zipline_url: "http://your-server:3000"

deployment:
  host: "your-server-ip"
  port_range: "8000-9000"
  docker_registry: "your-registry.com"

security:
  flag_prefix: "is1abCTF"
  public_repo: "your-org/2024-is1ab-CTF-public"  # 將建立的公開 repo
```

#### 2.6 創建 public.yml 文件（重要！）
```bash
# 創建 public.yml 來追蹤公開發布的題目
touch public.yml
```

在 `public.yml` 中加入以下內容：
```yaml
# 公開發布的題目追蹤
# 格式：category/challenge_name: status
published_challenges:
  # web/welcome: "published"
  # crypto/rsa_basic: "draft"
  # pwn/buffer_overflow: "planned"

# 發布統計
statistics:
  total_challenges: 0
  published_challenges: 0
  draft_challenges: 0
  planned_challenges: 0

# 最後更新時間
last_updated: "2024-01-01T00:00:00Z"

# 發布配置
release_config:
  auto_sync: true
  sync_on_merge: true
  exclude_patterns:
    - "*/solution/*"
    - "*/flag.txt"
    - "*/private_notes.md"
```

### 階段 3：Public Repository（公開發布階段）

#### 3.1 創建公開 Repository
```bash
# 在 GitHub 上創建新的公開 repository
# 命名格式：{year}-{org-name}-CTF-public
# 例如：2024-is1ab-CTF-public
```

#### 3.2 設置自動同步
確保 `.github/workflows/sync-to-public.yml` 存在並正確配置：

```yaml
name: Sync to Public Repository

on:
  push:
    branches: [ main ]
    paths:
      - 'public.yml'
      - 'challenges/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install uv
        run: pip install uv
        
      - name: Install dependencies
        run: uv sync
        
      - name: Run sync script
        run: uv run scripts/sync-to-public.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PUBLIC_REPO: ${{ secrets.PUBLIC_REPO }}
```

## 🎮 開始開發題目

### 創建第一個題目
```bash
# 使用命令列創建題目
uv run scripts/create-challenge.py web welcome baby --author YourName

# 或使用 Web 介面
cd web-interface
uv run python server.py
# 訪問 http://localhost:8000
```

### 更新進度追蹤
```bash
# 手動更新 README（基於 public.yml）
uv run scripts/update-readme.py

# 驗證題目結構
uv run scripts/validate-challenge.py challenges/web/welcome/
```

### 發布到公開 Repository
```bash
# 編輯 public.yml，將題目標記為可發布
# 然後執行同步
uv run scripts/sync-to-public.py
```

## 📁 正確的目錄結構

建立完成後，您應該有以下結構：

```
私有 Repository (2024-is1ab-CTF-private):
├── challenges/           # 所有題目（包含解答）
├── solutions/           # 詳細解題過程
├── internal-docs/       # 內部文件
├── config.yml          # 完整配置
├── public.yml          # 公開追蹤文件 ⭐
└── scripts/            # 管理腳本

公開 Repository (2024-is1ab-CTF-public):
├── challenges/         # 僅公開的題目（不含解答）
├── README.md          # 自動生成的說明
└── public-info/       # 公開資訊
```

## 🔧 重要修正項目

### 1. public.yml 文件缺失
**問題**：文檔提到基於 `public.yml` 自動追蹤，但該文件不存在  
**解決**：按照上述步驟創建 `public.yml` 文件

### 2. 同步腳本改進
確保 `scripts/sync-to-public.py` 能正確讀取 `public.yml`：

```python
# scripts/sync-to-public.py 應包含
import yaml

def load_public_config():
    with open('public.yml', 'r') as f:
        return yaml.safe_load(f)

def update_readme_progress():
    config = load_public_config()
    # 基於 config 更新 README 進度
    pass
```

### 3. GitHub Actions 配置
確保 `.github/workflows/update-progress.yml` 正確觸發：

```yaml
name: Update Progress
on:
  push:
    paths:
      - 'public.yml'
      - 'challenges/**'
```

## 🚀 完整工作流程

1. **開發階段**：在私有 repository 開發題目
2. **測試階段**：使用 validation 腳本檢查題目
3. **標記階段**：在 `public.yml` 中標記可發布的題目  
4. **發布階段**：自動同步到公開 repository
5. **追蹤階段**：基於 `public.yml` 自動更新 README 進度

## 📝 最佳實踐

- 總是先在私有 repository 開發和測試
- 定期更新 `public.yml` 來追蹤進度
- 使用 Web 介面進行題目管理
- 確保敏感資料不會同步到公開 repository
- 定期驗證同步流程的正確性

## 🔍 驗證安裝

完成設置後，執行以下命令驗證：

```bash
# 檢查環境
uv run scripts/validate-challenge.py --check-env

# 測試 Web 介面
cd web-interface && uv run python server.py --test

# 驗證同步設定
uv run scripts/sync-to-public.py --dry-run
```

如果所有檢查都通過，您的 CTF 開發環境就已經正確設置完成了！