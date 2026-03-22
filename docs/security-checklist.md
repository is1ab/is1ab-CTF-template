# ✅ 安全配置檢查清單

> **快速檢查清單** - 確保你的 IS1AB CTF 專案已正確配置所有安全措施

---

## 🎯 使用方式

使用此檢查清單確保專案符合安全標準。建議在以下時機檢查：

- ✅ 專案初始化時
- ✅ 新成員加入團隊時
- ✅ 比賽開始前
- ✅ 每月定期檢查

---

## 📋 完整檢查清單

### 1️⃣ Git Hooks 配置

- [ ] **Pre-commit hook 已安裝**
  ```bash
  ls -la .git/hooks/pre-commit
  # 應該顯示文件且有執行權限 (-rwxr-xr-x)
  ```

- [ ] **Pre-push hook 已安裝**
  ```bash
  ls -la .git/hooks/pre-push
  # 應該顯示文件且有執行權限 (-rwxr-xr-x)
  ```

- [ ] **測試 pre-commit hook**
  ```bash
  # 創建測試文件包含 flag
  echo "is1abCTF{test_flag}" > test.txt
  git add test.txt
  git commit -m "test"
  # 應該被 hook 阻止
  rm test.txt
  ```

**參考**: [如何安裝 hooks](../scripts/setup-hooks.sh)

---

### 2️⃣ .gitignore 配置

- [ ] **.gitignore 包含所有敏感文件規則**
  ```bash
  # 檢查關鍵規則
  grep "**/flag.txt" .gitignore
  grep "**/private.yml" .gitignore
  grep "**/secrets.yml" .gitignore
  grep "*.key" .gitignore
  grep "*.pem" .gitignore
  ```

- [ ] **驗證敏感文件未被追蹤**
  ```bash
  git ls-files | grep -E "(flag\.txt|private\.yml|secrets\.yml|\.key|\.pem)"
  # 應該無輸出
  ```

---

### 3️⃣ GitHub Secrets 配置

- [ ] **PUBLIC_REPO_TOKEN 已設置**
  - 前往: `Settings` → `Secrets and variables` → `Actions`
  - 確認存在 `PUBLIC_REPO_TOKEN`
  - 權限: `repo` + `workflow`

- [ ] **SLACK_WEBHOOK_URL 已設置** (可選)
  - 用於接收通知
  - 可在 `config.yml` 中配置

**參考**: [GitHub Secrets 設置指南](github-secrets-setup.md)

---

### 4️⃣ 分支保護規則

- [ ] **Main 分支已啟用保護**
  - 前往: `Settings` → `Branches`
  - 確認 `main` 有保護規則

- [ ] **必要配置已啟用**:
  - [ ] ✅ Require a pull request before merging
  - [ ] ✅ Require approvals: 1
  - [ ] ✅ Dismiss stale pull request approvals
  - [ ] ✅ Require status checks to pass
  - [ ] ✅ Require branches to be up to date
  - [ ] ✅ Require conversation resolution
  - [ ] ✅ Include administrators
  - [ ] ❌ Allow force pushes (應該禁用)
  - [ ] ❌ Allow deletions (應該禁用)

- [ ] **Required status checks 已添加**:
  - [ ] `security-scan / flag-scan`
  - [ ] `security-scan / sensitive-files`
  - [ ] `security-scan / advanced-scan`
  - [ ] `security-scan / docker-security`

**參考**: [分支保護設置指南](branch-protection-setup.md)

---

### 5️⃣ CODEOWNERS 配置

- [ ] **CODEOWNERS 文件存在**
  ```bash
  ls -la .github/CODEOWNERS
  ```

- [ ] **已更新實際的 GitHub 用戶名**
  ```bash
  # 檢查文件內容
  cat .github/CODEOWNERS | grep "@"
  # 不應該包含 @admin, @senior-dev 等佔位符
  ```

- [ ] **在分支保護中啟用 Code Owners review** (可選)

---

### 6️⃣ CI/CD Workflows

- [ ] **所有 workflows 正常運行**
  - 前往: `Actions` 標籤
  - 確認最近的 workflow runs 通過

- [ ] **Security Scan workflow 已測試**
  ```bash
  # 創建測試 PR 觸發 workflow
  git checkout -b test/security-scan
  git push origin test/security-scan
  # 在 GitHub 創建 PR 並觀察 workflow
  ```

- [ ] **Build Public workflow 已測試** (如需要發布)

**參考**: `.github/workflows/` 目錄

---

### 7️⃣ Commit 簽名 (強烈推薦)

- [ ] **GPG 金鑰已生成**
  ```bash
  gpg --list-secret-keys --keyid-format=long
  # 應該列出至少一個金鑰
  ```

- [ ] **Git 已配置使用 GPG 金鑰**
  ```bash
  git config --local commit.gpgsign
  # 應該輸出: true
  ```

