# 👀 Viewer Data Spec (Internal Progress Viewer)

> 版本：v1.0  
> 更新日期：2026-01-18  
> 目的：在 **Private Dev Repo** 中，自動產生一個 **CI 管理的 `viewer-data` 分支**，提供「只讀題目進度」網站（純靜態 HTML + Vanilla JS），**不顯示題目程式碼與 flag**。

---

## 1. Goals / Non-Goals

### Goals

- 用同一個 repo 內的 `viewer-data` 分支提供題目進度 Viewer
- Viewer 只讀、內網不登入即可看
- Viewer 顯示：
  - 題目列表（分類、難度、狀態、owners/assignee、更新時間）
  - 每題 `README.md`（來源：`challenges/**/README.md`）
  - 每題 `public.yml`（去敏後）
  - 附件列表（只列 `challenges/**/files/` 檔名/大小/時間，不提供下載）
- `viewer-data` 分支完全由 CI 生成與更新（CI-managed）
- 生成流程必須做 secrets scan，發現 flag/敏感資訊即阻擋更新

### Non-Goals

- Viewer 不提供建立/編輯題目（create/edit 留在 Admin GUI/CLI）
- Viewer 不提供檔案下載（附件僅列出 metadata）
- Viewer 不提供題目程式碼瀏覽（不複製 src/docker/writeup/solution）

---

## 2. Repository Model

### Branches

- `main`：Private Dev 主幹（完整題目開發內容）
- `challenge/<category>/<name>`：每題一個 feature branch（開發者）
- `viewer-data`：只讀 Viewer artifact（CI-managed，純靜態站 + 資料）

### Data Flow

1. 開發者在 `challenge/<category>/<name>` 開發 → 開 PR → merge 到 `main`
2. GitHub Actions 在 `main` 觸發 viewer 產生器
3. 生成 `viewer/` 內容後進行 secrets scan
4. 將 `viewer/` push 到 `viewer-data` 分支
5. 內網服務只需 checkout `viewer-data`，以 Nginx/靜態 server 提供網頁

---

## 3. Artifact Layout (viewer-data)

`viewer-data` 分支必須包含完整可運行的 Viewer 靜態站：

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

### Notes

- `viewer/site/`：前端靜態資產（CSS/JS/HTML）
- `viewer/data/`：由 `main` 生成的資料，供前端讀取

---

## 4. Source of Truth (main)

### Required per-challenge files

每題目必須至少包含：

- `challenges/<category>/<name>/public.yml`
- `challenges/<category>/<name>/README.md`

可選：

- `challenges/<category>/<name>/files/`（僅用於列出附件 metadata）

---

## 5. Metadata Spec

### 5.1 public.yml (per challenge)

最低要求欄位（Viewer 會用於統計/列表/篩選）：

```yaml
title: "SQL Injection 101"
category: "web"
difficulty: "easy"
author: "alice"

owners:
  - "alice"
  - "bob"
assignee: "alice"

status: "developing"        # planning|developing|testing|completed|deployed
ready_for_release: false
updated_at: "2026-01-18"
```

規則：

- `owners`、`assignee` 必須使用 GitHub username（不含 @ 或可帶 @，CI 會 normalize）
- `assignee` 必須出現在 `owners` 中

### 5.2 config.yml (quota)

- `challenge_quota`：全局配額（分類/難度/總數）
- `team_quota.by_member`：每人配額（可選 total / by_category / by_difficulty）

範例：

```yaml
challenge_quota:
  by_category:
    web: 6
    pwn: 6
  by_difficulty:
    baby: 8
    easy: 10
  total_target: 32

team_quota:
  by_member:
    alice:
      total: 6
      by_category: { web: 2, pwn: 1 }
      by_difficulty: { baby: 1, easy: 3, middle: 2 }
```

---

## 6. Viewer Dataset Schema

### 6.1 viewer/data/index.json

用途：題目列表、搜尋、點擊進入 detail。

Schema（概念）：

