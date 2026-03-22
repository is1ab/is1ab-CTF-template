# 30 分鐘建立你的第一個 CTF 題目

> 從零開始的端到端教學。跟著做，30 分鐘內你就能提交第一個 PR。

---

## Phase A：環境準備（5 分鐘）

### 1. 安裝必要工具

```bash
# macOS
brew install git python3
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ubuntu/Debian
sudo apt update && sudo apt install -y git python3
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (在 PowerShell 中)
# 安裝 Git: https://git-scm.com/download/win
# 安裝 Python: https://www.python.org/downloads/
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安裝完成後，確認版本：

```bash
git --version    # 應該看到 git version 2.x.x
python3 --version # 應該看到 Python 3.9+
uv --version     # 應該看到 uv 0.x.x
```

> **如果 `uv: command not found`**：重新開啟終端機，或執行 `source ~/.bashrc`（Linux）/ `source ~/.zshrc`（macOS）。

### 2. 取得專案

```bash
git clone <你的-private-repo-url>
cd <repo-名稱>
```

### 3. 安裝依賴並設定環境

```bash
uv sync
make setup
```

你應該看到類似這樣的輸出：

```
✅ Pre-commit hook 已安裝
✅ Pre-push hook 已安裝
✅ 所有檢查通過!
🎉 專案設置完整,可以開始使用
```

> **如果 `make: command not found`**：macOS 請安裝 Xcode Command Line Tools (`xcode-select --install`)，Linux 請安裝 `sudo apt install make`。

---

## Phase B：建立第一個題目（10 分鐘）

### 4. 選擇題目類型

不確定要選什麼類型？參考 [題目類型指南](docs/challenge-types-guide.md)。

常見選擇：

| 你的題目是... | 選這個 category |
|---|---|
| 網頁漏洞（XSS、SQL Injection） | `web` |
| 二進制漏洞利用（Buffer Overflow） | `pwn` |
| 密碼學（RSA、AES） | `crypto` |
| 逆向工程（Crackme） | `reverse` |
| 鑑識、隱寫術 | `misc` |

### 5. 用指令建立題目骨架

```bash
make new-challenge ARGS="crypto my_first_challenge baby"
```

> 格式：`make new-challenge ARGS="<category> <name> <difficulty>"`
> difficulty 可選：`baby`、`easy`、`middle`、`hard`、`impossible`

你應該看到：

```
📁 Creating challenge: crypto/my_first_challenge
✅ Challenge created successfully!
```

腳本會自動建立這些檔案：

```
challenges/crypto/my_first_challenge/
├── public.yml       ← 題目公開資訊（參與者看得到）
├── private.yml      ← Flag 和答案（永遠不會公開）
├── README.md        ← 題目描述
├── src/             ← 你的原始碼
├── docker/          ← Docker 設定（如需要）
├── solution/        ← 官方解法
├── writeup/         ← 賽後 writeup
└── files/           ← 給參與者下載的附件
```

> **為什麼有兩個 YAML？** `public.yml` 會同步到公開 repo，`private.yml` 只存在私有 repo 中。這確保 flag 永遠不會洩漏。詳見 [public/private 說明](docs/public-private-explained.md)。

### 6. 設定 Flag（最重要！）

打開 `private.yml`，找到 `flag` 欄位：

```bash
# 用你喜歡的編輯器
code challenges/crypto/my_first_challenge/private.yml
# 或
vim challenges/crypto/my_first_challenge/private.yml
```

修改 flag 值：

```yaml
flag: "is1abCTF{fake_flag_replace_me}"
```

> Flag 格式必須是 `is1abCTF{...}`（取決於 config.yml 中的 `flag_prefix`）。

### 7. 填寫題目資訊

打開 `public.yml`，修改以下欄位：

```bash
code challenges/crypto/my_first_challenge/public.yml
```

至少修改這些：

```yaml
title: "My First Crypto Challenge"
description: "這是一個入門級的密碼學題目，你需要..."
tags:
  - "crypto"
  - "beginner"
  - "rsa"
