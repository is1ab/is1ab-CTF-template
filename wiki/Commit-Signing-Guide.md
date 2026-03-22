# 🔐 Commit 簽名驗證指南

## 📋 目錄

- [為什麼需要 Commit 簽名](#為什麼需要-commit-簽名)
- [設置 GPG 金鑰](#設置-gpg-金鑰)
- [配置 Git](#配置-git)
- [簽署 Commits](#簽署-commits)
- [GitHub 設置](#github-設置)
- [疑難排解](#疑難排解)

---

## 為什麼需要 Commit 簽名？

Commit 簽名可以：

- ✅ **驗證身份**：證明 commit 確實由您提交
- ✅ **防止冒名**：防止他人使用您的名義提交代碼
- ✅ **增強安全性**：確保代碼來源的可信度
- ✅ **符合規範**：企業級專案的標準安全要求

---

## 設置 GPG 金鑰

### 1. 安裝 GPG

**macOS:**
```bash
brew install gnupg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install gnupg
```

**Windows:**
下載並安裝 [Gpg4win](https://www.gpg4win.org/)

### 2. 生成 GPG 金鑰

```bash
# 生成新的 GPG 金鑰
gpg --full-generate-key
```

選擇選項：
- **金鑰類型**: RSA and RSA (預設)
- **金鑰長度**: 4096
- **有效期**: 0 (永不過期) 或 1y (一年)
- **使用者 ID**: 輸入您的 GitHub 註冊信箱

示例：
```
Real name: GZTime
Email address: gztime@example.com
Comment: IS1AB CTF Signing Key
```

### 3. 列出 GPG 金鑰

```bash
# 列出所有金鑰
gpg --list-secret-keys --keyid-format=long

# 輸出示例：
# sec   rsa4096/3AA5C34371567BD2 2024-01-15 [SC]
#       ABCD1234ABCD1234ABCD1234ABCD1234ABCD1234
# uid                 [ultimate] GZTime <gztime@example.com>
# ssb   rsa4096/4BB6D45482678AE3 2024-01-15 [E]
```

記下金鑰 ID (例如: `3AA5C34371567BD2`)

### 4. 導出公鑰

```bash
# 將 3AA5C34371567BD2 替換為您的金鑰 ID
gpg --armor --export 3AA5C34371567BD2

# 輸出會顯示類似這樣的公鑰：
# -----BEGIN PGP PUBLIC KEY BLOCK-----
# ...
# -----END PGP PUBLIC KEY BLOCK-----
```

複製完整的公鑰（包括 BEGIN 和 END 行）

---

## 配置 Git

### 1. 設置簽名金鑰

```bash
# 設置您的 GPG 金鑰 ID
git config --global user.signingkey 3AA5C34371567BD2

# 啟用自動簽名所有 commits
git config --global commit.gpgsign true

# 啟用自動簽名所有 tags
git config --global tag.gpgsign true
```

### 2. 本地專案設置（可選）

如果只想在特定專案中啟用簽名：

```bash
cd /path/to/is1ab-CTF-template

# 僅在此專案中啟用簽名
git config --local commit.gpgsign true
git config --local tag.gpgsign true
```

### 3. 配置 GPG 程式路徑（如需要）

**macOS/Linux:**
```bash
git config --global gpg.program gpg
```

**Windows (使用 Gpg4win):**
```bash
git config --global gpg.program "C:/Program Files (x86)/GnuPG/bin/gpg.exe"
```

---

## 簽署 Commits

### 自動簽名

如果已啟用 `commit.gpgsign`，所有 commit 會自動簽名：

```bash
git commit -m "feat: add new challenge"
# 自動簽名，無需額外參數
```

### 手動簽名

如果未啟用自動簽名，使用 `-S` 參數：

```bash
git commit -S -m "feat: add new challenge"
```

### 簽署 Tag

```bash
# 創建簽名的 tag
git tag -s v1.0.0 -m "Release version 1.0.0"

# 驗證 tag 簽名
git tag -v v1.0.0
```

### 驗證簽名

```bash
# 查看 commit 的簽名
git log --show-signature

# 查看最後一個 commit 的詳細簽名資訊
git log --show-signature -1
```

---

## GitHub 設置

### 1. 添加 GPG 金鑰到 GitHub

1. 登入 GitHub
2. 點擊右上角頭像 → **Settings**
3. 側邊欄選擇 **SSH and GPG keys**
4. 點擊 **New GPG key**
5. 貼上剛才導出的公鑰
6. 點擊 **Add GPG key**

### 2. 驗證設置

提交一個簽名的 commit 並推送到 GitHub：

```bash
git commit -S -m "test: verify GPG signature"
git push
```

在 GitHub 上查看該 commit，應該會看到 **Verified** 徽章 ✅

### 3. 啟用警戒模式（Vigilant Mode）

啟用後，未簽名的 commit 會顯示 "Unverified" 標籤：

1. GitHub Settings → **SSH and GPG keys**
2. 勾選 **Flag unsigned commits as unverified**

---

## 疑難排解

### 問題 1: gpg failed to sign the data

**原因**: GPG 無法存取私鑰或 TTY 配置問題

**解決方案**:

```bash
# 方法 1: 設置 GPG_TTY 環境變數
export GPG_TTY=$(tty)

# 將以下行添加到 ~/.bashrc 或 ~/.zshrc
echo 'export GPG_TTY=$(tty)' >> ~/.zshrc

# 方法 2: 使用 pinentry-mac (macOS)
brew install pinentry-mac
echo "pinentry-program $(which pinentry-mac)" >> ~/.gnupg/gpg-agent.conf
gpgconf --kill gpg-agent

# 方法 3: 測試 GPG 簽名
echo "test" | gpg --clearsign
```

### 問題 2: GitHub 顯示 Unverified

**可能原因**:

1. **Email 不匹配**: Git 配置的 email 與 GPG 金鑰不同
   ```bash
   # 檢查 Git email
   git config user.email

   # 檢查 GPG email
   gpg --list-secret-keys --keyid-format=long

   # 如果不同，更新 Git email
   git config --global user.email "your-github-email@example.com"
   ```

2. **公鑰未添加到 GitHub**: 確認已將公鑰添加到 GitHub

3. **過期的金鑰**: 檢查金鑰是否過期
   ```bash
   gpg --list-keys
   ```

### 問題 3: 在多台電腦上使用同一金鑰

**導出私鑰** (在原電腦):
```bash
# 導出私鑰（小心保管！）
gpg --export-secret-keys --armor 3AA5C34371567BD2 > private-key.asc
```

**匯入私鑰** (在新電腦):
```bash
# 匯入私鑰
gpg --import private-key.asc

# 信任金鑰
gpg --edit-key 3AA5C34371567BD2
# 輸入: trust
# 選擇: 5 (我完全信任)
# 輸入: quit
```

**⚠️ 安全警告**:
- 私鑰文件極度敏感，務必安全傳輸（如 USB、加密郵件）
- 傳輸後立即刪除私鑰文件
- 不要透過網路或雲端儲存傳送

### 問題 4: macOS Keychain 問題

```bash
# 重啟 GPG agent
gpgconf --kill gpg-agent

# 清除快取
gpgconf --reload gpg-agent
```

---

## 在此專案中使用

### 推薦配置

為 IS1AB CTF Template 專案設置簽名：

```bash
cd /path/to/is1ab-CTF-template

# 啟用本地簽名
git config --local commit.gpgsign true
git config --local tag.gpgsign true

# 驗證配置
git config --local --list | grep sign
```

### 分支保護規則

建議在 GitHub 設置中啟用：

- ✅ **Require signed commits**: 要求所有 commit 必須簽名
- ✅ **Require linear history**: 要求線性歷史記錄

設置路徑：
```
Repository Settings
→ Branches
→ Branch protection rules (main)
→ Require signed commits ✓
```

---

## 最佳實踐

1. **團隊規範**
   - 所有成員必須設置 GPG 簽名
   - 在 CONTRIBUTING.md 中說明簽名要求

2. **金鑰管理**
   - 定期更換金鑰（建議每年）
   - 舊金鑰吊銷後上傳吊銷證書到 GitHub
   - 使用強密碼保護私鑰

3. **備份**
   - 備份私鑰到安全位置
   - 生成吊銷證書以備不時之需
   ```bash
   gpg --output revoke.asc --gen-revoke 3AA5C34371567BD2
   ```

4. **CI/CD**
   - 自動化工具可能需要特殊配置
   - 考慮使用 GitHub App 或 Deploy Key

---

## 參考資源

- [GitHub: Managing commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification)
- [Git: Signing Your Work](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)
- [GnuPG Documentation](https://www.gnupg.org/documentation/)

---

## 檢查清單

完成以下步驟後，您就可以開始使用簽名 commits：

- [ ] 安裝 GPG
- [ ] 生成 GPG 金鑰
- [ ] 配置 Git 使用 GPG 金鑰
- [ ] 導出公鑰並添加到 GitHub
- [ ] 測試簽名 commit
- [ ] 在 GitHub 上驗證簽名顯示 "Verified"
- [ ] 啟用 vigilant mode (可選)
- [ ] 備份私鑰到安全位置

---

**需要幫助？** 查看 [疑難排解](#疑難排解) 或建立 Issue
