# is1ab-CTF-template

🚀 **IS1AB CTF 比賽專案模板** - 快速建立標準化 CTF 比賽環境

## 📋 關於此模板

此模板提供完整的 CTF 題目管理解決方案，包含：
- 標準化的題目開發流程
- 自動化進度追蹤
- Docker 部署配置
- 協作工具和腳本

## 🎯 快速開始

### ⚡ 5 分鐘快速體驗

想要立即開始？請參考 [**快速開始指南**](docs/quick-start-guide.md) 在 15 分鐘內創建您的第一個 CTF 題目！

### 📚 完整工作流程

需要了解完整的三階段開發流程？請閱讀 [**工作流程教學**](docs/workflow-tutorial.md)。

### 🚀 基本步驟

```bash
# 1. 克隆模板
git clone https://github.com/is1ab/is1ab-CTF-template.git my-ctf-2024
cd my-ctf-2024

# 2. 安裝依賴
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# 3. 初始化專案
uv run scripts/init-project.py --year 2024 --org your-org

# 4. 創建第一個題目
uv run scripts/create-challenge.py web welcome baby --author YourName

# 5. 啟動 Web 管理介面
cd web-interface && python server.py
```

**🎉 完成！** 訪問 http://localhost:8000 查看您的 CTF 管理介面。

## 📁 專案結構

```
is1ab-CTF-template/
├── 📁 .github/                    # GitHub 配置
│   ├── 📁 workflows/              # GitHub Actions
│   │   ├── update-progress.yml    # 自動更新進度
│   │   ├── validate-challenge.yml # 題目驗證
│   │   └── deploy-container.yml   # 容器部署
│   ├── 📁 ISSUE_TEMPLATE/         # Issue 模板
│   │   ├── new-challenge.md       # 新題目請求
│   │   └── bug-report.md          # 錯誤回報
│   └── PULL_REQUEST_TEMPLATE.md   # PR 模板
├── 📁 scripts/                    # 自動化腳本
│   ├── create-challenge.py        # 創建新題目
│   ├── update-readme.py          # 更新 README
│   ├── validate-challenge.py     # 驗證題目
│   ├── sync-to-public.py         # 同步到公開倉庫
│   ├── prepare-public-release.py # 準備公開發布
│   ├── check-sensitive.py        # 檢查敏感資料
│   └── init-project.py           # 初始化專案
├── 📁 templates/                  # 文件模板
│   ├── README.md.j2              # README 模板
│   ├── challenge-readme.md       # 題目 README 模板
│   ├── docker-compose.yml        # Docker 模板
│   └── writeup-template.md       # Writeup 模板
├── 📁 docs/                      # 文檔
│   ├── setup-guide.md            # 設置指南
│   ├── contribution-guide.md     # 貢獻指南
│   ├── deployment-guide.md       # 部署指南
│   └── challenge-development.md  # 題目開發指南
├── 📁 web-interface/             # Web 管理介面
│   ├── index.html                # 主頁面
│   ├── create-challenge.html     # 創建題目
│   ├── progress.html             # 進度查看
│   └── api.js                    # API 接口
├── config.yml                    # 專案配置
├── requirements.txt              # Python 依賴 (uv 管理)
└── README.md                     # 說明文檔
```

## 🛠️ 功能特色

### ✨ 自動化工具
- **一鍵創建題目**: 自動生成標準化目錄結構
- **進度自動追蹤**: 基於 `public.yml` 自動更新 README
- **PR 自動驗證**: 檢查題目格式和安全性
- **Docker 自動部署**: 統一的容器化部署流程

### 🔒 隱私保護
- **三階段流程**: Template → Private → Public
- **敏感資料保護**: 自動檢查並防止 Flag 洩露
- **智能同步**: 只發布標記為安全的內容到公開倉庫

### 📊 進度管理
- **視覺化進度表**: 使用表情符號顯示狀態
- **任務分配追蹤**: 清楚的責任分工
- **多格式輸出**: README + JSON + Web 介面

### 🎨 標準化格式
- **統一題目格式**: Author + Difficulty + Category
- **Flag 格式統一**: `is1abCTF{...}`
- **題目類型分類**: 靜態/動態 + 附件/容器

