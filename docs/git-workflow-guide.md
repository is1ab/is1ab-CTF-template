# 📚 Git 操作完整教學

> 從零開始學習 Git 和 GitHub 操作，包含建立 repo、fork、push、commit 等完整流程

## 📋 目錄

- [前置準備](#前置準備)
- [GitHub 基本操作](#github-基本操作)
- [本地 Git 操作](#本地-git-操作)
- [完整開發流程](#完整開發流程)
- [常見問題](#常見問題)
- [進階技巧](#進階技巧)

---

## 前置準備

### 1. 安裝 Git

#### macOS

```bash
# 使用 Homebrew
brew install git

# 或下載安裝程式
# https://git-scm.com/download/mac
```

#### Windows

```bash
# 下載 Git for Windows
# https://git-scm.com/download/win

# 或使用 Chocolatey
choco install git
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git

# CentOS/RHEL
sudo yum install git

# Fedora
sudo dnf install git
```

### 2. 配置 Git

```bash
# 設定使用者名稱和信箱（首次使用必須設定）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 設定預設分支名稱
git config --global init.defaultBranch main

# 設定編輯器（可選）
git config --global core.editor "vim"  # 或 "code --wait" (VS Code)

# 查看配置
git config --list
```

### 3. 設定 SSH Key（推薦）

```bash
# 生成 SSH Key
ssh-keygen -t ed25519 -C "your.email@example.com"

# 按 Enter 使用預設路徑
# 設定密碼（可選，建議設定）

# 複製公鑰
cat ~/.ssh/id_ed25519.pub

# 在 GitHub 上添加 SSH Key
# Settings → SSH and GPG keys → New SSH key
# 貼上公鑰內容
```

### 4. 測試連線

```bash
# 測試 SSH 連線
ssh -T git@github.com

# 應該看到：
# Hi username! You've successfully authenticated...
```

---

## GitHub 基本操作

### 1. 建立 Repository

#### 方法 A：使用 Template（推薦）

1. **前往 Template Repository**

   ```
   https://github.com/is1ab/is1ab-CTF-template
   ```

2. **點擊 "Use this template"**

   - 選擇 "Create a new repository"

3. **填寫 Repository 資訊**

   ```
   Repository name: 2024-is1ab-CTF-private
   Description: IS1AB CTF 2024 - Private Development Repository
   Visibility: Private ✅
   Include all branches: ✅
   ```

4. **點擊 "Create repository"**

#### 方法 B：手動建立

1. **點擊右上角 "+" → "New repository"**

2. **填寫資訊**

   ```
   Repository name: 2024-is1ab-CTF-private
   Description: IS1AB CTF 2024 - Private Development Repository
   Visibility: Private ✅
   Initialize with README: ❌（如果使用 template）
   Add .gitignore: None（template 已包含）
   Choose a license: MIT（可選）
   ```

3. **點擊 "Create repository"**

### 2. Fork Repository

#### 何時需要 Fork？

- 您沒有直接寫入權限
- 想要在自己的帳號下開發
- 需要提交 Pull Request

#### Fork 步驟

1. **前往要 Fork 的 Repository**

   ```
   https://github.com/is1ab/2024-is1ab-CTF-private
   ```

2. **點擊右上角 "Fork"**

3. **選擇目標帳號/組織**

   - 選擇您的個人帳號或組織

4. **確認 Fork**

   - 等待 Fork 完成

5. **Clone Fork 的 Repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/2024-is1ab-CTF-private.git
   cd 2024-is1ab-CTF-private
   ```

### 3. 設定 Repository 權限

#### 組織管理員設定

1. **前往 Repository Settings**

   ```
   Settings → Manage access
   ```

2. **添加協作者**

   ```
   Invite a collaborator
   - Admin: 核心團隊 (3-5人)
   - Write: 題目開發者 (10-20人)
   - Read: 審查者
   ```

3. **設定分支保護**

   ```
   Settings → Branches → Add protection rule
   Branch name pattern: main

   保護規則：
   ✅ Require pull request reviews before merging
      - Required number of approvals: 1
   ✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
   ✅ Include administrators
   ```

### 4. 啟用 GitHub Pages

1. **前往 Repository Settings**

   ```
   Settings → Pages
   ```

2. **設定 Source**

   ```
   Source: Deploy from a branch
   Branch: main
   Folder: / (root)
   ```

3. **儲存設定**
   - GitHub Pages 會自動部署

---

## 本地 Git 操作

### 1. Clone Repository

#### HTTPS 方式（簡單）

```bash
# Clone 公開 Repository
git clone https://github.com/is1ab/is1ab-CTF-template.git
cd is1ab-CTF-template

# Clone 私有 Repository（需要認證）
git clone https://github.com/your-org/2024-is1ab-CTF-private.git
cd 2024-is1ab-CTF-private
```

#### SSH 方式（推薦）

```bash
# Clone 公開 Repository
git clone git@github.com:is1ab/is1ab-CTF-template.git
cd is1ab-CTF-template

# Clone 私有 Repository
git clone git@github.com:your-org/2024-is1ab-CTF-private.git
cd 2024-is1ab-CTF-private
```

### 2. 基本 Git 命令

#### 查看狀態

```bash
# 查看檔案狀態
git status

# 簡潔狀態
git status -s

# 查看變更內容
git diff

# 查看已暫存的變更
git diff --staged
```

#### 添加檔案

```bash
# 添加單一檔案
git add README.md

# 添加整個目錄
git add challenges/

# 添加所有變更
git add .

# 互動式添加（選擇性添加）
git add -p
```

#### 提交變更

```bash
# 基本提交
git commit -m "Add new challenge"

# 詳細提交訊息
git commit -m "feat(web): add SQL injection challenge

- Add SQL injection challenge
- Include Docker configuration
- Add writeup and hints
- Difficulty: easy, Points: 100"

# 修改最後一次提交（未 push）
git commit --amend -m "New commit message"

# 添加檔案到上次提交
git add forgotten_file.py
git commit --amend --no-edit
```

#### 查看歷史

```bash
# 查看提交歷史
git log

# 簡潔歷史
git log --oneline

# 圖形化歷史
git log --graph --oneline --all

# 查看特定檔案的歷史
git log -- challenges/web/sql_injection/

# 查看變更統計
git log --stat
```

### 3. 分支操作

#### 建立和切換分支

```bash
# 建立新分支
git branch feature/my-challenge

# 切換分支
git checkout feature/my-challenge

# 建立並切換分支（一步完成）
git checkout -b feature/my-challenge

# 或使用新語法（Git 2.23+）
git switch -c feature/my-challenge

# 查看所有分支
git branch -a

# 查看遠端分支
git branch -r
```

#### 合併分支

```bash
# 切換到目標分支
git checkout main

# 合併分支
git merge feature/my-challenge

# 合併後刪除分支
git branch -d feature/my-challenge

# 強制刪除分支（未合併）
git branch -D feature/my-challenge
```

#### 解決衝突

```bash
# 當合併發生衝突時
git merge feature/my-challenge

# 查看衝突檔案
git status

# 編輯衝突檔案
# 尋找 <<<<<<< ======= >>>>>>> 標記
# 手動解決衝突

# 標記為已解決
git add resolved_file.py

# 完成合併
git commit
```

### 4. 遠端操作

#### 查看遠端

```bash
# 查看遠端 Repository
git remote -v

# 查看詳細資訊
git remote show origin
```

#### 添加遠端

```bash
# 添加 upstream（原始 Repository）
git remote add upstream https://github.com/is1ab/2024-is1ab-CTF-private.git

# 添加多個遠端
git remote add personal https://github.com/your-username/2024-is1ab-CTF-private.git
```

#### Push 推送

```bash
# 推送到 origin
git push origin main

# 推送到特定分支
git push origin feature/my-challenge

# 設定上游分支（首次推送）
git push -u origin feature/my-challenge

# 強制推送（謹慎使用！）
git push --force origin main

# 推送所有分支
git push --all origin

# 推送標籤
git push --tags
```

#### Pull 拉取

```bash
# 拉取並合併
git pull origin main

# 只拉取不合併
git fetch origin

# 拉取後查看變更
git fetch origin
git log origin/main..HEAD

# 合併遠端變更
git merge origin/main
```

### 5. 同步 Fork

```bash
# 1. 添加 upstream
git remote add upstream https://github.com/is1ab/2024-is1ab-CTF-private.git

# 2. 拉取 upstream 變更
git fetch upstream

# 3. 切換到 main 分支
git checkout main

# 4. 合併 upstream/main
git merge upstream/main

# 5. 推送到自己的 Fork
git push origin main
```

---

## 完整開發流程

### 場景 1：建立新題目

#### 步驟 1：準備工作

```bash
# 1. Clone Repository（如果還沒有）
git clone git@github.com:your-org/2024-is1ab-CTF-private.git
cd 2024-is1ab-CTF-private

# 2. 確保 main 分支是最新的
git checkout main
git pull origin main

# 3. 建立功能分支
git checkout -b challenge/web/sql_injection
```

#### 步驟 2：開發題目

```bash
# 1. 建立題目（使用腳本或 Web GUI）
uv run python scripts/create-challenge.py web sql_injection easy --author YourName

# 2. 編輯題目檔案
vim challenges/web/sql_injection/private.yml
vim challenges/web/sql_injection/public.yml

# 3. 查看變更
git status
git diff
```

#### 步驟 3：提交變更

```bash
# 1. 添加變更
git add challenges/web/sql_injection/

# 2. 提交
git commit -m "feat(web): add SQL injection challenge

- Add SQL injection challenge
- Difficulty: easy, Points: 100
- Include Docker configuration
- Add hints and writeup"

# 3. 推送到遠端
git push -u origin challenge/web/sql_injection
```

#### 步驟 4：建立 Pull Request

1. **前往 GitHub**

   ```
   https://github.com/your-org/2024-is1ab-CTF-private
   ```

2. **點擊 "Compare & pull request"**

   - 或點擊 "Pull requests" → "New pull request"

3. **選擇分支**

   ```
   base: main ← compare: challenge/web/sql_injection
   ```

4. **填寫 PR 資訊**

   ```markdown
   ## 📋 變更內容

   - [x] 新增題目

   ## 🎯 題目資訊

   **題目名稱**: SQL Injection
   **分類**: Web
   **難度**: easy
   **分數**: 100

   ## 📝 變更說明

   新增一個簡單的 SQL 注入題目，適合初學者學習基本的注入技巧。

   ## ✅ 檢查清單

   - [x] 本地測試通過
   - [x] Docker 建構成功
   - [x] 安全掃描通過
   - [x] Writeup 已完成
   ```

5. **提交 PR**
   - 等待審查和 CI/CD 檢查

#### 步驟 5：處理審查意見

```bash
# 1. 切換到分支
git checkout challenge/web/sql_injection

# 2. 修改檔案
vim challenges/web/sql_injection/public.yml

# 3. 提交修改
git add challenges/web/sql_injection/public.yml
git commit -m "fix(web): update challenge description based on review"

# 4. 推送更新
git push origin challenge/web/sql_injection
# PR 會自動更新
```

#### 步驟 6：合併後清理

```bash
# 1. 切換到 main
git checkout main

# 2. 拉取最新變更
git pull origin main

# 3. 刪除本地分支
git branch -d challenge/web/sql_injection

# 4. 刪除遠端分支（可選）
git push origin --delete challenge/web/sql_injection
```

### 場景 2：更新現有題目

```bash
# 1. 建立更新分支
git checkout -b fix/web/sql_injection-description

# 2. 修改檔案
vim challenges/web/sql_injection/public.yml

# 3. 提交變更
git add challenges/web/sql_injection/public.yml
git commit -m "fix(web): improve SQL injection challenge description"

# 4. 推送
git push -u origin fix/web/sql_injection-description

# 5. 建立 PR
```

### 場景 3：同步團隊變更

```bash
# 1. 查看遠端變更
git fetch origin

# 2. 查看變更內容
git log origin/main..HEAD  # 本地有但遠端沒有的
git log HEAD..origin/main  # 遠端有但本地沒有的

# 3. 拉取並合併
git pull origin main

# 4. 如果有衝突，解決後提交
git add .
git commit -m "merge: resolve conflicts"
```

---

## 常見問題

### 1. 忘記設定 upstream

```bash
# 問題：無法 pull 或 push
# 解決：設定 upstream
git branch --set-upstream-to=origin/main main
```

### 2. 提交到錯誤分支

```bash
# 問題：在 main 分支提交了變更
# 解決：移動提交到新分支
git branch feature/my-challenge
git reset --hard origin/main
git checkout feature/my-challenge
```

### 3. 想要撤銷提交

```bash
# 撤銷最後一次提交（保留變更）
git reset --soft HEAD~1

# 撤銷最後一次提交（不保留變更）
git reset --hard HEAD~1

# 撤銷已 push 的提交（謹慎！）
git revert HEAD
git push origin main
```

### 4. 想要修改提交訊息

```bash
# 修改最後一次提交訊息（未 push）
git commit --amend -m "New commit message"

# 修改已 push 的提交訊息（需要 force push）
git commit --amend -m "New commit message"
git push --force origin main  # ⚠️ 謹慎使用！
```

### 5. 想要恢復刪除的檔案

```bash
# 查看刪除的檔案
git log --diff-filter=D --summary

# 恢復檔案
git checkout HEAD~1 -- path/to/file

# 或恢復到特定提交
git checkout <commit-hash> -- path/to/file
```

### 6. 想要清理未追蹤的檔案

```bash
# 查看未追蹤的檔案
git clean -n

# 刪除未追蹤的檔案
git clean -f

# 刪除未追蹤的檔案和目錄
git clean -fd
```

### 7. 想要暫存變更

```bash
# 暫存當前變更
git stash

# 暫存並添加訊息
git stash save "Work in progress"

# 查看暫存列表
git stash list

# 恢復暫存
git stash pop

# 恢復特定暫存
git stash apply stash@{0}

# 刪除暫存
git stash drop stash@{0}
```

### 8. 想要查看特定檔案的變更歷史

```bash
# 查看檔案歷史
git log -- challenges/web/sql_injection/public.yml

# 查看檔案的詳細變更
git log -p -- challenges/web/sql_injection/public.yml

# 查看誰修改了檔案
git blame challenges/web/sql_injection/public.yml
```

---

## 進階技巧

### 1. Git Hooks

#### 建立 Pre-commit Hook

```bash
# 建立 hook 檔案
vim .git/hooks/pre-commit

# 內容範例
#!/bin/bash
# 執行安全掃描
uv run python scripts/scan-secrets.py --path challenges/
if [ $? -ne 0 ]; then
    echo "❌ 安全掃描失敗，提交已取消"
    exit 1
fi

# 執行題目驗證
uv run python scripts/validate-challenge.py challenges/
if [ $? -ne 0 ]; then
    echo "❌ 題目驗證失敗，提交已取消"
    exit 1
fi

echo "✅ 檢查通過"
exit 0

# 設定執行權限
chmod +x .git/hooks/pre-commit
```

### 2. Git Aliases

```bash
# 設定常用別名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'

# 使用別名
git st    # 等同 git status
git co main  # 等同 git checkout main
```

### 3. 互動式 Rebase

```bash
# 修改最近 3 次提交
git rebase -i HEAD~3

# 在編輯器中：
# pick → 保留提交
# edit → 編輯提交
# squash → 合併到上一個提交
# drop → 刪除提交

# 完成後
git push --force origin branch-name  # ⚠️ 謹慎使用！
```

### 4. 子模組（Submodules）

```bash
# 添加子模組
git submodule add https://github.com/user/repo.git path/to/submodule

# Clone 包含子模組的 Repository
git clone --recursive https://github.com/user/repo.git

# 更新子模組
git submodule update --remote
```

### 5. 標籤（Tags）

```bash
# 建立標籤
git tag v1.0.0

# 建立帶訊息的標籤
git tag -a v1.0.0 -m "Release version 1.0.0"

# 查看標籤
git tag

# 推送標籤
git push origin v1.0.0

# 推送所有標籤
git push --tags
```

---

## 最佳實踐

### 1. 提交訊息規範

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**範例：**

```
feat(web): add SQL injection challenge

Add a new SQL injection challenge for beginners.
Includes Docker configuration and writeup.

Closes #123
```

**Type 類型：**

- `feat`: 新功能
- `fix`: 修復問題
- `docs`: 文檔變更
- `style`: 格式變更
- `refactor`: 重構
- `test`: 測試
- `chore`: 雜項

### 2. 分支命名規範

```
<type>/<category>/<name>

範例：
- challenge/web/sql_injection
- fix/pwn/buffer_overflow
- docs/update-readme
- refactor/scripts/build
```

### 3. 工作流程建議

1. **總是從 main 分支建立新分支**

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/new-feature
   ```

2. **頻繁提交，小步前進**

   ```bash
   # ✅ 好的做法
   git commit -m "Add challenge structure"
   git commit -m "Add Docker configuration"
   git commit -m "Add writeup"

   # ❌ 不好的做法
   git commit -m "Complete challenge"  # 一次提交所有變更
   ```

3. **提交前檢查**

   ```bash
   git status
   git diff
   git log --oneline -5
   ```

4. **Push 前 Pull**
   ```bash
   git pull origin main
   git push origin feature/branch
   ```

---

## 快速參考

### 常用命令速查

```bash
# 初始化
git init
git clone <url>

# 基本操作
git status
git add <file>
git commit -m "message"
git push
git pull

# 分支操作
git branch
git checkout <branch>
git checkout -b <new-branch>
git merge <branch>

# 查看歷史
git log
git log --oneline
git log --graph --all

# 撤銷操作
git reset HEAD~1
git revert HEAD
git checkout -- <file>

# 遠端操作
git remote -v
git remote add <name> <url>
git fetch
git push origin <branch>
git pull origin <branch>
```

---

## 總結

### 基本工作流程

```
1. git clone <repository>
2. git checkout -b feature/branch
3. 進行開發
4. git add .
5. git commit -m "message"
6. git push origin feature/branch
7. 在 GitHub 建立 Pull Request
8. 審查和合併
9. git checkout main
10. git pull origin main
```

### 重要提醒

- ✅ 提交前總是檢查 `git status` 和 `git diff`
- ✅ 使用有意義的提交訊息
- ✅ 頻繁提交，小步前進
- ✅ 不要 force push 到 main 分支
- ✅ 使用分支進行開發
- ✅ 定期同步遠端變更

---

**最後更新**：2025-01-XX  
**版本**：1.0.0  
**維護者**：IS1AB Team
