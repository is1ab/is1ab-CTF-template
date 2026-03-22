# 🚀 CTF Template 設置指南

## 📋 系統需求

### 必要軟體
- **Git**: 版本控制
- **Python 3.9+**: 執行自動化腳本
- **Docker**: 容器化部署
- **Node.js** (可選): Web 介面開發

### 推薦環境
- **作業系統**: Linux/macOS/WSL2
- **記憶體**: 4GB+ RAM
- **硬碟**: 10GB+ 可用空間

## 🔧 初始設置

### 1. 克隆模板

```bash
# 使用 GitHub Template
# 點擊 "Use this template" 按鈕創建新 repository

# 或者直接克隆
git clone https://github.com/your-org/is1ab-CTF-template.git 2024-is1ab-CTF
cd 2024-is1ab-CTF
```

### 2. 安裝依賴

```bash
# 安裝 uv (推薦的 Python 包管理工具)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/macOS
# 或 powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 創建虛擬環境並安裝依賴
uv venv
uv sync

# 或傳統方式 (仍然支援)
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 3. 配置專案

```bash
# 複製配置檔案模板
cp config.yml.example config.yml

# 編輯配置檔案
nano config.yml
```

配置重要選項：
```yaml
project:
  name: "2024-is1ab-CTF"  # 修改為你的專案名稱
  year: 2024
  flag_prefix: "is1abCTF"

platform:
  gzctf_url: "你的GZCTF網址"
  ctfd_url: "你的CTFd網址"
  
deployment:
  host: "你的部署主機IP"
  docker_registry: "你的Docker Registry"
```

### 4. 初始化專案

```bash
# 執行初始化腳本
uv run scripts/init-project.py --year 2024

# 創建基本目錄結構
mkdir -p challenges/{web,pwn,reverse,crypto,forensic,misc,general}
```

## 🔐 GitHub 設置

### 1. Repository 設置

1. **設置為 Private**: Settings → General → Repository visibility
2. **保護主分支**: Settings → Branches → Add protection rule
   - Branch name pattern: `main`
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging

### 2. Secrets 配置

Settings → Secrets and variables → Actions → New repository secret

```bash
# 必要的 Secrets
PUBLIC_REPO_TOKEN=ghp_xxxxxxxxxxxxxxx  # 用於同步公開倉庫
PUBLIC_REPO=your-org/2024-is1ab-CTF-public
DOCKER_REGISTRY=registry.example.com
DOCKER_USERNAME=your-username
DOCKER_PASSWORD=your-password
DEPLOY_HOST=your-deploy-host
DEPLOY_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### 3. 協作者設置

Settings → Manage access → Invite collaborators
- 添加團隊成員
- 設置適當的權限 (Write/Admin)

## 🎯 第一個題目

### 創建測試題目

```bash
# 創建一個簡單的 Web 題目
uv run scripts/create-challenge.py web welcome baby --author YourName

# 檢查生成的檔案
ls -la challenges/web/welcome/
```

### 編輯題目內容

```bash
# 編輯題目配置
nano challenges/web/welcome/public.yml

# 編輯題目描述  
nano challenges/web/welcome/README.md

# 開發題目源碼
nano challenges/web/welcome/src/app.py
```

### 測試和提交

```bash
# 驗證題目格式
uv run scripts/validate-challenge.py challenges/web/welcome/

# 提交 PR
git add challenges/web/welcome/
git commit -m "feat(web): add welcome challenge"
git push origin challenge/web/welcome
```

## 🐳 Docker 設置

### 安裝 Docker

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker

# macOS
brew install --cask docker

# 驗證安裝
docker --version
docker-compose --version
```

### 測試容器建構

```bash
# 測試 Docker 建構
cd challenges/web/welcome/docker/
docker-compose up -d

# 檢查容器狀態
docker-compose ps

# 查看日誌
docker-compose logs

# 清理
docker-compose down
```

## 🌐 Web 介面設置

### 啟動本地 Web 介面

```bash
# 進入 web 介面目錄
cd web-interface/

# 啟動 Python Web 服務器
uv run web-interface/server.py --host localhost --port 8000

# 或啟動簡單 HTTP 伺服器
uv run python -m http.server 8000

# 或使用 Node.js
npx serve .
```

訪問: http://localhost:8000

### 設置 API 端點 (進階)

如果需要完整的 API 功能：

```bash
# 安裝 Flask (如果尚未安裝)
uv pip install flask flask-cors

# 啟動 API 伺服器
uv run api/server.py
```

## 🔍 驗證設置

### 執行完整測試

```bash
# 驗證所有腳本
uv run scripts/validate-challenge.py --all

