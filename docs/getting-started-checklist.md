# ✅ 新手入門檢查清單

> 確保您已完成所有必要的設置步驟

## 📋 前置準備檢查

### 工具安裝

- [ ] **Git** 已安裝
  ```bash
  git --version
  # 應該顯示：git version 2.x.x
  ```

- [ ] **Python 3.8+** 已安裝
  ```bash
  python3 --version
  # 應該顯示：Python 3.8.x 或更高
  ```

- [ ] **uv** 已安裝
  ```bash
  uv --version
  # 應該顯示：uv x.x.x
  ```

- [ ] **Docker**（可選，用於測試題目）
  ```bash
  docker --version
  # 可選，但建議安裝
  ```

### Git 配置

- [ ] **使用者名稱已設定**
  ```bash
  git config --global user.name "Your Name"
  ```

- [ ] **信箱已設定**
  ```bash
  git config --global user.email "your.email@example.com"
  ```

- [ ] **SSH Key 已設定**（推薦）
  ```bash
  ssh -T git@github.com
  # 應該顯示：Hi username! You've successfully authenticated...
  ```

---

## 🚀 專案設置檢查

### 取得專案

- [ ] **已 Clone 或 Fork Repository**
  ```bash
  git clone https://github.com/YOUR-USERNAME/your-repo.git
  cd your-repo
  ```

- [ ] **在正確的分支**
  ```bash
  git branch
  # 應該顯示：* main
  ```

### 環境設置

- [ ] **依賴已安裝**
  ```bash
  uv sync
  # 應該成功完成，無錯誤
  ```

- [ ] **腳本可執行**
  ```bash
  uv run python scripts/create-challenge.py --help
  # 應該顯示幫助訊息
  ```

---

## 🎯 第一個題目檢查

### 創建題目

- [ ] **已創建第一個題目**
  ```bash
  uv run python scripts/create-challenge.py web hello_world baby --author "YourName"
  ```

- [ ] **題目結構完整**
  ```bash
  ls challenges/web/hello_world/
  # 應該包含：private.yml, public.yml, README.md, src/, docker/, files/, writeup/
  ```

### 編輯題目

- [ ] **已編輯 private.yml**（設定 flag）
  ```bash
  # 確認 flag 已設定
  grep "flag:" challenges/web/hello_world/private.yml
  ```

- [ ] **已編輯 public.yml**（設定公開資訊）
  ```bash
  # 確認 description 已設定
  grep "description:" challenges/web/hello_world/public.yml
  ```

### 驗證題目

- [ ] **題目驗證通過**
  ```bash
  uv run python scripts/validate-challenge.py challenges/web/hello_world/
  # 應該顯示：✅ All checks passed
  ```

- [ ] **安全掃描通過**
  ```bash
  uv run python scripts/scan-secrets.py --path challenges/web/hello_world/
  # 應該無 CRITICAL 錯誤
  ```

---

## 🔄 Git 工作流程檢查

### 基本操作

- [ ] **已建立分支**
  ```bash
  git checkout -b challenge/web/hello_world
  ```

- [ ] **已提交變更**
  ```bash
  git add challenges/web/hello_world/
  git commit -m "feat(web): add hello_world challenge"
  ```

- [ ] **已推送到遠端**
  ```bash
  git push -u origin challenge/web/hello_world
  ```

### Pull Request

- [ ] **已建立 Pull Request**
  - 在 GitHub 上建立 PR
  - 填寫 PR 模板
  - 等待 CI/CD 檢查通過

---

## 🌐 Web GUI 檢查（可選）

- [ ] **Web GUI 可啟動**
  ```bash
  cd web-interface
  uv run python app.py
  # 應該啟動在 http://localhost:8004
  ```

- [ ] **可以訪問儀表板**
  - 打開瀏覽器訪問 http://localhost:8004
  - 應該看到題目統計和進度

---

## 🔒 安全流程檢查

### 了解安全流程

- [ ] **已閱讀安全流程指南**
  - [安全流程完整指南](security-workflow-guide.md)

- [ ] **了解 private.yml 和 public.yml 的區別**
  - private.yml：含 flag，不公開
  - public.yml：公開資訊，無 flag

### 安全操作

- [ ] **了解 build.sh 的使用**
  ```bash
  ./scripts/build.sh --help
  ```

- [ ] **了解安全掃描的使用**
  ```bash
  uv run python scripts/scan-secrets.py --help
  ```

---

## 📚 文檔閱讀檢查

### 必讀文檔

- [ ] **[5 分鐘快速入門](getting-started.md)** ⭐
- [ ] **[Git 操作教學](git-workflow-guide.md)**
- [ ] **[安全流程指南](security-workflow-guide.md)**（至少快速瀏覽）

### 參考文檔

- [ ] **[快速參考指南](quick-reference.md)**
- [ ] **[常見問題 FAQ](faq.md)**
- [ ] **[Web GUI 整合說明](web-gui-integration.md)**（如使用 Web GUI）

---

## ✅ 完成確認

### 我已經能夠：

- [ ] 創建新題目
- [ ] 編輯題目內容
- [ ] 驗證題目結構
- [ ] 執行安全掃描
- [ ] 使用 Git 基本操作（commit, push）
- [ ] 建立 Pull Request
- [ ] 理解安全流程（private.yml vs public.yml）

### 下一步學習：

- [ ] 學習進階 Git 操作（rebase, cherry-pick）
- [ ] 學習 Docker 部署
- [ ] 學習 GitHub Actions 配置
- [ ] 學習建置公開版本流程

---

## 🎉 恭喜！

如果您完成了以上所有檢查項目，恭喜您已經掌握了基本的使用方法！

### 現在您可以：

1. **開始開發更多題目**
   ```bash
   uv run python scripts/create-challenge.py pwn buffer_overflow easy --author "YourName"
   ```

2. **探索進階功能**
   - 使用 Web GUI 管理題目
   - 執行安全掃描和建置
   - 配置 GitHub Actions

3. **參與團隊協作**
   - 提交 Pull Request
   - 審查其他人的 PR
   - 協助改進文檔

---

**需要幫助？** 查看 [常見問題 FAQ](faq.md) 或 [完整文檔目錄](README.md)

