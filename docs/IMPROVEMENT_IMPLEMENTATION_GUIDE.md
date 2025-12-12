# 🚀 CTF Template 改善建議實施指南

> **文檔版本**: v1.0
> **建立日期**: 2025-12-12
> **目的**: 根據專業建議優化現有流程、工具設計、安全性與自動化

---

## 📋 目錄

1. [改善建議總覽](#改善建議總覽)
2. [優先級分級](#優先級分級)
3. [詳細實施方案](#詳細實施方案)
4. [實施時程建議](#實施時程建議)
5. [驗證與測試](#驗證與測試)

---

## 🎯 改善建議總覽

### 現狀分析

**✅ 已實現的優秀功能**:
- 完整的安全掃描工具 (`scan-secrets.py`)
- GitHub Actions CI/CD 自動化
- 題目驗證與批量驗證工具
- 公開發布流程 (`sync-to-public.py`, `deploy-pages.yml`)
- Web 管理介面
- 詳細的文檔系統

**⚠️ 需要改進的關鍵點**:
1. Fork-based 工作流程過於複雜
2. Git Flow 標準化不夠明確
3. 角色權限管理可以更清晰
4. 自動化程度可以進一步提升
5. Metadata 標準化需要加強

---

## 🎚️ 優先級分級

### 🔴 P0 - 立即實施 (影響大、實施容易)

1. **取消 Private Fork 層，改用 Feature Branch 開發**
   - **影響**: 大幅簡化開發流程，減少 Git 操作錯誤
   - **實施難度**: 低
   - **預估時間**: 1-2 小時

2. **更新文檔中的工作流程說明**
   - **影響**: 避免新成員使用錯誤流程
   - **實施難度**: 低
   - **預估時間**: 2-3 小時

### 🟡 P1 - 短期實施 (2 週內)

3. **建立標準化 Git Flow 文檔**
   - **影響**: 統一團隊工作方式
   - **實施難度**: 低
   - **預估時間**: 3-4 小時

4. **優化角色權限管理文檔**
   - **影響**: 明確團隊分工與責任
   - **實施難度**: 低
   - **預估時間**: 2-3 小時

5. **增強 Metadata 標準化**
   - **影響**: 提升題目資料一致性
   - **實施難度**: 中
   - **預估時間**: 4-6 小時

### 🟢 P2 - 中期實施 (1 個月內)

6. **自動化 Release 流程**
   - **影響**: 減少手動操作，提高效率
   - **實施難度**: 中
   - **預估時間**: 6-8 小時

7. **Branch Protection Rules 自動化設定**
   - **影響**: 確保 PR 流程正確執行
   - **實施難度**: 低
   - **預估時間**: 1-2 小時

---

## 📖 詳細實施方案

---

## ✅ 方案 1: 取消 Private Fork，改用 Feature Branch

### 📌 問題分析

**現行流程的問題**:
```
Template Repo → Private Org Repo
                     ↓
               Personal Fork (❌ 不必要)
                     ↓
               Feature Branch
                     ↓
               PR to Private Org Repo
```

**問題點**:
- Fork 權限配置複雜（private → private fork 需要特殊權限）
- 需要管理 upstream 同步
- PR 從 fork 到 org repo 容易出錯
- 增加新成員的學習成本

### ✨ 改進方案

**新流程**:
```
Template Repo → Private Org Repo
                     ↓
            直接在 Org Repo 創建 Feature Branch
                     ↓
               PR to main
```

**優點**:
- ✅ 減少 Git 操作步驟
- ✅ 降低錯誤率
- ✅ 簡化權限管理
- ✅ 加快開發速度

### 🔧 實施步驟

#### Step 1: 更新 README.md

將 [README.md](../README.md) 第 389-409 行的內容替換為:

```markdown
### 👤 題目開發者：Feature Branch 開發流程

#### 1. 取得 Repository 存取權限

**前提條件**:
- 組織管理員已將您加入 Private Dev Repository
- 您擁有 **Write** 權限

**⚠️ 重要**: 不需要 Fork！直接在組織 Repository 中開發

```bash
# Clone 組織的 Private Repository
git clone https://github.com/your-org/2024-is1ab-CTF.git
cd 2024-is1ab-CTF

# 確認您在 main 分支並同步最新代碼
git checkout main
git pull origin main
```

#### 2. 創建 Feature Branch

```bash
# 題目創建腳本會自動創建 feature branch
uv run python scripts/create-challenge.py web my_challenge middle --author YourName

# 或手動創建 feature branch
git checkout -b challenge/web/my_challenge
```

#### 3. 開發題目

```bash
# 編輯題目檔案
# - challenges/web/my_challenge/public.yml
# - challenges/web/my_challenge/private.yml
# - challenges/web/my_challenge/src/
# - challenges/web/my_challenge/docker/
# - challenges/web/my_challenge/writeup/
```

#### 4. 提交變更

```bash
# 提交到 feature branch
git add challenges/web/my_challenge/
git commit -m "feat(web): add my_challenge - description

- 新增題目描述
- 難度：middle (200 points)
- 包含完整的 writeup 和測試環境"

# 推送到遠端
git push origin challenge/web/my_challenge
```

#### 5. 創建 Pull Request

在 GitHub 上創建 PR：
- **From**: `challenge/web/my_challenge`
- **To**: `main`
- **標題**: `feat(web): add my_challenge`
- 使用 [PR 模板](../.github/PULL_REQUEST_TEMPLATE.md)

#### 6. Code Review 與合併

- PR 會自動觸發 CI/CD 檢查
- 等待至少 1 位 Reviewer 審核
- 審核通過後合併到 main
```

#### Step 2: 更新其他文檔

需要更新的文檔列表:
- [ ] [docs/git-workflow-guide.md](git-workflow-guide.md)
- [ ] [docs/quick-start-guide.md](quick-start-guide.md)
- [ ] [docs/getting-started.md](getting-started.md)
- [ ] [docs/workflow-tutorial.md](workflow-tutorial.md)

#### Step 3: 團隊溝通

1. **公告變更**:
   ```markdown
   📢 重要公告：工作流程變更

   從即日起，我們改用更簡單的 Feature Branch 工作流程：
   - ❌ 不再需要 Fork Private Repository
   - ✅ 直接在組織 Repository 中創建 Feature Branch
   - ✅ 簡化 Git 操作，減少錯誤

   詳細說明請參閱：[改善實施指南](docs/IMPROVEMENT_IMPLEMENTATION_GUIDE.md)
   ```

2. **培訓材料**: 提供簡短的教學影片或文檔

3. **過渡期支援**: 設立 Q&A 時段協助團隊成員適應

---

## ✅ 方案 2: 建立標準化 Git Flow

### 📌 目標

建立清晰、統一的 Git 分支管理標準

### 🌿 分支命名規範

```
main                          # 主分支，保護分支
├── challenge/<category>/<name>   # 題目開發分支
├── feature/<feature-name>        # 功能開發分支
├── fix/<bug-description>         # Bug 修復分支
├── docs/<doc-name>              # 文檔更新分支
└── release/<version>            # 發布分支（可選）
```

**範例**:
```bash
challenge/web/sql-injection
challenge/pwn/buffer-overflow
feature/web-gui-enhancement
fix/validate-script-error
docs/update-security-guide
release/2025-01-final
```

### 📝 Commit Message 規範

採用 [Conventional Commits](https://www.conventionalcommits.org/) 格式:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 類型**:
- `feat`: 新功能（新題目）
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 格式調整（不影響代碼運行）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 雜項（依賴更新、配置調整）

**範例**:
```bash
feat(web): add sql-injection challenge

- 新增 SQL 注入基礎題目
- 難度：middle (200 points)
- 包含完整的 writeup 和測試環境
- Docker 部署支援

Closes #123
```

### 🔒 Branch Protection Rules

**main 分支保護規則**:
```yaml
Branch protection rules for 'main':
  ✅ Require pull request before merging
    - Require 1 approval
    - Dismiss stale reviews when new commits are pushed
  ✅ Require status checks to pass
    - validate-challenge
    - security-scan
    - docker-build (if applicable)
  ✅ Require conversation resolution before merging
  ✅ Include administrators
  ✅ Do not allow bypassing the above settings
```

---

## ✅ 方案 3: 優化角色權限管理

### 👥 團隊角色定義

| 角色 | GitHub 權限 | 職責 | 人數建議 |
|------|------------|------|---------|
| **Admin** | Admin | - 管理 Repository 設定<br>- 配置 Branch Protection<br>- 管理團隊成員<br>- 處理緊急問題 | 2-3 人 |
| **Maintainer** | Maintain | - 審核 PR<br>- 合併代碼<br>- 管理 Issues<br>- 協調開發進度 | 3-5 人 |
| **Developer** | Write | - 創建 Feature Branch<br>- 提交題目<br>- 參與 Code Review | 10-20 人 |
| **Reviewer** | Triage | - Code Review<br>- 測試題目<br>- 提供反饋 | 5-10 人 |
| **Guest** | Read | - 查看進度<br>- 瀏覽代碼（僅限已授權） | 不限 |

### 🔐 權限分配指南

**新成員加入流程**:
1. Admin 將成員加入組織
2. 根據角色分配權限
3. 提供 [新手入門指南](getting-started.md)
4. 安排 Onboarding 會議

**權限調整**:
- 定期審查（每季度）
- 根據貢獻度調整
- 離職人員立即移除

---

## ✅ 方案 4: 自動化 Release 流程

### 🎯 目標

實現從 Private Repo 到 Public Repo 的全自動發布

### 🔄 自動化流程

```mermaid
graph LR
    A[比賽結束] --> B[創建 Release Tag]
    B --> C[觸發 auto-release.yml]
    C --> D[執行 build.sh]
    D --> E[安全掃描]
    E --> F[同步到 Public Repo]
    F --> G[生成 GitHub Pages]
    G --> H[發布完成]
```

### 📄 實施方案

創建 `.github/workflows/auto-release.yml`:

```yaml
name: 🚀 Auto Release to Public

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      release_tag:
        description: 'Release tag (e.g., 2025-01-final)'
        required: true
      target_repo:
        description: 'Target public repository'
        required: true
        default: 'your-org/2025-is1ab-CTF-public'

permissions:
  contents: write
  actions: write

jobs:
  prepare-release:
    name: 📦 準備公開發布版本
    runs-on: ubuntu-latest

    steps:
      - name: 📥 Checkout Private Repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 🐍 Setup Python with uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: 📦 Install Dependencies
        run: |
          uv venv
          uv pip install -r requirements.txt

      - name: 🔒 Security Scan
        run: |
          echo "🔒 執行最終安全掃描..."
          uv run python scripts/scan-secrets.py \
            --path challenges/ \
            --format markdown \
            --output pre-release-scan.md \
            --fail-on-critical

      - name: 🏗️ Build Public Release
        run: |
          echo "🏗️ 建置公開版本..."
          uv run python scripts/prepare-public-release.py \
            --event-date ${{ github.event.inputs.release_tag || github.event.release.tag_name }}

      - name: 🔍 Validate Public Release
        run: |
          echo "🔍 驗證公開版本..."
          uv run python scripts/validate-all-challenges.py \
            --path public-release/challenges/

      - name: 📤 Upload Release Artifact
        uses: actions/upload-artifact@v4
        with:
          name: public-release
          path: public-release/
          retention-days: 30

  sync-to-public:
    name: 📡 同步到公開 Repository
    runs-on: ubuntu-latest
    needs: prepare-release

    steps:
      - name: 📥 Download Release Artifact
        uses: actions/download-artifact@v4
        with:
          name: public-release
          path: public-release/

      - name: 🔐 Setup Git Credentials
        run: |
          git config --global user.name "IS1AB Bot"
          git config --global user.email "bot@is1ab.org"

      - name: 📡 Sync to Public Repository
        env:
          GITHUB_TOKEN: ${{ secrets.PUBLIC_REPO_TOKEN }}
        run: |
          TARGET_REPO="${{ github.event.inputs.target_repo || 'your-org/2025-is1ab-CTF-public' }}"

          echo "📡 同步到公開 Repository: $TARGET_REPO"

          # Clone public repo
          git clone https://x-access-token:${GITHUB_TOKEN}@github.com/${TARGET_REPO}.git public-repo
          cd public-repo

          # Copy files
          cp -r ../public-release/* .

          # Commit and push
          git add .
          git commit -m "chore: release ${{ github.event.inputs.release_tag || github.event.release.tag_name }}

          🤖 Automatically generated from private repository

          Release Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
          Release Tag: ${{ github.event.inputs.release_tag || github.event.release.tag_name }}"

          git push origin main

      - name: 🌐 Trigger GitHub Pages Deploy
        env:
          GITHUB_TOKEN: ${{ secrets.PUBLIC_REPO_TOKEN }}
        run: |
          TARGET_REPO="${{ github.event.inputs.target_repo || 'your-org/2025-is1ab-CTF-public' }}"

          echo "🌐 觸發 GitHub Pages 部署..."

          # Trigger deploy-pages.yml in public repo
          curl -X POST \
            -H "Accept: application/vnd.github.v3+json" \
            -H "Authorization: token ${GITHUB_TOKEN}" \
            https://api.github.com/repos/${TARGET_REPO}/actions/workflows/deploy-pages.yml/dispatches \
            -d '{"ref":"main"}'

  create-release-notes:
    name: 📝 生成 Release Notes
    runs-on: ubuntu-latest
    needs: sync-to-public

    steps:
      - name: 📥 Checkout
        uses: actions/checkout@v4

      - name: 📊 Generate Statistics
        run: |
          echo "📊 生成題目統計..."

          # 統計題目數量
          TOTAL=$(find challenges/ -name "public.yml" | wc -l)
          WEB=$(find challenges/web/ -name "public.yml" 2>/dev/null | wc -l)
          PWN=$(find challenges/pwn/ -name "public.yml" 2>/dev/null | wc -l)
          CRYPTO=$(find challenges/crypto/ -name "public.yml" 2>/dev/null | wc -l)

          # 生成 Release Notes
          cat > release-notes.md << EOF
          # IS1AB CTF ${{ github.event.inputs.release_tag || github.event.release.tag_name }}

          ## 📊 題目統計

          - 總題目數: **${TOTAL}** 題
          - Web: ${WEB} 題
          - Pwn: ${PWN} 題
          - Crypto: ${CRYPTO} 題

          ## 🔗 連結

          - 📖 題目展示: https://your-org.github.io/2025-is1ab-CTF-public
          - 📦 公開 Repository: https://github.com/${{ github.event.inputs.target_repo || 'your-org/2025-is1ab-CTF-public' }}

          ## 🎉 感謝

          感謝所有題目作者與貢獻者！
          EOF

          cat release-notes.md

      - name: 📝 Post to Discussion
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const notes = fs.readFileSync('release-notes.md', 'utf8');

            github.rest.repos.createRelease({
              owner: context.repo.owner,
              repo: context.repo.repo,
              tag_name: '${{ github.event.inputs.release_tag || github.event.release.tag_name }}',
              name: 'Release ${{ github.event.inputs.release_tag || github.event.release.tag_name }}',
              body: notes,
              draft: false,
              prerelease: false
            });
```

---

## ✅ 方案 5: 增強 Metadata 標準化

### 🎯 目標

統一題目 Metadata 格式，方便自動化處理

### 📋 標準 Metadata 格式

更新 `challenge-template/public.yml.template`:

```yaml
# =============================================================================
# CTF Challenge Metadata - Public Information
# =============================================================================

# 基本資訊
challenge:
  name: "{{CHALLENGE_NAME}}"          # 題目名稱（英文，用於系統識別）
  display_name: "{{DISPLAY_NAME}}"    # 顯示名稱（可中英文，用於前端顯示）
  category: "{{CATEGORY}}"            # 類別: web/pwn/crypto/reverse/misc/forensics/blockchain
  difficulty: "{{DIFFICULTY}}"        # 難度: baby/easy/middle/hard/insane

  # 分數與標籤
  points: {{POINTS}}                  # 基礎分數
  dynamic_scoring: false              # 是否啟用動態計分
  tags:                               # 題目標籤（用於分類與搜尋）
    - "{{TAG1}}"
    - "{{TAG2}}"

  # 作者資訊
  authors:
    - name: "{{AUTHOR_NAME}}"
      github: "{{GITHUB_USERNAME}}"   # 可選
      email: "{{EMAIL}}"              # 可選

# 題目描述
description:
  zh_TW: |
    {{DESCRIPTION_ZH}}
  en_US: |
    {{DESCRIPTION_EN}}

# 提示系統（可選）
hints:
  - cost: 50                          # 提示代價（扣分）
    content:
      zh_TW: "{{HINT1_ZH}}"
      en_US: "{{HINT1_EN}}"
  - cost: 100
    content:
      zh_TW: "{{HINT2_ZH}}"
      en_US: "{{HINT2_EN}}"

# 附件資訊
files:
  provided:                           # 提供給參賽者的檔案
    - name: "challenge.zip"
      path: "files/challenge.zip"
      description: "題目附件"
      size: "1.2 MB"                  # 自動計算
      sha256: "auto"                  # 自動計算

# 部署資訊
deployment:
  type: "docker"                      # none/docker/static/remote
  docker:
    enabled: true
    compose_file: "docker/docker-compose.yml"
    port: 8080
    internal_port: 80
  connection:
    protocol: "http"                  # http/https/tcp/nc
    host: "challenge.is1ab.com"       # 部署後填寫
    port: 8080

# 平台整合
platform:
  ctfd:
    category: "{{CATEGORY}}"
    type: "standard"                  # standard/dynamic
    state: "visible"                  # visible/hidden
    requirements: []                  # 前置題目 ID

  rctf:
    category: "{{CATEGORY}}"
    detail: "auto"                    # 自動生成或自訂

# Metadata 版本
metadata_version: "2.0"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
```

### 🔧 驗證工具增強

更新 `scripts/validate-challenge.py` 以支援新的 Metadata 格式:

```python
def validate_metadata(public_yml: dict) -> List[str]:
    """驗證 Metadata 完整性"""
    errors = []

    # 必填欄位檢查
    required_fields = {
        'challenge.name': str,
        'challenge.category': str,
        'challenge.difficulty': str,
        'challenge.points': int,
        'challenge.authors': list,
        'description.zh_TW': str,
        'metadata_version': str,
    }

    for field_path, expected_type in required_fields.items():
        value = get_nested_value(public_yml, field_path)
        if value is None:
            errors.append(f"缺少必填欄位: {field_path}")
        elif not isinstance(value, expected_type):
            errors.append(f"欄位類型錯誤: {field_path} 應為 {expected_type.__name__}")

    # 類別檢查
    valid_categories = {'web', 'pwn', 'crypto', 'reverse', 'misc', 'forensics', 'blockchain'}
    if public_yml.get('challenge', {}).get('category') not in valid_categories:
        errors.append(f"無效的類別，必須是: {valid_categories}")

    # 難度檢查
    valid_difficulties = {'baby', 'easy', 'middle', 'hard', 'insane'}
    if public_yml.get('challenge', {}).get('difficulty') not in valid_difficulties:
        errors.append(f"無效的難度，必須是: {valid_difficulties}")

    return errors
```

---

## 📅 實施時程建議

### Week 1: 立即改善（P0）
- [ ] Day 1-2: 更新 README.md 工作流程說明
- [ ] Day 3-4: 更新相關文檔（git-workflow-guide, quick-start-guide）
- [ ] Day 5: 團隊公告與培訓

### Week 2-3: 短期改善（P1）
- [ ] Week 2: 建立 Git Flow 標準文檔
- [ ] Week 2: 優化角色權限文檔
- [ ] Week 3: 增強 Metadata 標準化
- [ ] Week 3: 更新驗證工具

### Week 4: 中期改善（P2）
- [ ] Week 4: 實施自動化 Release 流程
- [ ] Week 4: 配置 Branch Protection Rules
- [ ] Week 4: 測試與驗證

---

## ✅ 驗證與測試

### 測試清單

#### 工作流程測試
- [ ] 新成員能否順利 Clone Repository
- [ ] Feature Branch 創建與提交是否順暢
- [ ] PR 流程是否正確觸發 CI/CD
- [ ] Code Review 流程是否順暢
- [ ] Merge 後是否自動清理 Branch

#### 自動化測試
- [ ] Security Scan 是否正確檢測問題
- [ ] 題目驗證是否通過
- [ ] Docker Build 是否成功
- [ ] Release 流程是否完整執行
- [ ] GitHub Pages 是否正確部署

#### 文檔測試
- [ ] 新成員能否根據文檔快速上手
- [ ] 所有連結是否有效
- [ ] 範例代碼是否可執行
- [ ] 文檔是否易於理解

---

## 📞 支援與回饋

### 問題回報

如在實施過程中遇到問題，請：
1. 查閱 [FAQ](faq.md)
2. 在 [GitHub Issues](https://github.com/is1ab/is1ab-CTF-template/issues) 回報
3. 聯繫團隊管理員

### 改善建議

歡迎提供改善建議：
- 📝 開啟 [GitHub Discussion](https://github.com/is1ab/is1ab-CTF-template/discussions)
- 💡 提交 [Feature Request](https://github.com/is1ab/is1ab-CTF-template/issues/new?template=feature_request.md)

---

## 📚 相關文檔

- [5 分鐘快速入門](getting-started.md)
- [Git 操作教學](git-workflow-guide.md)
- [安全流程完整指南](security-workflow-guide.md)
- [角色與權限管理](roles-and-permissions.md)
- [快速參考指南](quick-reference.md)

---

**維護者**: IS1AB Team
**最後更新**: 2025-12-12
**文檔版本**: v1.0
