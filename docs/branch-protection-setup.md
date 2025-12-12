# 🔒 Branch Protection Rules 配置指南

> **文檔版本**: v1.0
> **建立日期**: 2025-12-12
> **用途**: 配置 main 分支保護規則，確保代碼質量和安全性

---

## 📋 目錄

1. [概述](#概述)
2. [為什麼需要 Branch Protection](#為什麼需要-branch-protection)
3. [推薦配置](#推薦配置)
4. [配置步驟](#配置步驟)
5. [自動化配置](#自動化配置)
6. [驗證配置](#驗證配置)
7. [常見場景](#常見場景)
8. [故障排除](#故障排除)

---

## 🎯 概述

Branch Protection Rules 是 GitHub 提供的強大功能，用於保護重要分支（如 `main`）免受意外或惡意修改。

### 關鍵保護措施

- ✅ 強制通過 Pull Request 合併
- ✅ 要求 Code Review 批准
- ✅ 必須通過 CI/CD 檢查
- ✅ 防止強制推送和分支刪除
- ✅ 確保分支是最新的

---

## 🛡️ 為什麼需要 Branch Protection

### 問題場景

**沒有 Branch Protection 時可能發生**：

❌ 開發者直接推送到 main，跳過 Code Review
❌ 未經測試的代碼進入主分支
❌ 敏感資料（flag）意外被推送
❌ 分支被誤刪除
❌ 強制推送覆蓋歷史

### 使用 Branch Protection 後

✅ 所有變更必須通過 PR
✅ 自動執行安全掃描和驗證
✅ 至少 1 位審核者批准才能合併
✅ 防止意外的破壞性操作
✅ 保持主分支穩定可部署

---

## ⚙️ 推薦配置

### 基礎配置（必須）

```yaml
Branch name pattern: main

✅ Require a pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale pull request approvals when new commits are pushed
  ✅ Require review from Code Owners (可選)

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  Required status checks:
    - validate-challenge
    - security-scan / flag-scan
    - security-scan / sensitive-files
    - security-scan / advanced-scan
    - security-scan / docker-security

✅ Require conversation resolution before merging

✅ Do not allow bypassing the above settings
```

### 進階配置（可選但推薦）

```yaml
✅ Require signed commits (強烈推薦)
  # 確保所有 commits 都經過 GPG 簽名

✅ Require linear history (可選)
  # 強制使用 rebase 或 squash merge

✅ Include administrators
  # 管理員也必須遵守保護規則

❌ Allow force pushes
  # 禁止強制推送

❌ Allow deletions
  # 禁止刪除分支
```

---

## 📝 配置步驟

### 方法 A: 通過 GitHub Web Interface（推薦新手）

#### Step 1: 前往 Branch Protection 設定

1. 前往您的 Private Repository
2. 點擊 **Settings** 標籤
3. 左側選單點擊 **Branches**
4. 點擊 **Add branch protection rule**

或直接訪問：
```
https://github.com/your-org/2025-is1ab-CTF/settings/branch_protection_rules/new
```

#### Step 2: 設定 Branch Name Pattern

```
Branch name pattern: main
```

> 💡 **提示**：也可以使用 pattern 如 `main` 或 `release/*` 保護多個分支

#### Step 3: 配置 Pull Request 要求

勾選以下選項：

**✅ Require a pull request before merging**

進入子選項：
- **Require approvals**: 設為 `1`（或更多，建議 1-2）
- ✅ **Dismiss stale pull request approvals when new commits are pushed**
  - 當有新 commit 時，舊的批准會被撤銷
- ✅ **Require review from Code Owners**（可選）
  - 需要 CODEOWNERS 文件中指定的人員審核

**說明**：
- 1 位審核者：適合小團隊（5-10 人）
- 2 位審核者：適合中大型團隊（10+ 人）

#### Step 4: 配置 Status Checks（CI/CD）

**✅ Require status checks to pass before merging**

進入子選項：
- ✅ **Require branches to be up to date before merging**
  - 確保分支包含 main 的最新變更

**添加 Required status checks**：

在搜尋框輸入並選擇：
```
validate-challenge
security-scan / flag-scan
security-scan / sensitive-files
security-scan / advanced-scan
security-scan / docker-security
```

> 💡 **提示**：這些是從 [validate-challenge.yml](../.github/workflows/validate-challenge.yml) 和 [security-scan.yml](../.github/workflows/security-scan.yml) 定義的 jobs

#### Step 5: 配置其他保護措施

**✅ Require conversation resolution before merging**
- 所有 PR 評論必須被解決才能合併

**✅ Require signed commits**（強烈推薦）
- 所有 commits 必須使用 GPG 簽名
- 提供額外的安全保障

**✅ Require linear history**（可選）
- 強制使用 squash merge 或 rebase
- 保持 Git 歷史整潔

**✅ Include administrators**
- 管理員也必須遵守這些規則
- 強烈推薦啟用

**❌ Allow force pushes**（保持關閉）
- 禁止 `git push --force`

**❌ Allow deletions**（保持關閉）
- 禁止刪除 main 分支

#### Step 6: Restrict who can push

**可選配置**：

如果想限制誰可以直接推送（即使有 Write 權限）：

**✅ Restrict pushes that create matching branches**
- 指定可以推送的人員或團隊
- 適用於嚴格管控的場景

#### Step 7: 保存配置

點擊 **Create** 按鈕保存配置

---

### 方法 B: 使用 GitHub CLI（適合自動化）

#### 前置需求

安裝 GitHub CLI：
```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# 登入
gh auth login
```

#### 使用預設配置腳本

創建 `scripts/setup-branch-protection.sh`：

```bash
#!/bin/bash
# Branch Protection Setup Script

set -e

REPO_OWNER="${1:-your-org}"
REPO_NAME="${2:-2025-is1ab-CTF}"
BRANCH="main"

echo "🔒 設定 Branch Protection Rules"
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Branch: $BRANCH"
echo ""

# 使用 gh api 設定 branch protection
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection" \
  -f required_status_checks[strict]=true \
  -f "required_status_checks[contexts][]=validate-challenge" \
  -f "required_status_checks[contexts][]=security-scan / flag-scan" \
  -f "required_status_checks[contexts][]=security-scan / sensitive-files" \
  -f "required_status_checks[contexts][]=security-scan / advanced-scan" \
  -f "required_status_checks[contexts][]=security-scan / docker-security" \
  -f enforce_admins=true \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f required_pull_request_reviews[require_code_owner_reviews]=false \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -F required_linear_history=false \
  -F allow_force_pushes=false \
  -F allow_deletions=false \
  -F required_conversation_resolution=true

echo ""
echo "✅ Branch Protection Rules 已設定完成"
echo ""
echo "查看設定："
echo "https://github.com/$REPO_OWNER/$REPO_NAME/settings/branches"
```

#### 執行腳本

```bash
chmod +x scripts/setup-branch-protection.sh
./scripts/setup-branch-protection.sh your-org 2025-is1ab-CTF
```

---

### 方法 C: 使用 GitHub API（適合 CI/CD）

創建 `.github/workflows/setup-branch-protection.yml`：

```yaml
name: Setup Branch Protection

on:
  workflow_dispatch:

permissions:
  contents: write
  administration: write

jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - name: Setup Branch Protection Rules
        uses: actions/github-script@v7
        with:
          script: |
            const owner = context.repo.owner;
            const repo = context.repo.repo;
            const branch = 'main';

            await github.rest.repos.updateBranchProtection({
              owner,
              repo,
              branch,
              required_status_checks: {
                strict: true,
                contexts: [
                  'validate-challenge',
                  'security-scan / flag-scan',
                  'security-scan / sensitive-files',
                  'security-scan / advanced-scan',
                  'security-scan / docker-security'
                ]
              },
              enforce_admins: true,
              required_pull_request_reviews: {
                dismiss_stale_reviews: true,
                require_code_owner_reviews: false,
                required_approving_review_count: 1
              },
              restrictions: null,
              required_linear_history: false,
              allow_force_pushes: false,
              allow_deletions: false,
              required_conversation_resolution: true
            });

            console.log('✅ Branch protection rules updated successfully');
```

---

## ✅ 驗證配置

### 檢查 1: 查看 Branch Protection Rules

1. 前往 Repository **Settings** → **Branches**
2. 確認看到 `main` 分支的保護規則
3. 點擊 **Edit** 查看詳細配置

### 檢查 2: 測試 Direct Push（應該失敗）

```bash
# 嘗試直接推送到 main（應該被拒絕）
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "test: direct push"
git push origin main

# 預期結果：
# remote: error: GH006: Protected branch update failed for refs/heads/main.
# remote: error: Changes must be made through a pull request.
```

### 檢查 3: 測試 PR Workflow（應該成功）

```bash
# 正確的方式：通過 PR
git checkout -b test/branch-protection
echo "test" >> test.txt
git add test.txt
git commit -m "test: branch protection"
git push origin test/branch-protection

# 在 GitHub 創建 PR
# 應該看到：
# ✅ Required status checks (等待或通過)
# ✅ Requires 1 approval (等待)
```

### 檢查 4: 測試 Force Push（應該失敗）

```bash
# 嘗試強制推送（應該被拒絕）
git push origin main --force

# 預期結果：
# remote: error: GH006: Protected branch update failed for refs/heads/main.
# remote: error: Cannot force-push to this branch.
```

---

## 📚 常見場景

### 場景 1: 緊急修復（Hotfix）

**問題**：需要緊急修復生產環境問題，但 Branch Protection 阻止快速合併

**解決方案 A：臨時調整規則**（不推薦）

1. **Settings** → **Branches** → **Edit** protection rule
2. 暫時取消勾選部分要求（如 required approvals）
3. 合併 PR
4. **立即恢復**保護規則

**解決方案 B：使用管理員權限**（如果已啟用 Include administrators）

1. 仍需創建 PR
2. 立即自我審核並批准
3. 合併 PR

**解決方案 C：最佳實踐**（推薦）

1. 創建 hotfix PR
2. 快速通知審核者
3. 遵循正常流程
4. 事後 review

### 場景 2: CI/CD 檢查失敗

**問題**：某個 status check 持續失敗，但需要合併

**解決方案 A：修復問題**（推薦）

1. 檢查失敗原因
2. 修復代碼或配置
3. 推送新 commit
4. 等待 CI/CD 重新執行

**解決方案 B：暫時移除檢查**

1. **Settings** → **Branches** → **Edit**
2. 移除失敗的 status check
3. 合併 PR
4. **立即添加回**檢查

### 場景 3: 新增 CI/CD Workflow

**問題**：新增了 CI/CD workflow，但 Branch Protection 沒有包含新的檢查

**解決方案**：

1. **Settings** → **Branches** → **Edit** main protection rule
2. 在 **Required status checks** 中搜尋並添加新的 check
3. 點擊 **Save changes**

### 場景 4: 管理員需要快速推送

**問題**：管理員需要快速更新配置文件

**如果已啟用 "Include administrators"**：
- 管理員也必須遵守規則
- 創建 PR → 自我審核 → 合併

**如果未啟用 "Include administrators"**：
- 管理員可以直接推送
- ⚠️ 不推薦，應該啟用此選項

---

## 🔧 故障排除

### 問題 1: 無法創建 Branch Protection Rule

**症狀**：
```
Error: You don't have permission to create branch protection rules
```

**原因**：
- 您沒有 Repository 的 Admin 權限

**解決方案**：
1. 請管理員協助設定
2. 或請管理員授予您 Admin 權限

---

### 問題 2: Status Check 未顯示

**症狀**：
在添加 Required status checks 時找不到某些檢查

**原因**：
- CI/CD workflow 尚未執行過
- Workflow 名稱不正確
- Workflow 被禁用

**解決方案**：
1. 確保 workflow 文件存在於 `.github/workflows/`
2. 創建一個測試 PR 觸發 workflow
3. 等待 workflow 執行完成
4. 重新嘗試添加 status check

---

### 問題 3: PR 無法合併

**症狀**：
```
Merging is blocked
```

**可能原因與解決方案**：

**原因 1：缺少審核批准**
- 解決：等待至少 1 位審核者批准

**原因 2：Status checks 失敗**
- 解決：修復問題並推送新 commit

**原因 3：分支不是最新的**
- 解決：同步 main 分支
  ```bash
  git fetch origin main
  git merge origin/main
  git push
  ```

**原因 4：有未解決的對話**
- 解決：解決所有 PR 評論

---

### 問題 4: 管理員無法推送

**症狀**：
管理員也無法直接推送到 main

**原因**：
啟用了 "Include administrators"

**解決方案**：
這是**預期行為**！管理員應該：
1. 創建 feature branch
2. 提交 PR
3. 請其他人審核（或自我審核）
4. 合併 PR

如果確實需要緊急直接推送：
1. 臨時取消 "Include administrators"
2. 推送變更
3. **立即恢復**設定

---

### 問題 5: 設定後 PR 無法創建

**症狀**：
創建 PR 時報錯

**原因**：
某些 status checks 可能無法在 PR 創建時立即執行

**解決方案**：
1. 確保所有 required status checks 的 workflows 都存在
2. 檢查 workflow 的觸發條件（`on: pull_request`）
3. 可以暫時移除某些檢查，等 workflow 修復後再添加

---

## 📊 配置檢查清單

### 初次設定

- [ ] 設定 branch name pattern 為 `main`
- [ ] 啟用 "Require a pull request before merging"
- [ ] 設定 required approvals 為 1（或更多）
- [ ] 啟用 "Dismiss stale pull request approvals"
- [ ] 添加所有 required status checks
- [ ] 啟用 "Require branches to be up to date"
- [ ] 啟用 "Require conversation resolution"
- [ ] 啟用 "Include administrators"
- [ ] 禁用 "Allow force pushes"
- [ ] 禁用 "Allow deletions"
- [ ] 點擊 Create/Save 保存配置

### 驗證測試

- [ ] 測試直接推送（應該失敗）
- [ ] 測試通過 PR 合併（應該成功）
- [ ] 測試 force push（應該失敗）
- [ ] 確認所有 status checks 正常運行
- [ ] 確認審核流程正常

### 定期維護

- [ ] 每月檢查配置是否符合需求
- [ ] 有新增 workflow 時更新 required checks
- [ ] 檢查團隊規模是否需要調整 required approvals
- [ ] 審查是否有需要調整的保護措施

---

## 🔗 相關資源

### GitHub 官方文檔

- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)

### 內部文檔

- [Git Flow 標準化指南](git-flow-standard.md)
- [改善實施指南](IMPROVEMENT_IMPLEMENTATION_GUIDE.md)
- [角色與權限管理](roles-and-permissions.md)

---

**維護者**: IS1AB Team
**最後更新**: 2025-12-12
**文檔版本**: v1.0
