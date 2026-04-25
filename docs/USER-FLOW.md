# 使用流程總覽

> 從 0 到題目上線的端到端教學。讀完一次就知道「下一步要做什麼」。

依角色 / 時機劃分：

- [Phase 0 — 一次性設置（admin）](#phase-0--一次性設置admin)
- [Phase 1 — 出題人日常](#phase-1--出題人日常)
- [Phase 2 — 驗題（任一隊友）](#phase-2--驗題任一隊友)
- [Phase 3 — 合併後的自動化](#phase-3--合併後的自動化)
- [Phase 4 — 比賽結束發布](#phase-4--比賽結束發布)
- [角色與權限對照](#角色與權限對照)
- [常見問題](#常見問題)

---

## Phase 0 — 一次性設置（admin）

新團隊起手只做一次。完成後就交給出題人各自開 branch。

### 0.1 建立 private repo

GitHub 進入 [is1ab/is1ab-CTF-template](https://github.com/is1ab/is1ab-CTF-template) → **Use this template** → **Create a new repository**：

- Owner：你的組織（如 `is1ab`）
- Repository name：`2026-is1ab-CTF`（範例）
- Visibility：⚠️ **Private**（重要！flag 還在裡面）

或用 `gh` CLI：

```bash
gh repo create is1ab/2026-is1ab-CTF \
  --template is1ab/is1ab-CTF-template \
  --private --clone
cd 2026-is1ab-CTF
```

### 0.2 安裝環境 + Git Hooks

```bash
uv sync
make setup            # 裝 pre-commit + pre-push hook、驗證環境
```

預期看到 `✅ 所有檢查通過!`。

### 0.3 啟動 `/setup` Wizard

```bash
cd web-interface
uv run python app.py
```

開瀏覽器 `http://localhost:8004/setup`，跟著走 5 步：

| Step | 路徑 | 你要填 |
|---|---|---|
| 1 | `/setup/project` | 競賽名稱、年份、`flag_prefix`、平台 URL（GZCTF / CTFd） |
| 2 | `/setup/team` | 團隊成員清單（github_username + 顯示名 + 專長） |
| 3 | `/setup/event` | 比賽起訖日、出題截止、驗題截止、凍結截止 |
| 4 | `/setup/quota` | 各類別 / 難度的目標題數 |
| 5 | `/setup/finalize` | ☑ 三個產生選項全勾 → 點紅色「執行」 |

第 5 步會自動產生：

- `.github/PULL_REQUEST_TEMPLATE.md`（雙 checklist：出題人 + 驗題人）
- `.github/CODEOWNERS`（留空 placeholder，不指派固定 reviewer）
- `.github/branch-protection.md`（GitHub 分支保護指引含 `gh` CLI 指令）

> Wizard 是 **idempotent** 的：之後想改 deadline 或加 member，再開 `/setup` 任一步就能改。

### 0.4 設定 GitHub Branch Protection

打開剛產生的 [.github/branch-protection.md](../.github/branch-protection.md)，照裡面說明任選一種方式設定：

- **網頁**：repo Settings → Branches → Add rule
- **CLI**：複製貼上裡面的 `gh api` 指令

關鍵規則：
- Require 1 approval（驗題人 approve）
- Require CI 通過（`validate-challenge` / `security-scan` / `docker-build`）
- Disallow force-push to main

### 0.5 設定 GitHub Secrets

去 Settings → Secrets and variables → Actions，加入：

- `PUBLIC_REPO_TOKEN` — 推到 public repo 用（Personal Access Token，需要 `repo` + `workflow` 權限）

詳細：[wiki/GitHub-Secrets-Setup.md](../wiki/GitHub-Secrets-Setup.md)

### 0.6 commit & push 初始化結果

```bash
git add config.yml .github/
git commit -m "chore: initial setup via /setup wizard"
git push origin main
```

把 repo URL 給每位出題人，他們各自 clone。

---

## Phase 1 — 出題人日常

每出一題重複以下流程。

### 1.1 一次性個人設定

每個出題人 clone 後做一次：

```bash
git clone https://github.com/is1ab/2026-is1ab-CTF.git
cd 2026-is1ab-CTF
git config user.name "你的名字"          # 重要！create-challenge 會抓這個當 author
git config user.email "you@example.com"
make setup                                # 裝個人本地的 hooks
```

### 1.2 開分支建題

```bash
# 同步主分支
git checkout main && git pull

# 開分支（命名規範：challenge/<分類>/<題名>）
git checkout -b challenge/web/sql_injection_101

# 跑建題精靈（author 自動從 git config user.name 抓）
make new-challenge ARGS="web sql_injection_101 easy"
```

格式：`make new-challenge ARGS="<category> <name> <difficulty>"`

- `category`：web / pwn / crypto / reverse / forensic / misc / general
- `difficulty`：baby / easy / middle / hard / impossible

也可手動覆蓋 author：

```bash
make new-challenge ARGS="web demo easy --author Alice"
```

> Author 解析優先序：`--author` > `git config user.name` > `config.yml` 的 `team.default_author`

產生的目錄：

```
challenges/web/sql_injection_101/
├── private.yml      # 🔒 含 flag、解答、internal notes（永遠不公開）
├── public.yml       # 📢 公開資訊（會同步到 public repo）
├── README.md        # 題目描述
├── src/             # 你的原始碼
├── docker/          # Docker 設定（如有）
├── solution/        # 官方解法（不公開）
├── writeup/         # 賽後 writeup
└── files/           # 給參賽者下載的附件
```

### 1.3 編輯題目

**填 flag**（最重要）：編輯 `private.yml`：

```yaml
flag: "is1abCTF{your_real_flag_here}"
```

**填題目資訊**：編輯 `public.yml`：

```yaml
title: "SQL Injection 101"
description: |
  這是一題基礎 SQL Injection，連線資訊：http://challenge.is1ab.com:8001
tags: [web, sql, beginner]
hints:
  - cost: 0
    content: 試試 UNION SELECT
  - cost: 50
    content: 資料庫是 MySQL
```

**寫 source / Docker / writeup**：在對應目錄下開發。完整參考：

- [docs/challenge-types-guide.md](challenge-types-guide.md) — 五種題目類型骨架
- [wiki/Challenge-Development.md](../wiki/Challenge-Development.md) — 各分類開發詳解
- [docs/challenge-metadata-standard.md](challenge-metadata-standard.md) — YAML 欄位規格

> ⚠️ **絕對不要在 `public.yml` 寫真 flag！** Git hooks 會擋。

### 1.4 本地驗證

```bash
make validate ARGS="challenges/web/sql_injection_101"
make scan
```

預期：
- `✅ Validation passed`
- 無 CRITICAL / HIGH 安全問題

如果題目要 Docker：

```bash
cd challenges/web/sql_injection_101/docker
docker compose up -d
# 自己在瀏覽器試解一次
docker compose down
```

### 1.5 提交 PR

```bash
git add challenges/web/sql_injection_101/
git commit -m "feat(web): add sql_injection_101"
git push -u origin challenge/web/sql_injection_101
```

> Pre-commit hook 會在 commit 時掃 flag 洩漏 + 敏感檔。
> Pre-push hook 在 push 時再掃一次。被擋的話照訊息修。

GitHub 上會跳出 **Compare & pull request**，點下去：

- 標題會自動帶 commit message
- 描述會自動套用 PR template（雙 checklist）
- **填好「出題人 Checklist」**（六項打勾）
- 點 **Create pull request**

### 1.6 等 CI + 驗題

PR 開出後 GitHub Actions 自動跑：

| Check | 失敗怎麼辦 |
|---|---|
| `validate-challenge` | 修 `public.yml` 格式 |
| `security-scan` | 移除公開檔案中的 flag |
| `docker-build`（如有） | 修 Dockerfile |
| `pr-policy-check` | 確認分支命名 `challenge/<cat>/<name>` |

CI 全綠後等驗題人來看（見 Phase 2）。

---

## Phase 2 — 驗題（任一隊友）

**沒有固定指派**。誰有空、看到 PR 在 queue 裡就拉下來看。

### 2.1 接驗題

在 GitHub PR 頁面看「**驗題人 Checklist**」，把分支拉下來：

```bash
git fetch origin challenge/web/sql_injection_101
git checkout challenge/web/sql_injection_101
```

### 2.2 實際解題

依題目類型不同：

**Web / PWN（要起服務）**：

```bash
cd challenges/web/sql_injection_101/docker
docker compose up -d
# 嘗試解題、拿到 flag
docker compose down
```

**Crypto / Reverse / MISC（附件解題）**：

```bash
cd challenges/web/sql_injection_101
ls files/                            # 看給參賽者的檔案
# 用題目給的線索試解
cat solution/                        # 比對官方解法
```

### 2.3 比對 flag

解出來的 flag 是否等於 `private.yml` 的 `flag` 欄位？

```bash
grep "^flag:" challenges/web/sql_injection_101/private.yml
```

### 2.4 在 PR 上 review

回 GitHub PR，把 **驗題人 Checklist** 一條條打勾：

- [x] 已 git checkout 此 branch
- [x] 已成功 build / 起服務
- [x] 已實際解出 flag，且與 private.yml 一致
- [x] 難度標示與實際解題感受一致
- [x] 提示（hints）合理、不直接洩答
- [x] 無公開資料中夾帶 flag

留 comment 補充任何發現的問題。

點 **Approve**（綠勾）→ 出題人或 admin 可以 merge。

或者點 **Request changes**（紅圈）→ 出題人修正後重 push。

### 2.5 Merge

CI 通過 + 至少 1 approval → **Squash and merge** 進 main。

---

## Phase 3 — 合併後的自動化

PR 合到 main，GitHub Actions 自動：

1. **README 更新** — `update-readme.yml` 掃所有 `public.yml`，重算統計、更新進度表，自動 commit
2. **Viewer 資料生成** — `generate-viewer-data.yml` 重算內部進度 viewer 的 JSON
3. **Dashboard 統計** — Web GUI 的 dashboard 即時反映新題

不用手動做任何事。

詳細工作流程：[.github/workflows/](../.github/workflows/)

---

## Phase 4 — 比賽結束發布

比賽結束後 admin 操作。

### 4.1 更新題目狀態

批次把所有題目的 `public.yml` 改為：

```yaml
status: "deployed"
ready_for_release: true
```

或在 `config.yml` 開啟 writeup：

```yaml
public_release:
  include:
    writeups: true
```

```bash
git add . && git commit -m "chore: prepare for public release"
git push origin main
```

### 4.2 觸發 Build Public Release

GitHub Actions → **Build Public Release** → **Run workflow**：

- target_repo：`is1ab/2026-is1ab-CTF-public`（要先建好 public repo）
- include_writeups：`true`
- force_rebuild：`true`

或推送到 main 也會自動觸發（如果 `auto_sync.enabled: true`）。

### 4.3 自動執行的步驟

`build.sh` 會：

1. 複製 `challenges/` → `public-release/`
2. **刪除** `private.yml` / `solution.py` / `flag.txt` / 等敏感檔
3. **過濾** `public.yml` 中的敏感欄位（`flag` / `internal_notes` / `validation_status` 等）
4. 二次 `scan-secrets` 確認沒漏網之魚
5. 推到 public repo + 建立 GitHub Release

### 4.4 GitHub Pages 自動部署

Public repo 收到 push 後，`deploy-pages.yml` 自動：

1. 跑 `generate-pages.py` 生成靜態 HTML
2. 部署到 `https://is1ab.github.io/2026-is1ab-CTF-public/`
3. 部署後再次掃 flag 洩漏

完成 — 公開網站上線。

---

## 角色與權限對照

| 角色 | 權限 | 主要工作 |
|---|---|---|
| **Admin** | repo owner、Settings、Secrets | 跑 0.1–0.6 設置、最後 4.x 發布 |
| **出題人** | write 權限 | 1.1–1.5（個人 branch 出題、提 PR） |
| **驗題人** | write 權限 | 2.x（任一團隊成員，不固定指派） |
| **CI bot** | GitHub Actions 自動 | Phase 3 自動更新 README / dashboard |

> 「**出題人 = 驗題人 = 任一團隊成員**」是這套流程的核心精神 — 不指派固定角色，誰會解誰來驗。

---

## 常見問題

### Q: `make new-challenge` 說「無法決定出題人」

A: 沒設 `git config user.name`、`config.yml` 也沒填 `team.default_author`、又沒帶 `--author`。任一方式設一個即可：

```bash
git config user.name "Alice"
# 或
make new-challenge ARGS="web demo easy --author Alice"
```

### Q: PR 一直沒人驗題怎麼辦？

A: 在 PR 上 @ 整個團隊，或在 chat（Slack / Discord）發一句「有空的人幫我驗 PR #X」。沒有「分配機制」是刻意的 — 規模夠小時這比指派更輕量。

### Q: 我想看「目前還有誰在出題、進度多少」

A: 啟動 web-interface 看 dashboard：

```bash
cd web-interface && uv run python app.py
# 開 http://localhost:8004
```

或看 README — 自動更新的進度表會列出每個題目狀態。

### Q: 有舊版題目含 `validation_status` / `reviewer` 欄位怎麼辦？

A: 在 `/setup/finalize` 頁面，會自動偵測並顯示「偵測到 N 個檔案」。勾選清理 + 紅色 confirm 按鈕，會用 `cleanup-validation-fields.py` 清掉。

也可以手動跑 CLI：

```bash
uv run python scripts/cleanup-validation-fields.py --dry-run     # 先看會改什麼
uv run python scripts/cleanup-validation-fields.py --apply       # 實際執行
```

### Q: pre-commit hook 把我的合法檔案擋住了

A: 看 hook 訊息。如果是 flag 誤判，照 `make scan` 報告排除。如果真的需要繞過（例如 fixture 檔），用：

```bash
git commit --no-verify -m "..."
```

但 99% 情況不需要 — hook 攔下的多半是真的問題。

### Q: 比賽期間想預先讓部分題目公開嗎？

A: 不建議。`build.sh` 是「全部一起發布」設計。要分批請另開 public repo 並手動同步。

---

## 相關文件

- [QUICKSTART.md](../QUICKSTART.md) — 30 分鐘從 clone 到 PR 的最小教學
- [docs/ctf-challenge-workflow.md](ctf-challenge-workflow.md) — 三階段流程詳解（含 Mermaid 圖）
- [docs/authoring-challenges.md](authoring-challenges.md) — CLI vs Web 雙管道建題
- [docs/challenge-metadata-standard.md](challenge-metadata-standard.md) — YAML 欄位規格
- [docs/security-checklist.md](security-checklist.md) — 安全檢查清單
- [docs/troubleshooting.md](troubleshooting.md) — 常見問題排查
- [wiki/](../wiki/) — 進階主題（Hints、部署、GPG 簽名等）
