# ❓ 常見問題 FAQ

> 快速找到問題的解決方案

## 📋 目錄

- [安裝問題](#安裝問題)
- [環境設置問題](#環境設置問題)
- [題目創建問題](#題目創建問題)
- [Git 操作問題](#git-操作問題)
- [安全掃描問題](#安全掃描問題)
- [建置問題](#建置問題)
- [Web GUI 問題](#web-gui-問題)

---

## 安裝問題

### Q1: uv 安裝失敗怎麼辦？

**A:** 根據您的作業系統：

#### macOS
```bash
# 方法 1：使用官方安裝腳本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 方法 2：使用 Homebrew
brew install uv

# 方法 3：使用 pip
pip install uv
```

#### Windows
```powershell
# 使用 PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

#### Linux
```bash
# 使用官方安裝腳本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

**如果還是失敗：**
- 檢查網路連線
- 檢查 Python 是否已安裝：`python3 --version`
- 查看 [uv 官方文檔](https://github.com/astral-sh/uv)

### Q2: Git 安裝失敗怎麼辦？

**A:** 

#### macOS
```bash
# 使用 Homebrew
brew install git

# 或下載安裝程式
# https://git-scm.com/download/mac
```

#### Windows
- 下載 Git for Windows：https://git-scm.com/download/win
- 執行安裝程式，全部使用預設選項

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git

# CentOS/RHEL
sudo yum install git
```

### Q3: Python 版本不符合要求怎麼辦？

**A:** 需要 Python 3.8 或更高版本：

```bash
# 檢查當前版本
python3 --version

# 如果版本太低，需要升級
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# 下載並安裝：https://www.python.org/downloads/
```

---

## 環境設置問題

### Q4: `uv sync` 執行失敗怎麼辦？

**A:** 檢查以下項目：

```bash
# 1. 確認在專案根目錄
pwd
# 應該顯示：.../is1ab-CTF-template

# 2. 確認 config.yml 存在
ls config.yml

# 3. 檢查 Python 版本
python3 --version

# 4. 清理並重新安裝
rm -rf .venv
uv sync --verbose
```

### Q5: 找不到 `scripts/create-challenge.py`？

**A:** 

```bash
# 確認在專案根目錄
cd /path/to/is1ab-CTF-template

# 確認檔案存在
ls scripts/create-challenge.py

# 如果不存在，可能是 clone 不完整
git pull origin main
```

### Q6: 執行腳本時出現 `ModuleNotFoundError`？

**A:** 

```bash
# 確保使用 uv run
uv run python scripts/create-challenge.py --help

# 不要直接使用 python
# ❌ python scripts/create-challenge.py  # 錯誤
# ✅ uv run python scripts/create-challenge.py  # 正確
```

---

## 題目創建問題

### Q7: `create-challenge.py` 執行失敗？

**A:** 檢查輸入參數：

```bash
# 查看幫助
uv run python scripts/create-challenge.py --help

# 確認參數格式正確
uv run python scripts/create-challenge.py web my_challenge easy --author "YourName"

# 常見錯誤：
# ❌ 分類錯誤：category 必須是 web, pwn, reverse, crypto, forensic, misc 之一
# ❌ 難度錯誤：difficulty 必須是 baby, easy, middle, hard, impossible 之一
# ❌ 名稱錯誤：只能包含字母、數字、底線和連字號
```

### Q8: 題目已存在怎麼辦？

**A:** 

```bash
# 選項 1：使用不同的名稱
uv run python scripts/create-challenge.py web my_challenge_v2 easy --author "YourName"

# 選項 2：刪除現有題目（謹慎！）
rm -rf challenges/web/my_challenge

# 選項 3：檢查現有題目
ls challenges/web/
```

### Q9: 創建的題目結構不完整？

**A:** 

```bash
# 檢查題目結構
ls -la challenges/web/my_challenge/

# 應該包含：
# - private.yml
# - public.yml
# - README.md
# - src/
# - docker/
# - files/
# - writeup/

# 如果缺少檔案，手動創建
mkdir -p challenges/web/my_challenge/{src,docker,files,writeup}
```

---

## Git 操作問題

### Q10: `git clone` 失敗怎麼辦？

**A:** 

```bash
# 檢查網路連線
ping github.com

# 檢查 Git 配置
git config --list

# 使用 HTTPS（如果 SSH 失敗）
git clone https://github.com/is1ab/is1ab-CTF-template.git

# 使用 SSH（如果 HTTPS 失敗）
git clone git@github.com:is1ab/is1ab-CTF-template.git
```

### Q11: `git push` 失敗怎麼辦？

**A:** 

```bash
# 1. 檢查遠端設定
git remote -v

# 2. 檢查分支設定
git branch -vv

# 3. 設定 upstream（首次推送）
git push -u origin branch-name

# 4. 如果權限錯誤，檢查 SSH Key
ssh -T git@github.com

# 5. 如果認證失敗，使用 Personal Access Token
# GitHub → Settings → Developer settings → Personal access tokens
```

### Q12: 如何撤銷錯誤的提交？

**A:** 

```bash
# 撤銷最後一次提交（保留變更）
git reset --soft HEAD~1

# 撤銷最後一次提交（不保留變更）
git reset --hard HEAD~1

# 撤銷已 push 的提交（使用 revert）
git revert HEAD
git push origin main

# ⚠️ 注意：不要 force push 到 main 分支！
```

### Q13: 如何解決合併衝突？

**A:** 

```bash
# 1. 拉取遠端變更
git pull origin main

# 2. 如果有衝突，查看衝突檔案
git status

# 3. 編輯衝突檔案，尋找 <<<<<<< ======= >>>>>>> 標記
vim conflicted_file.py

# 4. 解決衝突後標記為已解決
git add conflicted_file.py

# 5. 完成合併
git commit
```

---

## 安全掃描問題

### Q14: `scan-secrets.py` 發現 Flag 洩漏怎麼辦？

**A:** 

```bash
# 1. 查看詳細報告
uv run python scripts/scan-secrets.py --path . --format markdown --output report.md
cat report.md

# 2. 找出包含 flag 的檔案
grep -r "is1abCTF{" challenges/

# 3. 修復問題：
# - 從 public.yml 中移除 flag 欄位
# - 從 README.md 中移除 flag 字串
# - 確保 private.yml 在 .gitignore 中

# 4. 重新掃描
uv run python scripts/scan-secrets.py --path .
```

### Q15: 安全掃描出現假陽性（False Positive）？

**A:** 

```bash
# 檢查是否為範例或佔位符
# 如果檔案中包含 "example", "test", "TODO" 等關鍵字，可能是假陽性

# 調整掃描配置（在 config.yml 中）
security:
  sensitive_patterns:
    - pattern: "example_flag"  # 排除範例
      severity: "INFO"
```

### Q16: GitHub Actions 安全掃描失敗？

**A:** 

1. **查看 Actions 日誌**
   - 前往 GitHub → Actions
   - 點擊失敗的 workflow
   - 查看詳細日誌

2. **檢查 PR 評論**
   - GitHub Actions 會在 PR 中留下掃描報告
   - 查看報告中的具體問題

3. **修復問題**
   ```bash
   # 根據報告修復問題
   # 然後重新提交
   git add .
   git commit -m "fix: resolve security scan issues"
   git push origin branch-name
   ```

---

## 建置問題

### Q17: `build.sh` 執行失敗？

**A:** 

```bash
# 1. 檢查權限
chmod +x scripts/build.sh

# 2. 確認在專案根目錄
pwd

# 3. 檢查 config.yml 是否存在
ls config.yml

# 4. 使用詳細模式查看錯誤
./scripts/build.sh --verbose --force

# 5. 檢查輸出目錄權限
ls -la public-release/
```

### Q18: 建置後發現 Flag 洩漏？

**A:** 

```bash
# 1. 立即停止建置
# 2. 檢查建置輸出
uv run python scripts/scan-secrets.py --path public-release

# 3. 找出問題來源
grep -r "is1abCTF{" public-release/

# 4. 修復源檔案
# 5. 重新建置
./scripts/build.sh --force
```

### Q19: `build.sh` 跳過所有題目？

**A:** 

```bash
# 檢查題目是否標記為 ready_for_release
grep "ready_for_release" challenges/*/public.yml

# 如果都是 false，需要設定為 true
# 編輯 public.yml
vim challenges/web/my_challenge/public.yml
# 設定：ready_for_release: true

# 重新建置
./scripts/build.sh --force
```

---

## Web GUI 問題

### Q20: Web GUI 無法啟動？

**A:** 

```bash
# 1. 檢查端口是否被占用
lsof -i :8004  # macOS/Linux
netstat -ano | findstr :8004  # Windows

# 2. 使用其他端口
cd web-interface
uv run python app.py --port 8005

# 3. 檢查依賴是否安裝
cd web-interface
uv sync

# 4. 查看錯誤訊息
uv run python app.py --verbose
```

### Q21: Web GUI 顯示空白或錯誤？

**A:** 

```bash
# 1. 檢查瀏覽器控制台（F12）
# 2. 檢查後端日誌
# 3. 確認 challenges 目錄存在
ls challenges/

# 4. 確認 public.yml 檔案存在
find challenges -name "public.yml"

# 5. 重新啟動
cd web-interface
uv run python app.py
```

### Q22: Web GUI 創建的題目結構不正確？

**A:** 

```bash
# Web GUI 會自動創建 private.yml 和 public.yml
# 如果結構不完整，手動補充：

# 1. 檢查題目結構
ls -la challenges/web/my_challenge/

# 2. 如果缺少目錄，創建它們
mkdir -p challenges/web/my_challenge/{src,docker,files,writeup}

# 3. 使用腳本驗證
uv run python scripts/validate-challenge.py challenges/web/my_challenge/
```

---

## 其他問題

### Q23: 如何更新專案到最新版本？

**A:** 

```bash
# 如果使用 Template 建立的 repo
git pull origin main

# 如果是 Fork
git fetch upstream
git merge upstream/main
git push origin main
```

### Q24: 如何備份專案？

**A:** 

```bash
# 方法 1：推送到 GitHub（推薦）
git push origin main

# 方法 2：建立本地備份
tar -czf backup-$(date +%Y%m%d).tar.gz .

# 方法 3：Clone 到其他位置
git clone /path/to/project /path/to/backup
```

### Q25: 如何重置專案到初始狀態？

**A:** 

```bash
# ⚠️ 警告：這會刪除所有本地變更！

# 1. 備份當前變更（可選）
git stash

# 2. 重置到遠端 main 分支
git fetch origin
git reset --hard origin/main

# 3. 清理未追蹤的檔案
git clean -fd
```

### Q26: 如何查看專案版本？

**A:** 

```bash
# 查看 Git 標籤
git tag

# 查看最新提交
git log -1

# 查看 README 中的版本資訊
grep "版本" README.md
```

---

## 🆘 還是找不到答案？

### 獲取幫助

1. **查看完整文檔**
   - [完整文檔目錄](README.md)
   - [安全流程指南](security-workflow-guide.md)
   - [故障排除](security-workflow-guide.md#故障排除)

2. **搜尋現有問題**
   - [GitHub Issues](https://github.com/is1ab/is1ab-CTF-template/issues)
   - [GitHub Discussions](https://github.com/is1ab/is1ab-CTF-template/discussions)

3. **提交新問題**
   - 前往 [GitHub Issues](https://github.com/is1ab/is1ab-CTF-template/issues/new)
   - 選擇適當的 Issue 模板
   - 提供詳細的錯誤訊息和環境資訊

4. **聯繫團隊**
   - 通過 GitHub Discussions
   - 或聯繫 IS1AB 團隊

---

**最後更新**：2025-01-XX  
**維護者**：IS1AB Team

