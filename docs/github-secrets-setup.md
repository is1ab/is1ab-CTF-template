# 🔐 GitHub Secrets 配置指南

> **文檔版本**: v1.0
> **建立日期**: 2025-12-12
> **用途**: 配置自動化 Release 所需的 GitHub Secrets

---

## 📋 目錄

1. [概述](#概述)
2. [必要的 Secrets](#必要的-secrets)
3. [配置步驟](#配置步驟)
4. [驗證配置](#驗證配置)
5. [安全最佳實踐](#安全最佳實踐)
6. [故障排除](#故障排除)

---

## 🎯 概述

為了讓自動化 Release 流程（[auto-release.yml](../.github/workflows/auto-release.yml)）能夠正常運作，需要配置 GitHub Secrets 來授權工作流程訪問 Public Repository。

### 為什麼需要 Secrets？

自動化 Release 流程需要：
1. ✅ 從 Private Repository 讀取題目
2. ✅ 推送內容到 Public Repository
3. ✅ 觸發 Public Repository 的 GitHub Pages 部署
4. ✅ 創建 Release Tag

這些操作需要具有適當權限的 GitHub Token。

---

## 🔑 必要的 Secrets

### PUBLIC_REPO_TOKEN

**用途**: 允許 Private Repository 的工作流程訪問和操作 Public Repository

**權限需求**:
- ✅ `repo` - 完整的 repository 訪問權限
- ✅ `workflow` - 更新 GitHub Actions 工作流程

**作用範圍**:
- 讀取 Public Repository
- 推送代碼到 Public Repository
- 創建 Release 和 Tag
- 觸發 Public Repository 的 Workflows

---

## 📝 配置步驟

### 步驟 1: 創建 GitHub Personal Access Token (PAT)

#### 方法 A: 使用 Fine-grained Personal Access Token (推薦)

1. **前往 GitHub Settings**
   ```
   GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
   ```
   或直接訪問: https://github.com/settings/tokens?type=beta

2. **點擊 "Generate new token"**

3. **配置 Token 設定**

   **基本資訊**:
   - **Token name**: `CTF-Auto-Release-Token`
   - **Description**: `Token for auto-release workflow from private to public repo`
   - **Expiration**: `90 days` 或 `Custom` (建議定期更新)
   - **Resource owner**: 選擇您的組織 (例如：`is1ab-org`)

4. **Repository access**
   - 選擇 **"Only select repositories"**
   - 選擇您的 **Public Repository** (例如：`2025-is1ab-CTF-public`)

5. **Permissions**

   **Repository permissions** (選擇以下權限):
   ```
   ✅ Actions: Read and write
   ✅ Contents: Read and write
   ✅ Metadata: Read-only (自動選擇)
   ✅ Workflows: Read and write
   ```

6. **點擊 "Generate token"**

7. **⚠️ 重要：立即複製 Token**
   - Token 只會顯示一次
   - 立即保存到安全的地方
   - 格式類似：`github_pat_11A...`

#### 方法 B: 使用 Classic Personal Access Token

1. **前往 GitHub Settings**
   ```
   GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   ```
   或直接訪問: https://github.com/settings/tokens

2. **點擊 "Generate new token (classic)"**

3. **配置 Token 設定**
   - **Note**: `CTF-Auto-Release-Token`
   - **Expiration**: `90 days` 或更長

   **Select scopes** (選擇以下權限):
   ```
   ✅ repo (完整的 repository 訪問)
     ✅ repo:status
     ✅ repo_deployment
     ✅ public_repo
     ✅ repo:invite
   ✅ workflow (更新 GitHub Actions workflows)
   ```

4. **點擊 "Generate token"**

5. **⚠️ 立即複製 Token**
   - 格式類似：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

### 步驟 2: 將 Token 添加到 Private Repository Secrets

1. **前往 Private Repository Settings**
   ```
   GitHub → Your Private Repo → Settings → Secrets and variables → Actions
   ```
   或直接訪問: `https://github.com/your-org/2025-is1ab-CTF/settings/secrets/actions`

2. **點擊 "New repository secret"**

3. **配置 Secret**
   - **Name**: `PUBLIC_REPO_TOKEN`
   - **Secret**: 貼上剛才複製的 Token

4. **點擊 "Add secret"**

---

### 步驟 3: 驗證 Secret 已添加

1. 返回 **Secrets and variables → Actions**
2. 確認看到 `PUBLIC_REPO_TOKEN` 在 Repository secrets 列表中
3. 顯示為：`PUBLIC_REPO_TOKEN` Updated X minutes ago

---

## ✅ 驗證配置

### 測試 1: 檢查 Secret 是否存在

在 Private Repository 中創建測試工作流程：

```yaml
# .github/workflows/test-secret.yml
name: Test Secret

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Check Secret
        env:
          TOKEN: ${{ secrets.PUBLIC_REPO_TOKEN }}
        run: |
          if [ -z "$TOKEN" ]; then
            echo "❌ PUBLIC_REPO_TOKEN not found!"
            exit 1
          else
            echo "✅ PUBLIC_REPO_TOKEN exists"
            echo "Token length: ${#TOKEN}"
          fi
```

執行測試：
1. 前往 **Actions** → **Test Secret** → **Run workflow**
2. 檢查輸出應該顯示 "✅ PUBLIC_REPO_TOKEN exists"

### 測試 2: 測試 Token 權限

```yaml
# .github/workflows/test-token-permissions.yml
name: Test Token Permissions

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test Token Access
        env:
          GITHUB_TOKEN: ${{ secrets.PUBLIC_REPO_TOKEN }}
        run: |
          # 測試讀取 Public Repo
          curl -H "Authorization: token $GITHUB_TOKEN" \
               https://api.github.com/repos/your-org/2025-is1ab-CTF-public

          # 測試權限
          curl -H "Authorization: token $GITHUB_TOKEN" \
               https://api.github.com/user
```

### 測試 3: Dry-run 自動化 Release

使用 `dry_run` 模式測試完整流程：

1. 前往 **Actions** → **Auto Release to Public** → **Run workflow**
2. 填寫參數：
   - **release_tag**: `test-2025-01-01`
   - **target_repo**: `your-org/2025-is1ab-CTF-public`
   - **dry_run**: ✅ `true`
3. 點擊 **Run workflow**
4. 檢查執行結果

---

## 🛡️ 安全最佳實踐

### 1. Token 權限最小化

✅ **建議**：使用 Fine-grained Token，只授予必要的權限
❌ **避免**：使用 Classic Token 的 `admin:org` 等過度權限

### 2. 定期更新 Token

```
建議更新週期：
- 生產環境：每 90 天
- 測試環境：每 180 天
```

**更新流程**：
1. 創建新 Token
2. 更新 Secret
3. 測試工作流程
4. 刪除舊 Token

### 3. Token 過期監控

在日曆中設置提醒：
- Token 過期前 7 天
- Token 過期前 1 天

### 4. 使用 Organization Secrets（可選）

如果有多個 Private Repository 需要訪問同一個 Public Repository：

1. 前往 **Organization Settings**
2. **Secrets and variables** → **Actions**
3. 創建 Organization Secret
4. 選擇可訪問的 Repositories

### 5. 審計日誌

定期檢查 Token 使用記錄：
```
GitHub → Settings → Developer settings → Personal access tokens → Your Token → Recent activity
```

### 6. 緊急撤銷

如果 Token 洩漏：
1. 立即前往 GitHub Settings 刪除 Token
2. 創建新 Token
3. 更新所有使用該 Token 的 Secrets
4. 檢查 Git 歷史是否有 Token 洩漏
5. 通知團隊

---

## 🔧 故障排除

### 問題 1: "Bad credentials" 錯誤

**症狀**：
```
Error: Bad credentials
```

**可能原因**：
- Token 已過期
- Token 被刪除
- Token 權限不足

**解決方案**：
1. 檢查 Token 是否有效：
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```
2. 創建新 Token
3. 更新 Secret

---

### 問題 2: "Resource not accessible by integration" 錯誤

**症狀**：
```
Error: Resource not accessible by integration
```

**可能原因**：
- Token 缺少必要權限
- Repository 可見性設定問題

**解決方案**：
1. 確認 Token 具有 `repo` 和 `workflow` 權限
2. 確認 Token 可以訪問 Public Repository
3. 對於 Fine-grained Token，確認已選擇正確的 Repository

---

### 問題 3: "Secret not found" 錯誤

**症狀**：
```
Error: Secret PUBLIC_REPO_TOKEN not found
```

**可能原因**：
- Secret 名稱拼寫錯誤
- Secret 未添加到正確的 Repository
- Secret 被意外刪除

**解決方案**：
1. 檢查 Secret 名稱是否為 `PUBLIC_REPO_TOKEN`（區分大小寫）
2. 確認 Secret 添加到 **Private Repository**（不是 Public Repository）
3. 重新添加 Secret

---

### 問題 4: Token 權限不足

**症狀**：
```
Error: You don't have permission to push to this repository
```

**可能原因**：
- Token 權限不包含 `Contents: Write`
- Token 沒有訪問 Public Repository 的權限

**解決方案**：
1. 重新創建 Token，確保包含所需權限
2. 對於 Fine-grained Token，確認 Repository access 包含 Public Repository

---

### 問題 5: Workflow 無法觸發

**症狀**：
```
Error: Could not trigger workflow
```

**可能原因**：
- Token 缺少 `Actions: Write` 或 `workflow` 權限
- Public Repository 的 Workflow 不存在

**解決方案**：
1. 確認 Token 包含 `Actions: Write` 和 `Workflows: Write` 權限
2. 確認 Public Repository 存在 `deploy-pages.yml` workflow
3. 檢查 workflow 文件名是否正確

---

## 📊 Token 管理檢查清單

### 創建 Token 時

- [ ] 使用有意義的名稱（例如：`CTF-Auto-Release-Token`）
- [ ] 設定適當的過期時間（建議 90 天）
- [ ] 僅授予必要的權限
- [ ] 記錄 Token 創建日期和用途

### 添加到 Secrets 時

- [ ] 名稱正確：`PUBLIC_REPO_TOKEN`
- [ ] 添加到 **Private Repository**
- [ ] Token 完整複製（沒有多餘空格）
- [ ] 驗證 Secret 已成功添加

### 定期維護

- [ ] 每 90 天更新 Token
- [ ] 檢查 Token 使用記錄
- [ ] 驗證 Token 權限仍然正確
- [ ] 測試自動化流程

### 團隊交接

- [ ] 記錄 Token 所有者
- [ ] 文檔化 Token 用途
- [ ] 提供更新流程文檔
- [ ] 設定過期提醒

---

## 🔗 相關資源

### GitHub 官方文檔

- [Creating a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Fine-grained personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)

### 內部文檔

- [自動化 Release 工作流程](../.github/workflows/auto-release.yml)
- [安全檢查清單](security-checklist.md)
- [CTF 完整工作流程](ctf-challenge-workflow.md)

---

## 📞 需要幫助？

### 遇到問題？

1. 查看 [故障排除](#故障排除) 章節
2. 檢查 GitHub Actions 執行日誌
3. 在 GitHub Issues 提問
4. 聯繫團隊管理員

### 安全問題

如果發現 Token 洩漏或安全問題：
1. 立即撤銷 Token
2. 通知團隊管理員
3. 檢查使用日誌
4. 創建新 Token

---

**維護者**: IS1AB Team
**最後更新**: 2025-12-12
**文檔版本**: v1.0