```

> **注意：永遠不要在 `public.yml` 中放 flag！** Git hooks 會自動掃描並阻擋。

### 8. 實作題目

在 `src/` 目錄中撰寫你的題目。以下是一個最小的 Crypto 範例：

```bash
cat > challenges/crypto/my_first_challenge/src/generate.py << 'PYEOF'
#!/usr/bin/env python3
"""產生題目附件"""

# 這是一個簡單的 XOR 加密範例
FLAG = "is1abCTF{fake_flag_replace_me}"
KEY = 0x42

encrypted = bytes([c ^ KEY for c in FLAG.encode()])

with open("../files/encrypted.bin", "wb") as f:
    f.write(encrypted)

print(f"Encrypted flag written to files/encrypted.bin")
print(f"Key hint: 0x{KEY:02x}")
PYEOF
```

> 如果你的題目需要 Docker（Web/PWN 類），請參考 `challenges/examples/` 中的範例。

---

## Phase C：本地測試（5 分鐘）

### 9. 驗證題目結構

```bash
make validate ARGS="challenges/crypto/my_first_challenge"
```

你應該看到：

```
🔍 Validating challenge: challenges/crypto/my_first_challenge
✅ Validation passed
```

> **如果看到錯誤**：根據錯誤訊息修正。常見問題請參考 [Troubleshooting](docs/troubleshooting.md)。

### 10. 掃描敏感資料

確保你沒有不小心把 flag 寫在公開檔案中：

```bash
make scan
```

你應該看到掃描結果，確認沒有 CRITICAL 或 HIGH 等級的問題。

---

## Phase D：提交 PR（10 分鐘）

### 11. 建立分支並提交

```bash
# 如果 create-challenge.py 沒有自動建立分支，手動建立
git checkout -b challenge/crypto/my_first_challenge

# 加入你的檔案
git add challenges/crypto/my_first_challenge/

# 提交（使用 Conventional Commits 格式）
git commit -m "feat(crypto): add my_first_challenge"
```

> **如果 commit 被 hook 擋住了**：代表有敏感資料被偵測到。執行 `make scan` 找出問題，修正後重新 commit。詳見 [Troubleshooting](docs/troubleshooting.md#commit-被-hook-擋住)。

### 12. 推送到遠端

```bash
git push -u origin challenge/crypto/my_first_challenge
```

### 13. 在 GitHub 建立 Pull Request

1. 打開你的 GitHub repo
2. 你會看到提示「Compare & pull request」，點擊它
3. PR 標題格式：`feat(crypto): add my_first_challenge`
4. 填寫描述，說明題目的內容和難度
5. 點擊「Create pull request」

### 14. CI 自動檢查

提交 PR 後，GitHub Actions 會自動執行：

| 檢查項目 | 說明 | 失敗怎麼辦 |
|---|---|---|
| **validate-challenge** | 驗證目錄結構和 YAML 格式 | 依錯誤訊息修正 public.yml |
| **pr-policy-check** | 檢查分支命名和 ownership | 確認分支名是 `challenge/<category>/<name>` |
| **security-scan** | 掃描 flag 和敏感資料洩漏 | 移除公開檔案中的 flag |
| **docker-build** | 測試 Docker 建置（如有） | 修正 Dockerfile |

所有檢查通過後，等待 reviewer 審核即可。

---

## Phase E：接下來做什麼？

恭喜！你已經完成了第一個題目！接下來你可以：

| 目標 | 文件 |
|---|---|
| 學習不同題目類型的開發方式 | [題目開發指南](docs/challenge-development.md) |
| 參考完整的範例題目 | [challenges/examples/](challenges/examples/) |
| 了解提示系統的設計 | [提示系統指南](docs/hints-system-guide.md) |
| 深入安全流程 | [安全流程指南](docs/security-workflow-guide.md) |
| Git 操作速查 | [Git 速查表](docs/git-workflow-cheatsheet.md) |
| 查看常用指令 | [命令速查表](docs/quick-reference.md) |
| 解決遇到的問題 | [常見問題](docs/troubleshooting.md) |

---

## 常用指令速查

```bash
make help            # 查看所有可用指令
make new-challenge   # 建立新題目
make validate        # 驗證單一題目
make validate-all    # 驗證所有題目
make scan            # 掃描敏感資料
make test            # 執行測試
make build           # 建置公開發布版本
```
