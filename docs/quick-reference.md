# 🚀 CTF 安全流程快速參考

> 常用命令和流程的快速參考指南

## 📋 常用命令

### 建置相關

```bash
# 建置所有題目
./scripts/build.sh --force

# 建置特定題目
./scripts/build.sh --challenge challenges/web/sql_injection --force

# 模擬建置（不實際建立檔案）
./scripts/build.sh --dry-run

# 包含 writeup
./scripts/build.sh --include-writeups --force
```

### 安全掃描

```bash
# 掃描當前目錄
uv run python scripts/scan-secrets.py

# 掃描建置輸出
uv run python scripts/scan-secrets.py --path public-release

# 輸出報告
uv run python scripts/scan-secrets.py --format markdown --output report.md

# 發現 HIGH 時失敗
uv run python scripts/scan-secrets.py --fail-on-high
```

### Pages 生成

```bash
# 生成網站（dark 主題）
uv run python scripts/generate-pages.py \
    --input public-release \
    --output _site \
    --theme dark

# 生成網站（light 主題）
uv run python scripts/generate-pages.py --theme light

# 預覽模式（從 challenges 生成）
uv run python scripts/generate-pages.py \
    --input challenges \
    --output _preview
```

## 🔄 完整工作流程

### 1. 開發新題目

```bash
# 建立題目
uv run python scripts/create-challenge.py web my_challenge easy --author YourName

# 進入題目目錄
cd challenges/web/my_challenge

# 編輯 private.yml（含 flag）
vim private.yml

# 編輯 public.yml（公開資訊）
vim public.yml

# 標記為準備發布
# 在 public.yml 中設定: ready_for_release: true
```

### 2. 本地測試

```bash
# 返回根目錄
cd ../../..

# 安全掃描
uv run python scripts/scan-secrets.py --path challenges/web/my_challenge

# 模擬建置
./scripts/build.sh --challenge challenges/web/my_challenge --dry-run

# 實際建置
./scripts/build.sh --challenge challenges/web/my_challenge --force

# 驗證輸出
uv run python scripts/scan-secrets.py --path public-release
```

### 3. 提交 PR

```bash
# 提交變更
git add challenges/web/my_challenge/
git commit -m "feat(web): add my_challenge"

# 推送並建立 PR
git push origin feature/my_challenge
# 在 GitHub 上建立 Pull Request
```

### 4. 自動化流程

- ✅ PR 時自動執行 `security-scan.yml`
- ✅ 合併到 main 時自動執行 `build-public.yml`
- ✅ Public repo 更新時自動執行 `deploy-pages.yml`

## 📁 檔案結構檢查清單

### Private Repository

```
challenges/web/my_challenge/
├── private.yml          ✅ 含 flag
├── public.yml           ✅ 公開資訊
├── README.md            ✅ 題目說明
├── src/                 ✅ 源碼
├── docker/              ✅ Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── files/               ✅ 附件
└── writeup/             ✅ 解答（可選）
```

### Public Repository（建置後）

```
public-release/challenges/web/my_challenge/
├── public.yml           ✅ 已過濾
├── README.md            ✅ 已過濾
└── files/               ✅ 安全附件
```

## 🔒 安全檢查清單

### 開發時

- [ ] `private.yml` 包含真實 flag
- [ ] `public.yml` 不包含 flag
- [ ] README.md 中無 flag
- [ ] Docker 配置使用環境變數 `${FLAG}`
- [ ] 無硬編碼密碼或 API Key

### PR 前

- [ ] 執行 `scan-secrets.py` 無錯誤
- [ ] `ready_for_release: true`（如要發布）
- [ ] 本地建置測試通過
- [ ] 檢查 GitHub Actions 狀態

### 發布前

- [ ] 所有題目已測試
- [ ] 安全掃描通過
- [ ] 建置輸出驗證無 flag
- [ ] Pages 預覽正常

## ⚙️ 配置檢查

### config.yml 關鍵設定

```yaml
project:
  flag_prefix: "is1abCTF" # ✅ 確認正確

public_release:
  repository:
    name: "your-org/repo-name" # ✅ 確認設定

security:
  scan_level: "normal" # ✅ 確認等級
```

### GitHub Secrets

- [ ] `PUBLIC_REPO_TOKEN` 已設定
- [ ] `PUBLIC_REPO` 已設定（如使用）
- [ ] `SLACK_WEBHOOK_URL` 已設定（可選）

## 🐛 常見問題快速修復

### Flag 洩漏

```bash
# 找出包含 flag 的檔案
grep -r "is1abCTF{" challenges/

# 移除或替換
# 在 public.yml 中移除 flag 欄位
# 在 README.md 中替換為 [REDACTED]
```

### 建置失敗

```bash
# 檢查權限
chmod +x scripts/build.sh

# 檢查目錄
ls challenges/

# 檢查配置
cat config.yml
```

### 掃描失敗

```bash
# 查看詳細報告
uv run python scripts/scan-secrets.py --format markdown --output report.md
cat report.md

# 修復問題後重新掃描
```

## 📞 取得幫助

- 📖 [完整指南](security-workflow-guide.md)
- 🐛 [故障排除](security-workflow-guide.md#故障排除)
- 🔄 [Git 操作教學](git-workflow-guide.md)
- 📚 [其他文檔](../README.md)

---

**提示**：將此頁面加入書籤以便快速參考！
