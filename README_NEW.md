# IS1AB CTF Template 🚀

一個現代化的 CTF (Capture The Flag) 競賽管理模板，專為 IS1AB 團隊設計。

## 📋 專案概述

這個專案提供了完整的 CTF 競賽管理解決方案，包含題目創建、管理、部署和評分系統。

## 🏗️ 專案結構

```
is1ab-CTF-template/
├── web-interface/          # 主要的 Web 管理介面
│   ├── app.py             # Flask 應用程式
│   ├── templates/         # Jinja2 模板
│   ├── static/           # 靜態資源 (CSS, JS)
│   └── pyproject.toml    # Python 專案配置
├── challenges/           # CTF 題目目錄
├── docs/                # 專案文檔
├── scripts/             # 輔助腳本
├── challenge-templates/ # 題目創建模板
├── config.yml          # 主要配置檔案
└── archive/            # 舊版本檔案封存
```

## 🚀 快速開始

### 1. 環境準備

確保已安裝 Python 3.8+ 和 uv：

```bash
# 安裝 uv (如果尚未安裝)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 啟動 Web 介面

```bash
cd web-interface
uv sync
uv run python app.py
```

### 3. 訪問系統

打開瀏覽器訪問：http://localhost:8004

## 🎯 主要功能

### ✅ Web 管理介面
- 📊 **儀表板**: 題目統計和進度追蹤
- 📋 **題目矩陣**: 視覺化顯示已出題目和待出題目
- 🔧 **題目管理**: 瀏覽、搜尋、驗證題目
- ➕ **創建題目**: 動態表單協助創建新題目
- ⚙️ **系統設定**: 配置管理

### 🎨 現代化設計
- **Bulma CSS 框架**: 現代響應式設計
- **題目配額系統**: 基於配置的進度追蹤
- **即時狀態顯示**: 已出題目 vs 未出題目
- **直觀操作介面**: 點擊、懸停、動畫效果

### 📱 響應式支援
- 桌面端優化體驗
- 平板裝置適配
- 手機端友善介面

## 📖 詳細文檔

- [安裝指南](docs/setup-guide.md)
- [uv 環境設定](docs/uv-setup-guide.md)
- [完整建立教學](IS1AB%20CTF%20模板完整建立教學.md)
- [開發流程](repo流程.md)

## 🛠️ 技術堆疊

### 後端
- **Flask 3.1.1** - Web 框架
- **PyYAML 6.0.2** - 配置解析
- **Flask-Assets 2.1.0** - 資源管理

### 前端
- **Bulma CSS 0.9.4** - CSS 框架
- **Font Awesome** - 圖標
- **標準 Jinja2** - 模板引擎

### 開發工具
- **uv** - Python 包管理
- **Flask Debug Mode** - 開發除錯

## 📋 配置系統

系統基於 `config.yml` 進行配置：

```yaml
# 題目配額配置
challenge_quota:
  by_category:
    web: 6         # Web 安全題目數量
    pwn: 6         # 二進制題目數量
    crypto: 4      # 密碼學題目數量
    # ...
  
  by_difficulty:
    baby: 8        # 入門題目數量
    easy: 10       # 簡單題目數量
    # ...
```

## 🎉 題目矩陣特色

- **進度追蹤**: 顯示 "已出題/配額總數"
- **視覺區分**: 已出題目 (綠框) vs 未出題目 (虛線黃框)
- **雙重檢視**: 按類別/按難度切換
- **即時更新**: 配額狀態即時計算

## 🤝 開發貢獻

1. Fork 這個專案
2. 創建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個 Pull Request

## 📄 授權

本專案採用 MIT 授權條款 - 查看 [LICENSE](LICENSE) 檔案了解詳情。

## 📞 支援

如有問題或建議，請：
- 開啟 [Issue](../../issues)
- 聯繫 IS1AB 團隊

---

**維護者**: IS1AB Team  
**最後更新**: 2025年8月4日  
**版本**: 2.0.0 (Web Interface)