```json
{
  "generated_at": "2026-01-18T11:00:00Z",
  "items": [
    {
      "category": "web",
      "name": "sql_injection",
      "title": "SQL Injection 101",
      "difficulty": "easy",
      "status": "developing",
      "points": 100,
      "owners": ["alice"],
      "assignee": "alice",
      "ready_for_release": false,
      "author": "alice",
      "updated_at": "2026-01-18",
      "data_path": "data/challenges/web/sql_injection"
    }
  ]
}
```

### 6.2 viewer/data/progress.json

用途：Dashboard 指標、quota/狀態統計。

Schema（概念）：

```json
{
  "generated_at": "2026-01-18T11:00:00Z",
  "total": 32,
  "by_status": { "planning": 2, "developing": 10, "testing": 6, "completed": 12, "deployed": 2 },
  "by_category": { "web": {"count": 6, "quota": 6} },
  "by_difficulty": { "easy": {"count": 10, "quota": 10} },
  "by_member": { "alice": {"assigned": 6, "completed": 2, "quota_total": 6} },
  "quota": { "total_target": 32 }
}
```

### 6.3 viewer/data/challenges/.../files.json

用途：附件列表（只列不下載）。

```json
{
  "items": [
    { "name": "challenge.zip", "size": 12345, "modified_at": "2026-01-18T10:00:00Z" }
  ]
}
```

---

## 7. Security Requirements

### Hard Deny (must never appear in viewer-data)

- `private.yml` / `private.yaml`
- flag pattern：`${flag_prefix}{...}`（`flag_prefix` 由 `config.yml` 讀取）
- 敏感欄位：`flag`, `solution_steps`, `internal_notes`, `verified_solutions`, `secrets`, `password`, `token` 等
- 題目程式碼與解答：`src/`, `docker/`, `writeup/`, `solution/`, `exploit.py`, `solve.py`

### Defense in Depth

- 生成器只白名單複製 `public.yml` + `README.md`
- 生成 `public.yml` 會再做敏感 key 移除（即使誤寫進 public.yml 也會被剔除）
- 生成後對整個 `viewer/` 目錄執行 `scan-secrets.py`，fail-on-high

---

## 8. Automation (CI)

### 8.1 Generate Viewer Data Workflow

Workflow 檔：`.github/workflows/generate-viewer-data.yml`

觸發：
- push to `main`，路徑包含：
  - `challenges/**/public.yml`
  - `challenges/**/README.md`
  - `config.yml`
  - `viewer/site/**`
  - `scripts/generate-viewer-data.py`

步驟：

```bash
python scripts/generate-viewer-data.py --clean --output viewer/data
python scripts/scan-secrets.py --path viewer --fail-on-high
# push viewer/ -> viewer-data
```

### 8.2 CI-managed viewer-data

建議 GitHub 設定：
- `viewer-data` 分支保護：禁止 direct push
- 只允許 GitHub Actions bot 推送

---

## 9. PR Policy (Branch + Ownership)

Workflow 檔：`.github/workflows/pr-policy-check.yml`

規則：

- 分支命名必須符合：`challenge/<category>/<name>`
- 必須存在：
  - `challenges/<category>/<name>/public.yml`
  - `challenges/<category>/<name>/README.md`
- `assignee in owners`
- PR author 必須在 `owners` 中（或等於 assignee）
- 對 PR diff（排除 private.yml）做 flag pattern 快速掃描

---

## 10. Viewer Deployment (Internal)

### Recommended: Nginx static serving

Checkout `viewer-data`，用 Nginx 靜態站直接 serve：

```bash
git clone git@github.com:ORG/REPO.git ctf-private
cd ctf-private
git checkout viewer-data
```

`docker-compose.yml`（示例）：

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
# http://<host>:8088
```

自動更新（cron）：

```bash
cd /path/to/ctf-private
git fetch origin viewer-data
git reset --hard origin/viewer-data
docker compose restart
```

---

## 11. Implementation References (in this repo)

- Generator: `scripts/generate-viewer-data.py`
- Viewer static site: `viewer/site/index.html`, `viewer/site/assets/app.css`, `viewer/site/assets/app.js`
- CI workflow: `.github/workflows/generate-viewer-data.yml`
- PR policy: `.github/workflows/pr-policy-check.yml`
- Template updated: `challenge-template/public.yml.template`
- Deployment guide: `docs/viewer-deployment.md`