## 📝 使用說明

### 創建新題目

```bash
# 基本用法
uv run scripts/create-challenge.py <category> <name> <difficulty>

# 範例
uv run scripts/create-challenge.py web sql_injection middle
uv run scripts/create-challenge.py pwn buffer_overflow hard
uv run scripts/create-challenge.py crypto rsa_challenge easy
```

### 更新進度

```bash
# 手動更新 README
uv run scripts/update-readme.py

# 驗證題目結構
uv run scripts/validate-challenge.py challenges/web/example/

# 同步到公開倉庫
uv run scripts/sync-to-public.py
```

### Web 介面使用

```bash
# 啟動本地 Web 介面
cd web-interface/
uv run server.py --host localhost --port 8000

# 或使用傳統方式提供靜態檔案
uv run python -m http.server 8000

# 訪問 http://localhost:8000
# 使用 Web 介面創建和管理題目
```

## 🔧 配置說明

### config.yml
```yaml
project:
  name: "2024-is1ab-CTF"
  year: 2024
  organization: "is1ab"

platform:
  gzctf_url: "http://140.124.181.153:8080/"
  ctfd_url: "http://140.124.181.153/"
  zipline_url: "http://140.124.181.153:3000"

deployment:
  host: "140.124.181.153"
  port_range: "8000-9000"
  docker_registry: "your-registry.com"

security:
  flag_prefix: "is1abCTF"
  public_repo: "your-org/2024-is1ab-CTF-public"
```

## 🚀 部署流程

### 1. 開發環境
```bash
# 本地開發
docker-compose -f docker/docker-compose.dev.yml up

# 測試題目
docker build -t challenge-test challenges/web/example/docker/
docker run -p 8080:80 challenge-test
```

### 2. 生產部署
```bash
# 使用 GitHub Actions 自動部署
# 或手動部署
uv run scripts/deploy.py --environment production
```

## 📚 相關文檔

- [⚡ 快速開始指南](docs/quick-start-guide.md) - 15 分鐘快速上手
- [🚀 三階段工作流程教學](docs/workflow-tutorial.md) - 完整開發流程指南
- [📖 設置指南](docs/setup-guide.md) - 詳細的環境設置說明
- [🤝 貢獻指南](docs/contribution-guide.md) - 如何參與開發
- [🐳 部署指南](docs/deployment-guide.md) - Docker 部署說明
- [💡 題目開發](docs/challenge-development.md) - 題目開發最佳實踐

## 🎭 題目類型說明

| 類型 | 說明 | 使用場景 |
|------|------|----------|
| 靜態附件 | 共用附件，固定 flag | 逆向、密碼學、取證 |
| 靜態容器 | 共用容器，固定 flag | Web、簡單 Pwn |
| 動態附件 | 隊伍專屬附件 | 個人化題目 |
| 動態容器 | 獨立容器，唯一 flag | 複雜 Web、Pwn |

## 🏷️ 難度分級

- 🍼 **baby**: 新手友善，10-30 分鐘解決
- ⭐ **easy**: 入門級，30-60 分鐘解決  
- ⭐⭐ **middle**: 中等難度，1-3 小時解決
- ⭐⭐⭐ **hard**: 高難度，3-8 小時解決
- 💀 **impossible**: 極限挑戰，8+ 小時解決

## 🤝 貢獻方式

1. **Fork** 此模板到你的組織
2. **創建分支** 進行題目開發
3. **提交 PR** 並等待審核
4. **合併後** 自動更新進度

## 📞 支援與聯絡

- 🐛 **問題回報**: 使用 [Issues](../../issues)
- 💡 **功能建議**: 使用 [Discussions](../../discussions)  
- 📧 **聯絡我們**: [your-email@example.com]
- 📚 **文檔**: [Wiki](../../wiki)

## 📄 授權條款

MIT License - 詳見 [LICENSE](LICENSE) 檔案

---

**⭐ 如果這個模板對你有幫助，請給我們一個 Star！**

最後更新：2024-XX-XX | 版本：v1.0.0