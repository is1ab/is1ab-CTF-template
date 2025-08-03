# Web Interface 使用指南

## 🚀 快速啟動

### 1. 進入 web-interface 目錄

```bash
cd web-interface
```

### 2. 啟動應用

```bash
# 使用系統 Python（如果已安裝依賴）
python app.py

# 或使用虛擬環境
./venv/bin/python app.py
```

### 3. 訪問應用

打開瀏覽器訪問：<http://localhost:8004>

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
├── venv/             # Python 虛擬環境
├── legacy/           # 舊版本文件
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

- 確保已安裝所有依賴：`pip install flask flask-cors flask-assets pyyaml cssmin jsmin markupsafe`
- 檢查 Python 版本：需要 Python 3.8+

### 2. 模板錯誤

- 檢查 `url_for()` 函數參數是否正確
- 確保路由定義與函數參數一致

### 3. 靜態資源問題

- 清理瀏覽器緩存
- 重新啟動應用

## 📝 開發日誌

### 2025年8月4日

- ✅ 移除所有硬編碼 URL
- ✅ 統一路由參數命名
- ✅ 修復 JavaScript 語法錯誤
- ✅ 清理項目文件結構
