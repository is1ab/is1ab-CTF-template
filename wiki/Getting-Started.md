# 🎯 5 分鐘快速入門

> 完全新手也能快速上手的超簡單指南

## 📋 我是誰？這份指南適合我嗎？

- ✅ 我完全沒用過這個系統
- ✅ 我想快速了解如何開始
- ✅ 我需要最簡單的步驟說明
- ✅ 我對 Git 和 GitHub 不太熟悉

**如果您符合以上條件，這份指南就是為您準備的！**

---

## 🎯 目標

在 **5 分鐘內**，您將：
1. ✅ 完成環境設置
2. ✅ 建立第一個題目
3. ✅ 了解基本流程

---

## 步驟 1：安裝必要工具（2 分鐘）

### 檢查您是否已安裝

打開終端機（Terminal），執行以下命令檢查：

```bash
# 檢查 Git
git --version
# 應該顯示：git version 2.x.x

# 檢查 Python
python3 --version
# 應該顯示：Python 3.8 或更高版本

# 檢查 Docker（可選，用於測試題目）
docker --version
```

### 如果沒有安裝

#### macOS 用戶

```bash
# 安裝 Homebrew（如果還沒有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 Git
brew install git

# 安裝 Python（通常已內建）
# 如果沒有：brew install python3

# 安裝 uv（Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows 用戶

1. **安裝 Git**
   - 下載：https://git-scm.com/download/win
   - 執行安裝程式，全部使用預設選項

2. **安裝 Python**
   - 下載：https://www.python.org/downloads/
   - ✅ 勾選 "Add Python to PATH"
   - 執行安裝程式

3. **安裝 uv**
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

#### Linux 用戶

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git python3 python3-pip

# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 步驟 2：取得專案（1 分鐘）

### 方法 A：使用 GitHub Template（推薦）

1. **前往 GitHub**
   ```
   打開瀏覽器，前往：
   https://github.com/is1ab/is1ab-CTF-template
   ```

2. **點擊綠色按鈕**
   ```
   找到 "Use this template" 按鈕
   點擊 → "Create a new repository"
   ```

3. **填寫資訊**
   ```
   Repository name: my-first-ctf
   Description: 我的第一個 CTF 專案
   Visibility: Private ✅（建議）
   點擊 "Create repository"
   ```

4. **Clone 到本地**
   ```bash
   # 複製 HTTPS 連結（在 GitHub 頁面上點擊綠色 "Code" 按鈕）
   git clone https://github.com/YOUR-USERNAME/my-first-ctf.git
   cd my-first-ctf
   ```

### 方法 B：直接 Clone（簡單快速）

```bash
git clone https://github.com/is1ab/is1ab-CTF-template.git my-first-ctf
cd my-first-ctf
```

---

## 步驟 3：設置環境（1 分鐘）

```bash
# 1. 安裝依賴（自動建立虛擬環境）
uv sync

# 2. 檢查是否成功
uv run python --version
# 應該顯示 Python 版本

# 3. 測試腳本是否可用
uv run python scripts/create-challenge.py --help
# 應該顯示幫助訊息
```

**✅ 檢查點**：如果看到幫助訊息，表示環境設置成功！

---

## 步驟 4：建立第一個題目（1 分鐘）

```bash
# 建立一個簡單的 Web 題目
uv run python scripts/create-challenge.py web hello_world baby --author "YourName"

# 查看建立的題目
ls challenges/web/hello_world/
```

**您應該看到：**
```
hello_world/
├── private.yml      # 🔒 敏感資料（含 flag）
├── public.yml       # 📢 公開資訊
├── README.md        # 題目說明
├── src/             # 源碼目錄
├── docker/          # Docker 配置
├── files/           # 附件目錄
└── writeup/         # 解答目錄
```

---

## 步驟 5：編輯題目（可選）

### 設定 Flag（在 private.yml）

```bash
# 編輯 private.yml
vim challenges/web/hello_world/private.yml
# 或使用您喜歡的編輯器

# 找到 flag 欄位，修改為：
flag: "is1abCTF{hello_world_flag_here}"
```

### 設定公開資訊（在 public.yml）

```bash
# 編輯 public.yml
vim challenges/web/hello_world/public.yml

# 修改 description 等公開資訊
# 注意：不要在這裡放 flag！
```

---

## ✅ 完成！您已經成功：

- ✅ 設置了開發環境
- ✅ 建立了第一個題目
- ✅ 了解了基本結構

---

## 🎓 下一步學習

### 想要了解更多？

1. **📖 閱讀完整指南**
   - [安全流程完整指南](security-workflow-guide.md) - 深入了解安全流程
   - [Git 操作教學](git-workflow-guide.md) - 學習 Git 和 GitHub 操作

2. **🚀 嘗試更多功能**
   ```bash
   # 驗證題目
   uv run python scripts/validate-challenge.py challenges/web/hello_world/
   
   # 安全掃描
   uv run python scripts/scan-secrets.py --path challenges/
   
   # 啟動 Web GUI
   cd web-interface
   uv run python app.py
   # 訪問 http://localhost:8004
   ```

3. **🔄 學習 Git 工作流程**
   ```bash
   # 建立分支
   git checkout -b challenge/web/hello_world
   
   # 提交變更
   git add challenges/web/hello_world/
   git commit -m "feat(web): add hello_world challenge"
   
   # 推送到 GitHub
   git push origin challenge/web/hello_world
   ```

---

## ❓ 常見問題

### Q: 我沒有 GitHub 帳號怎麼辦？

**A:** 您可以：
1. 免費註冊 GitHub 帳號：https://github.com/signup
2. 或直接 clone 模板，在本地使用（無法使用 GitHub 功能）

### Q: 命令執行失敗怎麼辦？

**A:** 檢查：
1. 是否在正確的目錄（`cd my-first-ctf`）
2. 是否已安裝所有工具（Git、Python、uv）
3. 查看錯誤訊息，通常會告訴您缺少什麼

### Q: 我不會用 vim 編輯器

**A:** 可以使用其他編輯器：
- **VS Code**: `code challenges/web/hello_world/private.yml`
- **nano**: `nano challenges/web/hello_world/private.yml`
- **Windows 記事本**: 直接雙擊檔案開啟

### Q: 我想了解更多細節

**A:** 請參閱：
- [快速開始指南](quick-start-guide.md) - 15 分鐘完整教學
- [安全流程指南](security-workflow-guide.md) - 深入了解安全流程
- [Git 操作教學](git-workflow-guide.md) - Git 和 GitHub 完整教學

---

## 📞 需要幫助？

- 📖 查看 [完整文檔目錄](../README.md#詳細文檔)
- 🐛 提交 [Issue](https://github.com/is1ab/is1ab-CTF-template/issues)
- 💬 參與 [討論](https://github.com/is1ab/is1ab-CTF-template/discussions)

---

**🎉 恭喜！您已經完成快速入門！現在可以開始探索更多功能了！**

---

## 📚 延伸閱讀

- **[15 分鐘完整教學](quick-start-guide.md)** — 包含 Docker 測試和 Web 管理介面
- **[環境設置指南](setup-guide.md)** — 詳細的系統需求和設定步驟
- **[快速命令參考](quick-reference.md)** — 常用命令速查表

