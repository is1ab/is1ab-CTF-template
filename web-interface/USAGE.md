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

## 📝 建題與驗題（與 CLI 雙管道）

- **與命令列等價**：專案根目錄的 `uv run python scripts/create-challenge.py ...` 與本介面的「**創建挑戰**」**擇一即可**，都會建立 `challenges/<類別>/<名稱>/` 及 `public.yml` / `private.yml`。
- **事前設定**：在專案根目錄 `config.yml` 填寫 `team.default_author`（出題人預設值）、`team.reviewers`（驗題人建議清單），並依比賽計畫設定 `challenge_quota`（各類型／難度題目**數量**）。
- **新專案起手式**：建議先到導航列「**初始化**」頁（`/setup`）一次填完：題目配額、出題人/驗題人、舉辦時間與死線，再開始建題。
- **建題頁**（「創建挑戰」）：需填**出題人**、**驗題人**、類別、難度、題目類型等；分數可隨難度自動帶入。
- **驗題頁**（導航列「**驗題**」）：對 `validation_status` 非 `approved` 的題目執行通過／退回；紀錄寫入 `private.yml` 的 `internal_validation_notes`。
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
