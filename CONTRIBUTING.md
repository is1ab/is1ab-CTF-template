# 🤝 貢獻指南

感謝您對 IS1AB CTF Template 專案的關注！本指南將幫助您了解如何參與貢獻。

## 📋 目錄

- [行為準則](#行為準則)
- [如何貢獻](#如何貢獻)
- [開發環境設置](#開發環境設置)
- [提交規範](#提交規範)
- [Pull Request 流程](#pull-request-流程)
- [Issue 報告](#issue-報告)

---

## 行為準則

本專案遵循 [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md)。參與本專案即表示您同意遵守此行為準則。

---

## 如何貢獻

### 🐛 報告 Bug

發現 Bug？請先檢查 [Issues](https://github.com/is1ab/is1ab-CTF-template/issues) 確認是否已有人報告。

如果沒有，請建立新的 Issue，包含：

- **清晰的標題**：簡要描述問題
- **詳細描述**：問題的具體情況
- **重現步驟**：如何重現這個問題
- **預期行為**：您期望的行為
- **實際行為**：實際發生的行為
- **環境資訊**：作業系統、Python 版本、uv 版本等
- **截圖/日誌**：如果適用

### 💡 提出功能建議

有好的想法？歡迎提出！

請建立 Feature Request Issue，包含：

- **功能描述**：詳細說明您想要的功能
- **使用場景**：這個功能解決什麼問題
- **可能的實現方式**：如果有想法，歡迎分享

### 📝 改進文檔

文檔改進同樣重要！您可以：

- 修正錯別字或語法錯誤
- 補充缺失的說明
- 改進範例和教程
- 翻譯文檔（歡迎！）

### 💻 提交代碼

1. **Fork 本專案**
2. **建立功能分支**：`git checkout -b feature/amazing-feature`
3. **提交變更**：遵循 [提交規範](#提交規範)
4. **推送到分支**：`git push origin feature/amazing-feature`
5. **建立 Pull Request**

---

## 開發環境設置

### 1. Fork 並 Clone

```bash
# Fork 專案後，clone 您的 fork
git clone https://github.com/YOUR-USERNAME/is1ab-CTF-template.git
cd is1ab-CTF-template
```

### 2. 設置開發環境

```bash
# 安裝 uv（如果尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝依賴
uv sync

# 驗證安裝
uv run python scripts/create-challenge.py --help
```

### 3. 建立開發分支

```bash
# 從 main 分支建立新分支
git checkout -b feature/your-feature-name

# 或修復 bug
git checkout -b fix/bug-description
```

---

## 提交規範

我們使用 [Conventional Commits](https://www.conventionalcommits.org/) 規範：

### 提交類型

- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔變更
- `style`: 代碼格式（不影響功能）
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 構建過程或輔助工具的變動
- `perf`: 性能優化
- `ci`: CI 配置變更

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 範例

```bash
# 新功能
git commit -m "feat(scripts): add flag validation to validate-challenge.py"

# Bug 修復
git commit -m "fix(web): resolve template rendering issue"

# 文檔改進
git commit -m "docs(readme): add quick start guide"

# 多行提交訊息
git commit -m "feat(security): enhance flag detection

- Add regex patterns for common flag formats
- Check all public files recursively
- Add severity levels (CRITICAL, HIGH, MEDIUM)
- Improve error messages with line numbers"
```

---

## Pull Request 流程

### 1. 準備 PR

在提交 PR 前，請確保：

- [ ] 代碼遵循專案風格
- [ ] 已添加必要的測試
- [ ] 已更新相關文檔
- [ ] 所有測試通過
- [ ] 沒有 lint 錯誤

### 2. 執行檢查

```bash
# 驗證所有題目
uv run python scripts/validate-challenge.py

# 執行安全掃描
uv run python scripts/scan-secrets.py --path .

# 檢查代碼風格（如果有的話）
# flake8 scripts/
# black --check scripts/
```

### 3. 建立 PR

1. 前往您的 Fork 的 GitHub 頁面
2. 點擊 "New Pull Request"
3. 選擇正確的 base 分支（通常是 `main`）
4. 填寫 PR 描述，包含：
   - 變更摘要
   - 相關 Issue（使用 `#123` 連結）
   - 測試說明
   - 截圖（如果適用）

### 4. PR 審查

- 維護者會審查您的 PR
- 可能需要修改，請根據反饋進行調整
- 審查通過後，PR 會被合併

---

## Issue 報告

### Bug Report 模板

```markdown
## Bug 描述
簡要描述問題

## 重現步驟
1. 執行 '...'
2. 點擊 '....'
3. 看到錯誤

## 預期行為
應該發生什麼

## 實際行為
實際發生了什麼

## 環境資訊
- OS: [e.g. macOS 14.0]
- Python: [e.g. 3.11.0]
- uv: [e.g. 0.1.0]
- 專案版本: [e.g. 2.1.0]

## 截圖/日誌
如果適用，請添加截圖或錯誤日誌
```

### Feature Request 模板

```markdown
## 功能描述
詳細描述您想要的功能

## 問題/需求
這個功能解決什麼問題？

## 建議的解決方案
您希望如何實現這個功能？

## 替代方案
是否有其他解決方案？

## 額外資訊
任何其他相關資訊
```

---

## 代碼風格

### Python

- 遵循 [PEP 8](https://pep8.org/)
- 使用 4 個空格縮進
- 行長度限制：100 字元
- 使用類型提示（Type Hints）

### Shell Scripts

- 使用 `#!/bin/bash`
- 使用 `set -euo pipefail`
- 變數使用引號：`"$variable"`

### 文檔

- Markdown 格式
- 中文文檔使用繁體中文
- 代碼範例包含註釋

---

## 專案結構

```
is1ab-CTF-template/
├── scripts/          # 腳本目錄
├── docs/            # 文檔目錄
├── web-interface/   # Web 介面
├── challenge-template/  # 題目模板
└── .github/         # GitHub 配置
```

---

## 測試

在提交 PR 前，請確保：

```bash
# 測試題目創建
uv run python scripts/create-challenge.py web test_challenge baby --author "Test"

# 測試題目驗證
uv run python scripts/validate-challenge.py challenges/web/test_challenge/

# 測試安全掃描
uv run python scripts/scan-secrets.py --path challenges/web/test_challenge/

# 清理測試題目
rm -rf challenges/web/test_challenge
```

---

## 問題？

如果您在貢獻過程中遇到問題，可以：

- 查看 [文檔](docs/README.md)
- 查看 [常見問題](docs/troubleshooting.md)
- 建立 [Issue](https://github.com/is1ab/is1ab-CTF-template/issues)

---

**感謝您的貢獻！** 🎉

