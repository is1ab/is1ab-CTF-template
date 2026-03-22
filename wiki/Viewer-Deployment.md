# 👀 Internal Viewer (viewer-data) 部署與操作

本文件描述：如何在 private dev repo 中，透過 CI 自動產生 `viewer-data` 分支，並用 Docker/Nginx 在內網提供「只讀題目進度」網站。

## ✅ 設計目標

- Viewer **只讀**：不提供建立/編輯題目
- Viewer **不登入即可看**（內網環境）
- Viewer **只顯示**：題目進度、`public.yml`（去敏後）、`challenges/**/README.md`、附件清單（不下載）
- Viewer **永不包含**：`private.yml`、flag、題目程式碼、writeup/solution

## 🧩 分支與資料

- `main`：題目完整開發內容
- `viewer-data`：CI 生成的 viewer-only artifact（包含前端 CSS/JS + data JSON + README/public.yml）

目錄結構（`viewer-data` 分支）：

```text
viewer/
  site/
    index.html
    assets/
      app.css
      app.js
  data/
    index.json
    progress.json
    challenges/<category>/<name>/{public.yml,README.md,files.json}
```

## 🤖 自動生成（GitHub Actions）

Workflow：`.github/workflows/generate-viewer-data.yml`

觸發條件（main）：
- `challenges/**/public.yml`
- `challenges/**/README.md`
- `config.yml`
- `viewer/site/**`（前端更新）

生成步驟：
1. `python scripts/generate-viewer-data.py --clean --output viewer/data`
2. `python scripts/scan-secrets.py --path viewer --fail-on-high`
3. 推送 `viewer/` 到 `viewer-data` 分支（CI-managed）

## 🔐 CI-managed 規範

建議在 GitHub 設定：
- 對 `viewer-data` 啟用 branch protection：
  - 禁止 direct push
  - 只允許 GitHub Actions Bot 推送（或只允許特定 workflow token）

> GitHub UI 中可以透過「Restrict who can push」和保護規則達成。

## 🖥️ 內網部署（推薦：Nginx 靜態站）

### 1) 只 checkout `viewer-data`

```bash
git clone git@github.com:ORG/REPO.git ctf-private
cd ctf-private
git checkout viewer-data
```

### 2) 用 Docker 跑 Nginx

在內網主機建立 `docker-compose.yml`：

```yaml
services:
  ctf-viewer:
    image: nginx:alpine
    ports:
      - "8088:80"
    volumes:
      - ./viewer/site:/usr/share/nginx/html:ro
      - ./viewer/data:/usr/share/nginx/html/data:ro
```

啟動：

```bash
docker compose up -d
# 瀏覽器打開 http://<host>:8088
```

> Viewer 的 `index.html` 會從 `/data/index.json` 與 `/data/progress.json` 讀取資料。

### 3) 自動更新（cron）

每分鐘更新一次 viewer-data：

```bash
cd /path/to/ctf-private
git fetch origin viewer-data
git reset --hard origin/viewer-data
docker compose restart
```

## 🧪 本地測試

在 `main` 上也可以本地生成資料：

```bash
python scripts/generate-viewer-data.py --clean --output viewer/data
python scripts/scan-secrets.py --path viewer --fail-on-high
```

然後在 repo root：

```bash
python -m http.server 8088
# 打開 http://localhost:8088/viewer/site/
```

## 🧾 附件顯示策略

- Viewer 只列出 `challenges/**/files/` 的檔名/大小/修改時間
- 不複製檔案內容到 `viewer-data`
- 不提供下載

## 🛠️ 常見問題

### Q: 為什麼 README 需要掃描 flag？
A: README 很可能被誤貼 flag 或敏感資訊，CI 會阻擋這種情況。

### Q: viewer-data 分支是否會包含題目程式碼？
A: 不會。生成腳本只複製 `public.yml` + `README.md` + 附件 metadata。
