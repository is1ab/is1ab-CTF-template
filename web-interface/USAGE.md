# Web Interface 使用指南

## 🚀 快速啟動

### 1. 進入 web-interface 目錄

```bash
cd web-interface
```

### 2. 啟動應用

```bash
# 使用 uv（推薦）
uv run python app.py

# 或使用系統 Python（如果已安裝依賴）
python app.py
```

### 3. 訪問應用

打開瀏覽器訪問：<http://localhost:8004>

## 🧙 初始化精靈

第一次使用請先進入 `/setup` 精靈完成 5 步驟設定：

| Step | 路徑 | 內容 |
|------|------|------|
| 1 | `/setup/project` | 競賽名稱、flag prefix、平台 URL |
| 2 | `/setup/team` | 團隊成員（github_username / 顯示名 / 專長） |
| 3 | `/setup/event` | 比賽時程與死線 |
| 4 | `/setup/quota` | 各類別 / 難度的目標題數 |
| 5 | `/setup/finalize` | 產生 `.github/` 模板（PR template / CODEOWNERS / branch-protection 指引），可選清理舊版驗題欄位 |

可隨時回任一步調整（idempotent）。

## ✅ 驗題流程

驗題透過 **GitHub Pull Request review** 進行（不在 Web GUI 中操作）。
PR template 由 `/setup/finalize` 產生於 `.github/PULL_REQUEST_TEMPLATE.md`，含出題人與驗題人雙 checklist。

詳細流程：[docs/authoring-challenges.md](../docs/authoring-challenges.md)。

## 📝 建題（與 CLI 雙管道）

- **與命令列等價**：專案根目錄的 `uv run python scripts/create-challenge.py ...` 與本介面的「**創建挑戰**」**擇一即可**，都會建立 `challenges/<類別>/<名稱>/` 及 `public.yml` / `private.yml`。
- **建題頁**（「創建挑戰」）：需填**出題人**、類別、難度、題目類型等；分數可隨難度自動帶入。
- **完整說明**（雙方式對照、欄位意義）見專案 `docs/authoring-challenges.md`。

## 📁 目錄結構

```
web-interface/
├── app.py              # 主應用程式
├── templates/          # Jinja2 模板
│   ├── base.html      # 基礎模板
│   ├── challenges.html # 挑戰列表
│   ├── challenge_detail.html # 挑戰詳情
│   ├── edit_challenge.html   # 編輯挑戰
│   ├── create_challenge.html # 創建挑戰
│   └── components/    # 組件模板
├── static/            # 靜態資源
│   ├── css/          # 樣式文件
│   └── js/           # JavaScript 文件
├── .venv/            # uv 虛擬環境（自動生成）
├── uv.lock          # uv 鎖定檔案
└── pyproject.toml    # 項目配置
```

## 🔧 開發注意事項

### 1. 路由規範

- 所有模板中使用 `url_for()` 函數生成 URL
- 避免硬編碼路徑
- 路由參數使用 `name` 而非 `n`

### 2. 靜態資源

- CSS 和 JS 文件通過 Flask-Assets 管理
- 開發模式下會自動重新編譯
- 生產環境下使用壓縮版本

### 3. 模板系統

- 使用 Jinja2 模板引擎
- 基礎模板 `base.html` 包含通用佈局
- 組件模板位於 `components/` 目錄

## 🐛 故障排除

### 1. 啟動問題

- 確保已安裝所有依賴：`uv sync`（在 web-interface 目錄）
- 檢查 Python 版本：需要 Python 3.8+
- 如果使用 uv，確保已安裝：`curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. 模板錯誤

- 檢查 `url_for()` 函數參數是否正確
- 確保路由定義與函數參數一致

### 3. 靜態資源問題

- 清理瀏覽器緩存
- 重新啟動應用

## 📖 更多資訊

- 詳細說明請參閱 [README.md](README.md)
- 完整文檔請參閱 [Web GUI 整合說明](../wiki/Web-GUI-Integration.md)