# 更新 README
uv run scripts/update-readme.py

# 檢查生成的檔案
cat README.md
cat progress.json
```

### 檢查 GitHub Actions

1. 推送到 GitHub 觸發 Actions
2. 查看 Actions 頁面確認運行狀態
3. 檢查自動更新的 README

## ⚡ 快速命令參考

```bash
# 常用操作
uv run scripts/create-challenge.py <category> <name> <difficulty>
uv run scripts/validate-challenge.py <path>
uv run scripts/update-readme.py
git checkout -b challenge/<category>/<name>

# Docker 操作
docker-compose up -d
docker-compose logs -f
docker-compose down

# 專案管理
uv run scripts/sync-to-public.py
```

## 🐛 常見問題

### Q: Python 依賴安裝失敗
```bash
# 使用 uv (推薦)
uv pip install -r requirements.txt

# 使用鏡像源 (如果需要)
uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# 傳統方式
pip install --upgrade pip
pip cache purge
pip install -r requirements.txt
```

### Q: Docker 權限錯誤
```bash
# 添加用戶到 docker 組
sudo usermod -aG docker $USER
newgrp docker

# 或使用 sudo
sudo docker-compose up -d
```

### Q: GitHub Actions 失敗
1. 檢查 Secrets 是否正確設置
2. 查看 Actions 日誌詳細錯誤
3. 確認分支保護規則設置

### Q: 題目驗證失敗
```bash
# 檢查詳細錯誤
uv run scripts/validate-challenge.py challenges/web/example/ --verbose

