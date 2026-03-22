# Git 操作速查表

> 只列出 CTF 題目開發需要的 Git 操作。不多不少。

---

## 日常開發流程

```bash
# 1. 確保在最新的 main 上
git checkout main
git pull origin main

# 2. 建立題目分支（或用 create-challenge.py 自動建立）
git checkout -b challenge/web/my_challenge

# 3. 開發題目...（編輯檔案）

# 4. 查看目前改了什麼
git status

# 5. 加入變更
git add challenges/web/my_challenge/

# 6. 提交
git commit -m "feat(web): add my_challenge"

# 7. 推送到遠端
git push -u origin challenge/web/my_challenge

# 8. 去 GitHub 建立 Pull Request
```

---

## 分支命名規範

| 用途 | 格式 | 範例 |
|---|---|---|
| 新題目 | `challenge/<category>/<name>` | `challenge/web/sql_injection` |
| 修復 | `fix/<描述>` | `fix/typo-in-readme` |
| 文件 | `docs/<描述>` | `docs/add-setup-guide` |
| 功能 | `feature/<描述>` | `feature/auto-deploy` |

---

## Commit 訊息格式

```
<type>(<scope>): <描述>

type: feat, fix, docs, refactor, test, chore
scope: web, pwn, crypto, reverse, misc, ci, docs
```

範例：

```bash
git commit -m "feat(crypto): add rsa_beginner challenge"
git commit -m "fix(web): fix SQL injection docker port"
git commit -m "docs: update getting started guide"
```

---

## 常見操作

### 更新你的分支到最新

```bash
git checkout main
git pull origin main
git checkout challenge/web/my_challenge
git merge main
```

### 修改最後一次 commit

```bash
# 修改 commit 訊息
git commit --amend -m "feat(web): better commit message"

# 加入遺漏的檔案（不改訊息）
git add forgotten-file.py
git commit --amend --no-edit
```

### 撤銷還沒 commit 的修改

```bash
# 撤銷單個檔案
git checkout -- path/to/file

# 撤銷所有修改（小心！）
git checkout -- .
```

### 分支名稱打錯了

```bash
# 重新命名本地分支
git branch -m challenge/web/correct_name

# 如果已經推送，刪除遠端舊分支再推新的
git push origin --delete old-branch-name
git push -u origin challenge/web/correct_name
```

---

## 遇到問題？

| 情境 | 解法 |
|---|---|
| Commit 被 hook 擋住 | `make scan` 找出問題 → 修正 → 重新 commit |
| Push 被拒絕 | `git pull --rebase origin main` → 解決衝突 → 重新 push |
| 不確定改了什麼 | `git diff` 或 `git status` |
| 想看歷史 | `git log --oneline -10` |

詳細的故障排除請參考 [Troubleshooting](troubleshooting.md)。
