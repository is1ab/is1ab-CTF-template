# 🚀 UV Setup Guide

此專案使用 [uv](https://docs.astral.sh/uv/) 作為主要的 Python 包管理工具，提供更快速、可靠的依賴管理體驗。

## 📦 關於 UV

UV 是由 Astral 開發的現代 Python 包管理器，具有以下優勢：

- **⚡ 極致速度**: 比 pip 快 10-100 倍
- **🔒 可靠性**: 確定性的依賴解析
- **🛠️ 兼容性**: 完全兼容 pip 和 PyPI
- **🎯 簡潔性**: 統一的工具鏈體驗

## 🔧 安裝 UV

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 使用包管理器

```bash
# macOS (Homebrew)
brew install uv

# Linux (apt)
sudo apt install uv

# 或使用 pip 安裝
pip install uv
```

### 驗證安裝

```bash
uv --version
```

## 🚀 快速開始

### 1. 創建虛擬環境

```bash
# 創建虛擬環境
uv venv

# 啟動虛擬環境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

### 2. 安裝依賴

```bash
# 安裝專案依賴
uv pip install -r requirements.txt

# 或使用 pyproject.toml (推薦)
uv pip install -e .

# 安裝開發依賴
uv pip install -e ".[dev]"

# 安裝所有可選依賴
uv pip install -e ".[dev,web,docker]"
```

### 3. 執行腳本

```bash
# 直接執行腳本 (自動啟用虛擬環境)
uv run scripts/create-challenge.py web example easy

# 或在虛擬環境中執行
python scripts/create-challenge.py web example easy
```

## 📋 常用命令

### 虛擬環境管理

```bash
# 創建虛擬環境
uv venv [name]

# 創建指定 Python 版本的環境
uv venv --python 3.11

# 移除虛擬環境
rm -rf .venv
```

### 包管理

```bash
# 安裝包
uv pip install package-name

# 安裝特定版本
uv pip install "package-name==1.0.0"

# 安裝多個包
uv pip install package1 package2 package3

# 從 requirements.txt 安裝
uv pip install -r requirements.txt

# 卸載包
uv pip uninstall package-name

# 列出已安裝的包
uv pip list

# 顯示包資訊
uv pip show package-name

# 檢查過期包
uv pip list --outdated

# 更新包
uv pip install --upgrade package-name
```

### 執行腳本

```bash
# 在虛擬環境中執行腳本
uv run script.py

# 執行模組
uv run -m module_name

# 執行帶參數的腳本
uv run scripts/create-challenge.py --help
```

### 依賴管理

```bash
# 生成 requirements.txt
uv pip freeze > requirements.txt

# 檢查依賴衝突
uv pip check

# 編譯依賴 (類似 pip-compile)
uv pip compile requirements.in

# 同步依賴 (類似 pip-sync)
uv pip sync requirements.txt
```

## 🔧 專案配置

### pyproject.toml 設置

我們已在專案根目錄配置了 `pyproject.toml`，包含：

```toml
[project]
name = "is1ab-ctf-template"
dependencies = [
    "pyyaml>=6.0",
    "jinja2>=3.0.0",
    "click>=8.0.0",
    # ... 其他依賴
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "black>=22.0.0"]
web = ["flask>=2.0.0", "gunicorn>=20.1.0"]
docker = ["docker>=6.0.0"]
```

### 使用配置

```bash
# 安裝基本依賴
uv pip install -e .

# 安裝開發依賴
uv pip install -e ".[dev]"

# 安裝 Web 功能依賴
uv pip install -e ".[web]"

# 安裝所有依賴
uv pip install -e ".[dev,web,docker]"
```

## 🎯 CTF 專案工作流程

### 初始化新專案

```bash
# 1. 克隆專案
git clone <your-repo> ctf-project
cd ctf-project

# 2. 創建虛擬環境
uv venv

# 3. 啟動虛擬環境
source .venv/bin/activate

# 4. 安裝依賴
uv pip install -e ".[dev,web]"

# 5. 初始化專案
uv run scripts/init-project.py --year 2024
```

### 開發新題目

```bash
# 1. 創建題目
uv run scripts/create-challenge.py web sql_injection middle

# 2. 驗證題目
uv run scripts/validate-challenge.py challenges/web/sql_injection/

# 3. 更新 README
uv run scripts/update-readme.py

# 4. 啟動 Web 介面
uv run web-interface/server.py
```

### 測試和驗證

```bash
# 執行所有驗證
uv run scripts/validate-challenge.py --all

# 檢查敏感資料
uv run scripts/check-sensitive.py

# 運行測試 (如果有)
uv run python -m pytest

# 格式化代碼
uv run black scripts/

# 檢查代碼風格
uv run flake8 scripts/
```

## 🔄 遷移指南

### 從 pip 遷移到 uv

如果你之前使用 pip，遷移很簡單：

```bash
# 1. 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 創建新的虛擬環境
uv venv

# 3. 啟動虛擬環境
source .venv/bin/activate

# 4. 安裝現有依賴
uv pip install -r requirements.txt

# 5. 驗證安裝
uv pip list
```

### 更新現有腳本

將腳本中的 pip 命令替換為 uv：

```bash
# 舊的方式
pip install -r requirements.txt
python scripts/create-challenge.py

# 新的方式
uv pip install -r requirements.txt
uv run scripts/create-challenge.py
```

## 🐛 疑難排解

### 常見問題

#### Q: uv 命令找不到
```bash
# 重新載入 shell 配置
source ~/.bashrc  # 或 ~/.zshrc

# 或重新安裝
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Q: 虛擬環境未啟動
```bash
# 檢查虛擬環境
ls -la .venv/

# 手動啟動
source .venv/bin/activate

# 或使用 uv run 自動處理
uv run python --version
```

#### Q: 依賴安裝失敗
```bash
# 使用詳細輸出
uv pip install -r requirements.txt -v

# 清除快取
uv cache clean

# 使用鏡像源
uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### Q: 與 pip 不兼容
```bash
# uv 完全兼容 pip，可以混用
pip install some-package
uv pip list  # 會顯示 pip 安裝的包

# 但建議統一使用 uv
uv pip install some-package
```

## 📚 進階用法

### Lock 檔案

```bash
# 生成精確版本的依賴檔案
uv pip compile requirements.in --output-file requirements.txt

# 升級所有依賴到最新版本
uv pip compile requirements.in --upgrade

# 同步到精確版本
uv pip sync requirements.txt
```

### 多 Python 版本

```bash
# 使用特定 Python 版本
uv venv --python 3.9
uv venv --python 3.11

# 檢查可用的 Python 版本
uv python list
```

### 快取管理

```bash
# 查看快取大小
uv cache size

# 清除快取
uv cache clean

# 查看快取位置
uv cache dir
```

## 🔗 參考資源

- [UV 官方文檔](https://docs.astral.sh/uv/)
- [UV GitHub 倉庫](https://github.com/astral-sh/uv)
- [UV vs pip 性能比較](https://docs.astral.sh/uv/concepts/resolution/)
- [Python 包管理最佳實踐](https://packaging.python.org/guides/)

## 🎉 最佳實踐

1. **總是使用虛擬環境**: `uv venv` 創建乾淨的環境
2. **版本固定**: 在 `requirements.txt` 中固定版本號
3. **定期更新**: 使用 `uv pip list --outdated` 檢查更新
4. **快取利用**: UV 自動快取，加速後續安裝
5. **配置管理**: 使用 `pyproject.toml` 統一管理專案配置

---

🚀 現在你已經準備好使用 UV 來高效管理你的 CTF 專案了！