- [ ] **GPG 公鑰已添加到 GitHub**
  - 前往: `Settings` → `SSH and GPG keys`
  - 確認公鑰已添加

- [ ] **測試簽名 commit**
  ```bash
  git commit --allow-empty -S -m "test: GPG signature"
  git log --show-signature -1
  # 應該顯示 "Good signature from..."
  ```

**參考**: [Commit 簽名指南](commit-signing-guide.md)

---

### 8️⃣ 配置文件驗證

- [ ] **config.yml 已正確配置**
  ```bash
  uv run python scripts/verify-setup.py
  # 檢查輸出是否有錯誤
  ```

- [ ] **關鍵欄位已填寫**:
  - [ ] `project.flag_prefix`
  - [ ] `project.organization`
  - [ ] `public_release.repository.name` (如需要發布)
  - [ ] `team.default_author`
  - [ ] `team.reviewers`

- [ ] **安全掃描已啟用**:
  - [ ] `security.scan_sensitive_data: true`
  - [ ] `security.scan_level: normal` 或 `strict`

---

### 9️⃣ 文檔完整性

- [ ] **README.md 已更新**
  - 包含專案特定資訊
  - 移除模板佔位符

- [ ] **CONTRIBUTING.md 已審查**
  - 符合團隊工作流程

- [ ] **必要文檔已閱讀**:
  - [ ] [快速開始指南](getting-started.md)
  - [ ] [安全工作流程指南](security-workflow-guide.md)
  - [ ] [Git 工作流程指南](git-workflow-guide.md)

---

### 🔟 題目安全檢查

- [ ] **Private/Public 分離正確**
  ```bash
  # 檢查題目結構
  ls challenges/*/*/private.yml
  ls challenges/*/*/public.yml
  # 兩者都應該存在
  ```

- [ ] **Private.yml 不在 git 追蹤中**
  ```bash
  git ls-files | grep private.yml
  # 應該無輸出（除了模板）
  ```

- [ ] **Flag 格式正確**
  - 檢查 `private.yml` 中的 flag
  - 應該符合: `is1abCTF{...}` (或配置的前綴)

- [ ] **Public-release 目錄無敏感資料**
  ```bash
  # 掃描 public-release 目錄
  uv run python scripts/scan-secrets.py --path public-release/ --fail-on-high
  # 應該無 CRITICAL 或 HIGH 等級問題
  ```

---

### 1️⃣1️⃣ 團隊設置

- [ ] **所有團隊成員已添加到 repository**
  - 前往: `Settings` → `Collaborators and teams`

- [ ] **權限設置正確**:
  - **管理員**: Admin 權限
  - **核心成員**: Write 權限
  - **一般成員**: Triage 權限

- [ ] **所有成員已設置 Git hooks**
  ```bash
  # 每位成員執行
  ./scripts/setup-hooks.sh
  ```

- [ ] **所有成員已設置 GPG 簽名** (如要求)

**參考**: [角色與權限管理](roles-and-permissions.md)

---

### 1️⃣2️⃣ 自動化測試

- [ ] **手動執行安全掃描**
  ```bash
  uv run python scripts/scan-secrets.py --path . --format markdown
  # 檢查報告輸出
  ```

- [ ] **手動執行題目驗證**
  ```bash
  uv run python scripts/validate-all-challenges.py
  # 所有題目應該通過驗證
  ```

- [ ] **測試建置腳本**
  ```bash
  bash scripts/build.sh --dry-run
  # 檢查是否正常運行
  ```

---

## 🎉 驗證完成

當所有項目都已勾選，你的專案已符合安全標準！

### 最終確認

執行完整驗證：

```bash
# 1. 驗證專案設置
uv run python scripts/verify-setup.py

# 2. 掃描敏感資料
uv run python scripts/scan-secrets.py --path . --fail-on-high

# 3. 驗證所有題目
uv run python scripts/validate-all-challenges.py

# 4. 測試 hooks
echo "is1abCTF{test}" > test_flag.txt
git add test_flag.txt
git commit -m "test"  # 應該被阻止
rm test_flag.txt
```

---

## 📊 定期維護

### 每週檢查
- [ ] 檢查是否有新的 security alerts
- [ ] 檢查 CI/CD workflows 是否正常

### 每月檢查
- [ ] 審查分支保護規則
- [ ] 更新文檔
- [ ] 檢查團隊成員權限

### 比賽前檢查
- [ ] 運行此完整檢查清單
- [ ] 執行完整的安全掃描
- [ ] 驗證所有題目
- [ ] 確認 Public Release 已就緒

---

## 🔗 相關資源

- [完整安全工作流程指南](security-workflow-guide.md)
- [分支保護設置指南](branch-protection-setup.md)
- [Commit 簽名指南](commit-signing-guide.md)
- [GitHub Secrets 設置指南](github-secrets-setup.md)
- [快速開始指南](getting-started.md)

---

**有問題？** 查看 [FAQ](FAQ.md) 或建立 Issue
