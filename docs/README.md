# 📚 文檔目錄

> IS1AB CTF Template 完整文檔索引

## 🗺️ 新手路線圖

```
QUICKSTART.md（30 分鐘端到端教學）
    ↓
docs/challenge-types-guide.md（選對題目類型）
    ↓
docs/challenge-development.md（進階開發技巧）
    ↓
docs/security-workflow-guide.md（理解安全架構）
```

> **第一次使用？直接看 [QUICKSTART.md](../QUICKSTART.md)，其他文件以後再讀。**

---

## 🎯 新手入門

### 核心教學

1. **[QUICKSTART.md](../QUICKSTART.md)** ⭐ **必讀** — 30 分鐘從 clone 到 PR
2. **[題目類型選擇指南](challenge-types-guide.md)** — 不知道選什麼類型？看這裡
3. **[public/private YAML 說明](public-private-explained.md)** — 為什麼有兩個設定檔
4. **[常見問題](troubleshooting.md)** — 遇到問題？這裡有答案
5. **[Git 操作速查表](git-workflow-cheatsheet.md)** — CTF 開發需要的 Git 指令

### 進階入門

1. **[5 分鐘快速入門](getting-started.md)** ⭐
   - 完全新手專用
   - 最簡單的步驟說明
   - 5 分鐘內完成第一個題目

2. **[快速開始指南](quick-start-guide.md)**
   - 15 分鐘完整教學
   - 包含 Docker 測試
   - 詳細的步驟說明

3. **[Git 操作完整教學](git-workflow-guide.md)**
   - 從零開始學習 Git
   - 包含建立 repo、fork、push、commit
   - 常見問題解決

---

## 🔒 安全流程

### 核心文檔

1. **[安全流程完整指南](security-workflow-guide.md)** 📖
   - 完整的架構設計
   - 詳細使用說明
   - 最佳實踐和故障排除

2. **[快速參考指南](quick-reference.md)** ⚡
   - 常用命令速查
   - 完整工作流程
   - 安全檢查清單

3. **[Web GUI 整合說明](web-gui-integration.md)** 🌐
   - Web 介面與安全流程整合
   - 使用建議
   - 功能對照表

---

## 📖 其他文檔

### 設置和配置

- **[安裝指南](setup-guide.md)** - 系統需求和初始設置（含 UV 快速安裝）
- **[UV 環境詳細設定](uv-setup-guide.md)** - uv 包管理器完整說明
- **[常見問題 FAQ](faq.md)** ⭐ - 常見問題和解決方案

### 開發指南

- **[CTF 完整工作流程](ctf-challenge-workflow.md)** ⭐ - 從 Template 到 Public Release 的完整流程
- **[題目開發指南](challenge-development.md)** - 題目開發最佳實踐與範例
- **[題目元數據標準](challenge-metadata-standard.md)** - public.yml/private.yml 格式規範

### 部署和發布

- **[部署指南](deployment-guide.md)** - 部署到生產環境
- **[Internal Viewer Spec](viewer-data-spec.md)** - viewer-data 分支規格（只讀題目進度）
- **[Internal Viewer 部署](viewer-deployment.md)** - 內網 Docker/Nginx 部署方式
- **[提示系統指南](hints-system-guide.md)** - 多階段提示系統

### 進階配置

- **[GitHub Secrets 設置](github-secrets-setup.md)** - 配置 GitHub Secrets 與環境變數
- **[分支保護設置](branch-protection-setup.md)** - 設置 Branch Protection Rules
- **[Commit 簽名指南](commit-signing-guide.md)** - 設置 GPG 簽名驗證
- **[安全檢查清單](security-checklist.md)** ⚡ - 12 大類安全配置快速檢查
- **[Private/Public 邊界](private-public-boundaries.md)** - 內容分離與資料保護指南
- **[角色與權限管理](roles-and-permissions.md)** - 團隊角色和權限設置

### 貢獻

- **[貢獻指南](../CONTRIBUTING.md)** - 如何貢獻代碼（根目錄）

---

## 📋 文檔閱讀順序建議

### 場景 A：完全新手

```
1. getting-started.md          ← 5 分鐘快速入門
2. git-workflow-guide.md       ← 學習 Git 操作
3. quick-start-guide.md        ← 完整功能體驗
4. security-workflow-guide.md  ← 深入了解安全流程
```

### 場景 B：有 Git 經驗但沒用過這個系統

```
1. getting-started.md          ← 快速了解系統
2. quick-start-guide.md        ← 完整功能體驗
3. security-workflow-guide.md  ← 深入了解安全流程
4. quick-reference.md          ← 常用命令參考
```

### 場景 C：想要深入了解安全流程

```
1. security-workflow-guide.md  ← 完整安全流程
2. quick-reference.md          ← 快速參考
3. web-gui-integration.md      ← Web GUI 整合
4. git-workflow-guide.md       ← Git 操作細節
```

---

## 🔍 快速查找

### 我想...

| 需求 | 推薦文檔 |
|------|----------|
| 快速開始 | [5 分鐘快速入門](getting-started.md) |
| 學習 Git | [Git 操作完整教學](git-workflow-guide.md) |
| 了解安全流程 | [安全流程完整指南](security-workflow-guide.md) |
| 查找命令 | [快速參考指南](quick-reference.md) |
| 使用 Web GUI | [Web GUI 整合說明](web-gui-integration.md) |
| 創建題目 | [題目開發指南](challenge-development.md) |
| 部署題目 | [部署指南](deployment-guide.md) |
| 解決問題 | [常見問題 FAQ](faq.md) ⭐ |
| 故障排除 | [安全流程指南 - 故障排除](security-workflow-guide.md#故障排除) |

---

## 📝 文檔更新記錄

- **2025-01-15**: 新增安全流程完整指南
- **2025-01-15**: 新增 Git 操作教學
- **2025-01-15**: 新增 5 分鐘快速入門
- **2025-01-15**: 更新快速開始指南以符合新安全流程

---

## 💡 文檔改進建議

如果您發現文檔有任何問題或改進建議，歡迎：

- 📝 提交 [Pull Request](https://github.com/is1ab/is1ab-CTF-template/pulls)
- 🐛 回報 [Issue](https://github.com/is1ab/is1ab-CTF-template/issues)
- 💬 參與 [討論](https://github.com/is1ab/is1ab-CTF-template/discussions)

---

**最後更新**：2025-01-15  
**維護者**：IS1AB Team

