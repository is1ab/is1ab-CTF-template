# 👥 角色與權限管理

> 清晰的角色定義和權限分配指南

## 📋 目錄

- [角色定義](#角色定義)
- [權限分配](#權限分配)
- [職責說明](#職責說明)
- [最佳實踐](#最佳實踐)

---

## 角色定義

### 🎯 管理者 (Admin)

**權限等級**：最高權限

**職責**：
- 管理 Repository 設定和權限
- 設定分支保護規則
- 審查並合併 Pull Request
- 執行發布流程（Private → Public）
- 管理 GitHub Actions 和 CI/CD
- 處理敏感操作（如 flag 重置）

**GitHub 權限**：Admin

---

### ✍️ 題目作者 (Challenge Author / Write)

**權限等級**：開發權限

**職責**：
- 創建新題目（使用 CLI 或 Web GUI）
- 在 Feature Branch 開發題目
- 提交 Pull Request
- 回應 Code Review 意見
- 修復驗證發現的問題
- 更新題目 metadata

**GitHub 權限**：Write

**工作流程**：
```bash
# 1. 建立 feature branch
git checkout -b challenge/web/sql-injection

# 2. 創建題目
uv run python scripts/create-challenge.py web sql_injection middle --author "YourName"

# 3. 開發和測試
# ... 編輯題目內容 ...

# 4. 驗證題目
uv run python scripts/validate-challenge.py challenges/web/sql_injection/

# 5. 提交 PR
git add .
git commit -m "feat(web): add SQL injection challenge"
git push origin challenge/web/sql-injection
# 在 GitHub 上建立 PR
```

---

### 👀 審查者 (Reviewer / Read)

**權限等級**：只讀 + 評論

**職責**：
- 審查 Pull Request
- 測試題目功能
- 檢查題目品質
- 驗證安全掃描結果
- 提供改進建議
- 批准或要求修改

**GitHub 權限**：Read（可通過 PR 評論參與）

**審查檢查清單**：
- [ ] 題目描述清晰明確
- [ ] 難度設定合理
- [ ] Docker 配置正確
- [ ] 沒有敏感資訊洩露（flag、writeup）
- [ ] 解題流程可重現
- [ ] Flag 格式正確
- [ ] 代碼品質良好
- [ ] 通過所有自動化檢查

---

## 權限分配

### GitHub Repository 權限

| 角色 | 權限 | 說明 |
|------|------|------|
| **管理者** | Admin | 完整控制權，包括設定、權限管理、分支保護 |
| **題目作者** | Write | 可以 push、建立 branch、提交 PR |
| **審查者** | Read | 只能查看和評論，不能直接修改 |

### 分支保護規則

**main 分支保護**（建議設定）：

```yaml
保護規則：
  ✅ Require pull request reviews (至少 1-2 人)
  ✅ Require status checks to pass
    - validate-challenge
    - security-scan
    - docker-build-test
  ✅ Require branches to be up to date
  ✅ Include administrators (管理員也需要 review)
  ✅ Restrict who can push (僅管理員)
```

### Feature Branch 權限

- ✅ 所有 Write 權限成員可以建立和 push feature branch
- ✅ Feature branch 可以自由修改，不需要保護
- ✅ PR 合併需要通過審查和自動化檢查

---

## 職責說明

### 管理者職責

#### Repository 設置

```bash
# 1. 使用 Template 建立 Private Dev Repo
# GitHub Web: Use this template → Create repository
# Name: 2024-is1ab-CTF-private
# Visibility: Private

# 2. 設定分支保護
gh api repos/is1ab-org/2024-is1ab-CTF-private/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["validate-challenge","security-scan"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}'

# 3. 邀請團隊成員
gh api repos/is1ab-org/2024-is1ab-CTF-private/collaborators/username \
  --method PUT \
  --field permission=write
```

#### 發布流程

```bash
# 1. 確認所有題目已測試
uv run python scripts/validate-challenge.py

# 2. 執行安全掃描
uv run python scripts/scan-secrets.py --path challenges/

# 3. 建置公開版本
./scripts/build.sh --all public-release

# 4. 建立 PR 到 Public Repo
# 5. 審查並合併
# 6. GitHub Actions 自動部署到 Pages
```

---

### 題目作者職責

#### 開發流程

1. **建立 Feature Branch**
   ```bash
   git checkout -b challenge/web/sql-injection
   ```

2. **創建題目**
   ```bash
   uv run python scripts/create-challenge.py web sql_injection middle --author "YourName"
   ```

3. **開發和測試**
   ```bash
   # 編輯題目內容
   vim challenges/web/sql_injection/public.yml
   vim challenges/web/sql_injection/private.yml
   
   # 測試 Docker
   cd challenges/web/sql_injection/docker
   docker-compose up -d
   
   # 驗證題目
   uv run python scripts/validate-challenge.py challenges/web/sql_injection/
   ```

4. **提交 PR**
   ```bash
   git add .
   git commit -m "feat(web): add SQL injection challenge"
   git push origin challenge/web/sql-injection
   # 在 GitHub 上建立 PR
   ```

5. **回應 Review**
   - 根據審查意見修改
   - 重新 push 到同一個 branch
   - PR 會自動更新

---

### 審查者職責

#### 審查流程

1. **收到 PR 通知**
   - GitHub 會自動指派審查者
   - 或手動請求審查

2. **檢查自動化結果**
   - ✅ 結構驗證通過
   - ✅ 安全掃描通過
   - ✅ Docker 建置成功

3. **人工審查**
   - 檢查題目描述
   - 測試解題流程
   - 驗證 Flag 格式
   - 檢查代碼品質

4. **提供反饋**
   - 使用 GitHub PR 評論
   - 標記需要修改的地方
   - 提供改進建議

5. **批准或要求修改**
   - 如果通過：Approve
   - 如果需要修改：Request Changes

---

## 最佳實踐

### 權限管理

1. **最小權限原則**
   - 只給予必要的權限
   - 定期審查權限分配
   - 移除不再需要的成員

2. **分支保護**
   - main 分支必須保護
   - 要求 PR review
   - 要求通過自動化檢查

3. **審查分配**
   - 至少 1-2 人審查
   - 避免作者自己審查自己的 PR
   - 重要變更需要更多審查者

### 工作流程

1. **Feature Branch 命名**
   - 使用清晰的名稱：`challenge/<category>/<name>`
   - 避免使用個人名稱

2. **Commit 訊息**
   - 遵循 Conventional Commits
   - 清楚描述變更內容

3. **PR 描述**
   - 包含題目資訊
   - 說明變更內容
   - 連結相關 Issue

### 安全實踐

1. **敏感資料**
   - 永遠不要在 public.yml 中包含 flag
   - 使用 private.yml 存儲敏感資訊
   - 定期執行安全掃描

2. **權限審查**
   - 定期檢查誰有權限
   - 移除不再活躍的成員
   - 審查權限變更日誌

---

## 常見問題

### Q: 題目作者可以合併自己的 PR 嗎？

**A:** 不建議。即使有 Write 權限，也應該等待審查者批准。可以設定分支保護規則要求至少 1 人審查。

### Q: 審查者需要 Write 權限嗎？

**A:** 不需要。Read 權限即可進行審查和評論。只有需要直接修改代碼時才需要 Write 權限。

### Q: 如何處理緊急修復？

**A:** 如果是緊急情況，管理員可以：
1. 暫時降低分支保護要求
2. 直接合併到 main
3. 事後進行 review
4. 恢復分支保護規則

### Q: 多個題目作者可以同時開發嗎？

**A:** 可以。每個題目使用獨立的 feature branch，不會衝突。建議：
- 使用清晰的 branch 命名
- 定期同步 main 分支
- 避免修改其他題目的 branch

---

**最後更新**：2025-01-XX  
**維護者**：IS1AB Team