# 檢查檔案權限
chmod +x scripts/*.py
```

---

# 🤝 貢獻指南

> 詳細的貢獻指南請參閱 [CONTRIBUTING.md](../CONTRIBUTING.md)

## 📋 概述

歡迎為 IS1AB CTF 專案貢獻！本指南將幫助你了解如何參與開發。

## 🎯 貢獻方式

### 1. 題目開發
- 創建新的 CTF 題目
- 改進現有題目
- 修復題目問題

### 2. 工具改進
- 改進自動化腳本
- 優化 Docker 配置
- 增強 Web 介面

### 3. 文檔完善
- 更新使用指南
- 添加範例
- 翻譯內容

## 🔄 工作流程

### 1. 準備工作

```bash
# Fork 專案到你的 GitHub 帳號
# 克隆你的 Fork
git clone https://github.com/YOUR-USERNAME/is1ab-CTF-template.git
cd is1ab-CTF-template

# 添加上游倉庫
git remote add upstream https://github.com/ORIGINAL-OWNER/is1ab-CTF-template.git

# 獲取最新代碼
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. 創建分支

```bash
# 題目開發
git checkout -b challenge/category/challenge-name

# 功能開發
git checkout -b feature/feature-name

# 錯誤修復
git checkout -b fix/issue-description
```

### 3. 開發過程

#### 題目開發流程

```bash
# 使用腳本創建題目
uv run scripts/create-challenge.py web example easy

# 開發題目內容
# 1. 編輯 public.yml
# 2. 開發源碼
# 3. 編寫 Writeup
# 4. 準備檔案

# 本地測試
uv run scripts/validate-challenge.py challenges/web/example/
cd challenges/web/example/docker/
docker-compose up -d
# 測試題目功能
docker-compose down
```

#### 程式碼開發流程

```bash
# 修改代碼
nano scripts/your-script.py

# 測試修改
uv run scripts/your-script.py

# 執行單元測試 (如果有)
uv run python -m pytest tests/
```

### 4. 提交代碼

#### Commit 訊息規範

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```bash
# 格式
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Type 類型**:
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔更新
- `style`: 程式碼格式 (不影響功能)
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 建構過程或輔助工具變動

**Scope 範圍**:
- `web`, `pwn`, `crypto` 等: 題目分類
- `scripts`: 自動化腳本
- `docker`: Docker 相關
- `docs`: 文檔
- `ci`: CI/CD

**範例**:
```bash
feat(web): add SQL injection challenge
fix(scripts): resolve validation error in create-challenge.py
docs: update setup guide with Docker instructions
style(web): format challenge source code
refactor(scripts): improve error handling
test: add unit tests for validation script
chore(ci): update GitHub Actions workflow
```

### 5. 提交 Pull Request

```bash
# 推送分支
git push origin your-branch-name
```

在 GitHub 上創建 Pull Request：

1. 填寫 PR 模板
2. 選擇適當的標籤
3. 請求程式碼審查
4. 關聯相關 Issue

## ✅ 程式碼審查

### 審查清單

#### 題目審查
- [ ] 題目概念明確有趣
- [ ] 難度分級合適
- [ ] 學習目標清楚
- [ ] 解題路徑唯一且合理
- [ ] Flag 格式正確
- [ ] Docker 配置安全
- [ ] 文檔完整

#### 程式碼審查
- [ ] 程式碼風格一致
- [ ] 錯誤處理完善
- [ ] 性能考量合理
- [ ] 安全性檢查通過
- [ ] 測試覆蓋充分
- [ ] 文檔同步更新

### 審查流程

1. **自動檢查**: GitHub Actions 自動驗證
2. **同行審查**: 至少一位團隊成員審查
3. **測試驗證**: 確保功能正常
4. **安全檢查**: 檢查敏感資料洩露
5. **最終確認**: 主要維護者批准

## 📝 程式碼風格

### Python 風格

```python
# 使用 PEP 8 風格
# 函數名使用 snake_case
def create_challenge():
    pass

# 類名使用 PascalCase  
class ChallengeCreator:
    pass

# 常數使用 UPPER_CASE
FLAG_PREFIX = "is1abCTF"

# 使用 docstring
def validate_challenge(path):
    """
    驗證題目格式和內容
    
    Args:
        path (str): 題目路徑
        
    Returns:
        bool: 驗證是否通過
    """
    pass
```

### YAML 風格

```yaml
# 使用 2 空格縮排
title: "Challenge Title"
author: "YourName"
difficulty: "middle"

# 列表格式
tags:
  - web
  - sql-injection
  - beginner

# 長字串使用 | 或 >
description: |
  這是一個多行的
  題目描述內容
```

### Docker 風格

```dockerfile
# 使用官方基礎映像
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 複製需求檔案
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 設置權限
RUN chmod +x *.sh

# 暴露端口
EXPOSE 80

# 啟動命令
CMD ["python", "app.py"]
```

## 🧪 測試指南

### 題目測試

```bash
# 結構驗證
uv run scripts/validate-challenge.py challenges/web/example/

# Docker 測試
cd challenges/web/example/docker/
docker-compose up -d
curl http://localhost:8080
docker-compose down

# 解題測試
# 按照 writeup 步驟驗證解題流程
```

### 腳本測試

```bash
# 單元測試
uv run python -m pytest tests/test_create_challenge.py

# 整合測試
uv run scripts/update-readme.py --dry-run
uv run scripts/validate-challenge.py --all
```

## 🐛 問題回報

### 回報錯誤

使用 [Bug Report Template](../.github/ISSUE_TEMPLATE/bug-report.md):

1. 清楚描述問題
2. 提供重現步驟
3. 包含錯誤訊息
4. 說明環境資訊

### 功能建議

使用 [Feature Request Template](../.github/ISSUE_TEMPLATE/feature-request.md):

1. 描述需求背景
2. 提出解決方案
3. 考慮替代方案
4. 評估實作複雜度

## 🎖️ 貢獻者認可

### Hall of Fame

我們會在以下地方認可貢獻者：

- README.md 貢獻者列表
- 每月貢獻者摘要
- 特殊貢獻者徽章

### 貢獻統計

- 題目貢獻數量
- 程式碼提交次數
- 文檔改進記錄
- 問題解決數量

## 📞 尋求幫助

### 獲得協助

- **GitHub Discussions**: 一般討論和問題
- **GitHub Issues**: 特定問題回報
- **Slack**: 即時溝通 (如果有)
- **Email**: 私人聯絡

### 指導機制

- **Buddy System**: 新貢獻者配對資深成員
- **Code Review**: 詳細的代碼審查回饋
- **Documentation**: 完整的開發文檔

## 📚 學習資源

### CTF 相關
- [CTF Wiki](https://ctf-wiki.org/)
- [PicoCTF](https://picoctf.org/)
- [OverTheWire](https://overthewire.org/)

### 開發工具
- [Git 教學](https://git-scm.com/book)
- [Docker 文檔](https://docs.docker.com/)
- [Python 風格指南](https://pep8.org/)

---

感謝你的貢獻！每一個改進都讓這個專案變得更好！ 🚀

---

## 📦 UV 環境設置

本專案統一使用 [uv](https://docs.astral.sh/uv/) 作為 Python 包管理工具。詳細的 UV 安裝與設定說明請參閱 [UV Setup Guide](uv-setup-guide.md)。

### 快速安裝

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝專案依賴
uv sync

# 安裝開發依賴
uv sync --extra dev

# 執行測試
uv run pytest tests/ -v
```