# 🧪 自動化 Release 測試指南

> **文檔版本**: v1.0
> **建立日期**: 2025-12-12
> **用途**: 測試自動化 Release 工作流程，確保發布流程正常運作

---

## 📋 目錄

1. [概述](#概述)
2. [前置準備](#前置準備)
3. [Dry-run 測試](#dry-run-測試)
4. [完整測試流程](#完整測試流程)
5. [驗證清單](#驗證清單)
6. [常見問題](#常見問題)
7. [故障排除](#故障排除)

---

## 🎯 概述

自動化 Release 工作流程（[auto-release.yml](../.github/workflows/auto-release.yml)）是一個關鍵流程，用於：

1. 📦 從 Private Repository 建置公開版本
2. 🔒 執行安全掃描
3. 📡 同步到 Public Repository
4. 🌐 部署 GitHub Pages

在正式使用前，**必須進行完整測試**以確保：
- ✅ 配置正確
- ✅ Secrets 有效
- ✅ 權限足夠
- ✅ 流程順暢

---

## 📝 前置準備

### 檢查清單

在開始測試前，確保已完成以下準備：

#### 1. GitHub Secrets 配置

- [ ] 已創建 `PUBLIC_REPO_TOKEN`
- [ ] Token 具有正確權限（repo + workflow）
- [ ] Secret 已添加到 Private Repository

> 📖 **參考**：[GitHub Secrets 配置指南](github-secrets-setup.md)

#### 2. Public Repository 準備

- [ ] Public Repository 已創建（例如：`org/2025-is1ab-CTF-public`）
- [ ] Repository 可見性設為 **Public**
- [ ] 已啟用 GitHub Actions

#### 3. Workflow 文件檢查

- [ ] `.github/workflows/auto-release.yml` 存在
- [ ] Workflow 語法正確（可使用 GitHub Actions linter）

#### 4. 測試題目準備

- [ ] 至少有 1-2 個完整的題目
- [ ] 題目包含 `public.yml`
- [ ] 題目通過 `validate-challenge.py` 驗證
- [ ] 題目通過 `scan-secrets.py` 掃描

---

## 🧪 Dry-run 測試

Dry-run 模式會執行完整流程，但**不會實際推送到 Public Repository**，是測試的最佳方式。

### 步驟 1: 前往 GitHub Actions

1. 打開您的 Private Repository
2. 點擊 **Actions** 標籤
3. 左側選單找到 **"🚀 Auto Release to Public"**
4. 點擊 **Run workflow** 按鈕

### 步驟 2: 填寫參數

在彈出的對話框中填寫：

```yaml
release_tag: test-2025-12-12       # 測試用的 tag
target_repo: your-org/2025-is1ab-CTF-public  # Public Repository
dry_run: ✅ true                    # ⚠️ 重要：勾選 dry_run
```

**參數說明**：
- **release_tag**: 任意測試用的 tag 名稱（不會實際創建）
- **target_repo**: 目標 Public Repository（格式：`owner/repo`）
- **dry_run**: **必須勾選**，這樣不會實際推送

### 步驟 3: 執行測試

點擊 **Run workflow** 按鈕開始執行

### 步驟 4: 監控執行過程

workflow 會執行以下 jobs：

#### Job 1: 📦 準備公開發布版本

預期時間：2-5 分鐘

**檢查項目**：
- ✅ 統計題目數量
- ✅ Pre-Release 安全掃描
- ✅ 建置公開版本
- ✅ 驗證公開版本（檢查 flag 洩漏）
- ✅ 生成 Release Notes
- ✅ 上傳 artifacts

**查看輸出**：
```
📊 題目統計:
  總計: 5
  Web: 2
  Pwn: 1
  Crypto: 1
  ...

🔒 執行發布前安全掃描...
✅ 安全掃描通過

🏗️ 建置公開版本...
  處理題目: web/sql-injection
  處理題目: pwn/buffer-overflow
  ...
✅ 公開版本建置完成

🔍 驗證公開版本...
✅ 公開版本驗證通過
```

#### Job 2: 📡 同步到公開 Repository

預期時間：⏭️ **Skipped**（因為 dry_run）

在 dry-run 模式下，此 job 會被跳過：
```
⏭️ sync-to-public: Skipped (dry_run enabled)
```

#### Job 3: 🌐 部署 GitHub Pages

預期時間：⏭️ **Skipped**（因為 dry_run）

在 dry-run 模式下，此 job 會被跳過：
```
⏭️ deploy-pages: Skipped (dry_run enabled)
```

#### Job 4: 📊 發布摘要

預期時間：<1 分鐘

生成執行摘要報告

### 步驟 5: 檢查 Artifacts

1. 在 workflow 執行完成後，滾動到頁面底部
2. 找到 **Artifacts** 區塊
3. 應該看到以下文件可供下載：

```
📦 public-release (約 X MB)
   - 包含建置後的公開版本

📝 release-notes (約 1 KB)
   - 包含自動生成的 Release Notes
```

4. **下載並檢查**：
   - 下載 `public-release.zip`
   - 解壓縮並檢查內容
   - 確認沒有 `private.yml` 或 flag

### 步驟 6: 檢查執行結果

#### 成功標準

✅ **Job 1 成功**（prepare-release）
✅ **Job 2 跳過**（sync-to-public）
✅ **Job 3 跳過**（deploy-pages）
✅ **Job 4 成功**（summary）
✅ **Artifacts 已生成**

#### 查看摘要報告

點擊 **Summary** 查看詳細報告：

```markdown
# 🚀 Release 摘要報告

## 📦 Release 資訊
- **Release Tag**: `test-2025-12-12`
- **Target Repository**: `your-org/2025-is1ab-CTF-public`
- **Release Time**: 2025-12-12 13:00:00 UTC

## 📊 執行結果
| Job | 結果 |
|-----|------|
| 準備發布版本 | ✅ 成功 |
| 同步到公開 Repo | ⏭️ 跳過 |
| 部署 Pages | ⏭️ 跳過 |

## 📝 Release Notes
[題目統計和詳細資訊]
```

---

## 🚀 完整測試流程

當 dry-run 測試成功後，可以進行完整測試。

⚠️ **警告**：完整測試會**實際推送**到 Public Repository

### 前置檢查

- [ ] Dry-run 測試已通過
- [ ] Public Repository 已準備好（可以使用測試 repo）
- [ ] 確認不會影響生產環境

### 方法 A: 使用測試 Repository（推薦）

創建一個測試用的 Public Repository：

```
Repository name: test-2025-is1ab-CTF-public
Visibility: Public
```

### 方法 B: 使用正式 Repository（謹慎）

如果已經確信配置正確，可以直接使用正式 repository

### 執行完整測試

#### 步驟 1: 觸發 Workflow

1. **Actions** → **Auto Release to Public** → **Run workflow**
2. 填寫參數：
   ```yaml
   release_tag: test-release-v1
   target_repo: your-org/test-2025-is1ab-CTF-public  # 測試 repo
   dry_run: ❌ false   # 不勾選 dry_run
   ```
3. 點擊 **Run workflow**

#### 步驟 2: 監控執行

**Job 1: 準備發布版本**（與 dry-run 相同）
- 預期時間：2-5 分鐘
- 應該成功

**Job 2: 同步到公開 Repository**
- 預期時間：1-3 分鐘
- **關鍵步驟**：
  ```
  📡 同步到公開 Repository: your-org/test-2025-is1ab-CTF-public
  📦 Release Tag: test-release-v1

  Cloning into 'public-repo'...
  ✅ 同步完成

  ✅ Tag 創建完成: test-release-v1
  ```

**Job 3: 部署 GitHub Pages**
- 預期時間：<1 分鐘
- **關鍵步驟**：
  ```
  🌐 觸發 GitHub Pages 部署...
  ✅ GitHub Pages 部署已觸發
  ```

**Job 4: 發布摘要**
- 預期時間：<1 分鐘
- 生成完整的摘要報告

#### 步驟 3: 驗證 Public Repository

1. **前往 Public Repository**
   ```
   https://github.com/your-org/test-2025-is1ab-CTF-public
   ```

2. **檢查內容**：
   - [ ] 題目已同步
   - [ ] 沒有 `private.yml`
   - [ ] 沒有 flag 洩漏
   - [ ] README.md 存在
   - [ ] LICENSE 存在

3. **檢查 Tag**：
   - 點擊 **Releases** 或 **Tags**
   - 確認看到 `test-release-v1`

4. **檢查 Commit 歷史**：
   - 點擊 **Commits**
   - 應該看到自動生成的 commit：
     ```
     chore: release test-release-v1

     🤖 Automatically generated from private repository
     ...
     ```

#### 步驟 4: 驗證 GitHub Pages

1. **前往 Public Repository Settings**
   ```
   Settings → Pages
   ```

2. **檢查部署狀態**：
   - Source: Deploy from a branch
   - Branch: `main` / `(root)`
   - 狀態應該顯示 "✅ Your site is live at ..."

3. **訪問 GitHub Pages**：
   ```
   https://your-org.github.io/test-2025-is1ab-CTF-public
   ```

4. **驗證內容**：
   - [ ] 頁面可以正常訪問
   - [ ] 顯示題目列表
   - [ ] 樣式正常
   - [ ] 連結可用

---

## ✅ 驗證清單

### Dry-run 測試

- [ ] Job 1 (prepare-release) 執行成功
- [ ] 題目統計正確
- [ ] 安全掃描通過
- [ ] 公開版本建置成功
- [ ] 驗證通過（無 flag 洩漏）
- [ ] Artifacts 已生成並可下載
- [ ] Release Notes 正確生成
- [ ] Job 2/3 正確跳過
- [ ] Job 4 (summary) 執行成功

### 完整測試

#### Private Repository

- [ ] Workflow 全部 jobs 執行成功
- [ ] 沒有錯誤或警告
- [ ] 執行時間合理（<10 分鐘）

#### Public Repository

- [ ] 代碼已同步
- [ ] 沒有 `private.yml` 文件
- [ ] 沒有 flag 洩漏
- [ ] Release Tag 已創建
- [ ] Commit 訊息正確
- [ ] 檔案結構正確

#### GitHub Pages

- [ ] Pages 部署成功
- [ ] 網站可以訪問
- [ ] 題目展示正常
- [ ] 無 404 錯誤
- [ ] 樣式和資源正常加載

---

## ❓ 常見問題

### Q1: Dry-run 測試需要多久？

**A**: 通常 2-5 分鐘，取決於：
- 題目數量
- 題目大小
- GitHub Actions 隊列狀況

### Q2: Dry-run 會創建任何內容嗎？

**A**: 不會！Dry-run 模式下：
- ❌ 不會推送到 Public Repository
- ❌ 不會創建 Tag
- ❌ 不會觸發 GitHub Pages
- ✅ 只會生成 Artifacts 供檢查

### Q3: 測試失敗了怎麼辦？

**A**:
1. 查看失敗的 job 日誌
2. 檢查錯誤訊息
3. 參考 [故障排除](#故障排除) 章節
4. 修復問題後重新測試

### Q4: 可以刪除測試產生的內容嗎？

**A**: 可以！
- **Public Repository**: 可以刪除測試 commits
  ```bash
  git reset --hard HEAD~1
  git push origin main --force
  ```
- **Release Tag**: 可以刪除
  ```bash
  git tag -d test-release-v1
  git push origin :refs/tags/test-release-v1
  ```
- **GitHub Pages**: 會自動更新

### Q5: 需要測試多少次？

**A**: 建議：
1. **首次配置**: Dry-run 1次 + 完整測試 1次
2. **有變更時**: Dry-run 1次（確認變更正確）
3. **正式發布前**: Dry-run 1次（最終檢查）

---

## 🔧 故障排除

### 問題 1: Job 1 失敗 - 安全掃描

**症狀**：
```
❌ 安全掃描發現 CRITICAL 問題，停止發布流程
```

**原因**：
- 題目中包含 flag
- 敏感檔案存在於 challenges/

**解決方案**：
1. 執行本地掃描：
   ```bash
   uv run python scripts/scan-secrets.py --path challenges/
   ```
2. 修復發現的問題
3. 確保 flag 只在 `private.yml` 中
4. 重新測試

---

### 問題 2: Job 2 失敗 - Bad credentials

**症狀**：
```
Error: Bad credentials
```

**原因**：
- `PUBLIC_REPO_TOKEN` 無效或過期
- Token 權限不足

**解決方案**：
1. 檢查 Token 是否有效
2. 重新創建 Token
3. 更新 Secret
4. 參考 [GitHub Secrets 配置指南](github-secrets-setup.md)

---

### 問題 3: Job 2 失敗 - Repository not found

**症狀**：
```
Error: Repository not found
```

**原因**：
- Target repository 不存在
- Repository 名稱拼寫錯誤
- Token 無權訪問 repository

**解決方案**：
1. 確認 Public Repository 存在
2. 檢查 repository 名稱格式：`owner/repo`
3. 確認 Token 可以訪問該 repository

---

### 問題 4: Job 3 失敗 - Workflow not found

**症狀**：
```
Error: Could not find workflow deploy-pages.yml
```

**原因**：
- Public Repository 缺少 `deploy-pages.yml` workflow
- Workflow 檔名不正確

**解決方案**：
1. 在 Public Repository 創建 `.github/workflows/deploy-pages.yml`
2. 參考 template 或現有的 Pages 部署 workflow
3. 確認 workflow 檔名正確

---

### 問題 5: GitHub Pages 未部署

**症狀**：
Workflow 成功但 Pages 沒有更新

**原因**：
- Pages 未啟用
- Pages 配置錯誤
- 部署 workflow 失敗

**解決方案**：
1. 前往 Public Repository **Settings** → **Pages**
2. 確認 Source 設為 "Deploy from a branch"
3. Branch 選擇 `main` / `(root)`
4. 檢查 Public Repository 的 Actions 是否有 Pages 部署記錄

---

### 問題 6: 執行時間過長

**症狀**：
Job 執行超過 10 分鐘

**原因**：
- 題目數量過多
- 題目檔案過大
- GitHub Actions runner 負載高

**解決方案**：
- 正常情況：耐心等待
- 優化題目大小
- 減少不必要的檔案

---

## 📊 測試報告模板

測試完成後，建議記錄測試結果：

```markdown
# Auto-Release 測試報告

## 測試資訊
- 測試日期：2025-12-12
- 測試者：Your Name
- 測試類型：Dry-run / 完整測試

## 配置資訊
- Private Repository: your-org/2025-is1ab-CTF
- Public Repository: your-org/2025-is1ab-CTF-public
- Release Tag: test-2025-12-12

## 測試結果

### Dry-run 測試
- [ ] ✅ Job 1: 準備發布版本（2分30秒）
- [ ] ✅ Job 2: 跳過（dry-run）
- [ ] ✅ Job 3: 跳過（dry-run）
- [ ] ✅ Job 4: 發布摘要（30秒）
- [ ] ✅ Artifacts 生成成功

### 完整測試
- [ ] ✅ Job 1: 準備發布版本（2分45秒）
- [ ] ✅ Job 2: 同步到公開 Repository（1分20秒）
- [ ] ✅ Job 3: 部署 GitHub Pages（45秒）
- [ ] ✅ Job 4: 發布摘要（30秒）

### 驗證結果
- [ ] ✅ Public Repository 內容正確
- [ ] ✅ 無 flag 洩漏
- [ ] ✅ GitHub Pages 部署成功
- [ ] ✅ 網站可正常訪問

## 問題與解決方案
（如有問題請記錄）

## 建議
（任何改進建議）

## 結論
✅ 測試通過 / ❌ 測試失敗

---
測試者簽名：__________
日期：__________
```

---

## 🔗 相關資源

### 內部文檔

- [自動化 Release 工作流程](../.github/workflows/auto-release.yml)
- [GitHub Secrets 配置指南](github-secrets-setup.md)
- [Branch Protection Rules 配置指南](branch-protection-setup.md)
- [改善實施指南](IMPROVEMENT_IMPLEMENTATION_GUIDE.md)

### 外部資源

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)

---

**維護者**: IS1AB Team
**最後更新**: 2025-12-12
**文檔版本**: v1.0
