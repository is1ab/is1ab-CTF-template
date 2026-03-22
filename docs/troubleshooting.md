# 常見問題與故障排除

> 遇到問題了？在這裡找答案。

---

## 環境設置問題

### `uv: command not found`

uv 沒有安裝或不在 PATH 中。

```bash
# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 重新載入 shell
source ~/.bashrc   # Linux
source ~/.zshrc    # macOS
```

### `make: command not found`

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt install make

# Windows
# 建議使用 WSL2，或安裝 Git Bash
```

### `make: *** No rule to make target`

你可能不在專案根目錄。確認當前目錄有 `Makefile`：

```bash
ls Makefile  # 應該看到 Makefile
# 如果沒有，cd 到專案根目錄
```

### `uv sync` 失敗

```bash
# 確認 Python 版本
python3 --version  # 需要 3.8+

# 如果版本太舊，升級 Python
brew install python3  # macOS
sudo apt install python3.11  # Ubuntu
```

---

## Git 和 Commit 問題

### Commit 被 hook 擋住 {#commit-被-hook-擋住}

**症狀**：執行 `git commit` 後看到類似這樣的錯誤：

```
🚫 BLOCKED: Flag pattern detected
```

**原因**：你的程式碼中有 flag 格式字串（`is1abCTF{...}`）出現在公開檔案中。

**修復**：

```bash
# 1. 找出哪裡有問題
make scan

# 2. 常見原因和修復方式：
#    - flag 寫在 public.yml 中 → 移到 private.yml
#    - flag 寫在 README.md 中 → 用 placeholder 替代
#    - flag 硬編碼在 Dockerfile 中 → 改用環境變數

# 3. 修正後重新 commit
git add .
git commit -m "feat(web): add my_challenge"
```

> **緊急情況**：如果你確定是誤報，可用 `git commit --no-verify` 繞過，但**不建議**。

### Branch 名稱不符合規範

**症狀**：PR 被 `pr-policy-check` 擋住，錯誤訊息提到 branch naming。

**規範**：題目分支必須命名為 `challenge/<category>/<name>`

```bash
# 重新命名分支
git branch -m challenge/web/my_challenge

# 如果已經推送了錯誤名稱的分支
git push origin --delete old-branch-name
git push -u origin challenge/web/my_challenge
```

### PR ownership 檢查失敗

**症狀**：`pr-policy-check` 報錯「PR author not in owners」

**修復**：在 `public.yml` 中加入你的 GitHub 用戶名：

```yaml
owners:
  - "your-github-username"
assignee: "your-github-username"
```

---

## 驗證和掃描問題

### `validate-challenge` 報錯

常見錯誤和修復：

| 錯誤訊息 | 原因 | 修復 |
|---|---|---|
| `Missing public.yml` | 題目缺少 public.yml | 確認檔案存在且名稱正確 |
| `Missing required field: title` | public.yml 缺少必要欄位 | 加上 title、category、difficulty |
| `Invalid difficulty` | 難度值不在允許範圍 | 使用 baby/easy/middle/hard/impossible |
| `Invalid category` | 分類值不在允許範圍 | 使用 web/pwn/reverse/crypto/misc 等 |
| `YAML parsing error` | YAML 格式錯誤 | 檢查縮排（用空格不用 Tab） |

```bash
# 重新驗證
make validate ARGS="challenges/web/my_challenge"
```

### `scan-secrets` 發現問題

嚴重程度說明：

| 等級 | 意義 | 處理方式 |
|---|---|---|
| CRITICAL | Flag 洩漏 | 必須立即修復 |
| HIGH | 硬編碼密碼/API Key | 應該修復 |
| MEDIUM | 可能的敏感資訊 | 檢查是否為誤報 |
| LOW | 潛在風險 | 了解即可 |
| INFO | 資訊提示 | 可忽略 |

---

## Docker 問題

### `docker-compose up` 失敗

```bash
# 確認 Docker 正在運行
docker info

# 常見修復
cd challenges/web/my_challenge/docker
docker-compose down       # 清理舊容器
docker-compose up --build # 重新建置
```

### Docker build 失敗

常見原因：
- `COPY` 指令的來源路徑不存在 → 確認 `src/` 中有對應檔案
- `pip install` 失敗 → 確認 `requirements.txt` 語法正確
- Port 衝突 → 更改 `docker-compose.yml` 中的 port mapping

---

## CI/CD 問題

### PR 被 CI 擋住了

GitHub Actions 會執行多個檢查。每個檢查的意義：

| CI Job | 檢查什麼 | 失敗怎麼辦 |
|---|---|---|
| **validate-challenge** | 目錄結構、YAML 格式 | 依錯誤訊息修正 public.yml |
| **pr-policy-check** | 分支命名、作者 ownership | 修正分支名或在 public.yml 加入你的名字 |
| **security-scan** | Flag 洩漏、敏感資料 | 移除公開檔案中的 flag |
| **docker-build** | Dockerfile 能否建置 | 修正 Dockerfile |

點擊 GitHub 上失敗的 check 可以看到詳細的錯誤日誌。

---

## 還是無法解決？

1. 查看 [FAQ](faq.md) 中是否有更多解答
2. 在 repo 中提交 [Issue](https://github.com/is1ab/is1ab-CTF-template/issues)
3. 詢問團隊中的 Admin 或 Senior Dev
