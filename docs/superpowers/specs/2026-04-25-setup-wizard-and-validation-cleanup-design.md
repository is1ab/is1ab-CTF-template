# Spec: 簡化驗題流程 + Web 初始化精靈

- **Date**: 2026-04-25
- **Status**: Approved (Brainstorming)
- **Owner**: guan4tou2
- **Related**: `web-interface/`, `scripts/create-challenge.py`, `config.yml`, `docs/`

---

## 1. 背景

`is1ab-CTF-template` 是一個 GitHub Template repo，給 CTF 出題團隊複製成 private repo 後協作開發題目，比賽結束再透過 build 流程過濾敏感資料、推到 public repo 與 GitHub Pages。

目前 working tree 中（尚未 commit）有兩條未完成的設計線：

1. **驗題機制**：在 `private.yml` / `public.yml` 中加入 `reviewer` / `validation_status` / `internal_validation_notes` 三個欄位，並在 Web GUI 加入 `/validation` 分頁、CLI `--reviewer` 必填。
2. **初始化引導**：在 Web GUI 加入 `/setup` 頁面，並在 `config.yml` 加入 `event` 與 `team.authors`。

問題：

- (1) 與團隊真實流程不對齊。團隊每位成員各自出題、不做傳統意義的 Code Review；唯一的 review 動作是「**驗題**」（驗題人 = 任一其他成員，不固定指派，把 branch 拉下來實際解題）。在 YAML 維護驗題狀態，會跟 GitHub PR approval 變成兩套要同步的事實，徒增同步成本。
- (2) 範圍模糊。`config.yml` / `CODEOWNERS` / GitHub Settings / Secrets 散落，缺一個單一入口讓新團隊「跟著走完就好」。

## 2. 目標

1. **砍掉冗餘的驗題機制**：`reviewer` / `validation_status` / `internal_validation_notes` / Web `/validation` / CLI `--reviewer` 全部移除。**PR approval 是 single source of truth**。
2. **新增 `/setup` 5 步驟初始化精靈**：填完 `config.yml` + 產生 `.github/` 模板 + 一鍵清理冗餘欄位。**可重複進入**當作設定中心（idempotent）。
3. **修正建題 author 來源順序**：`--author` flag > `git config user.name` > `team.default_author`（目前是反序）。

## 3. 非目標（Out of Scope）

- 配額（`challenge_quota`）的 CI enforcement
- 死線（`event.*_deadline`）的 CI enforcement
- 透過 GitHub API 自動套用 branch protection（風險過高，沿用「文件 + `gh` CLI 步驟」）
- 為 Web GUI 加 auth / HTTPS（沿用現狀，內部使用）
- 「待驗 PR 儀表板」讀 GitHub API（之後可選增）

## 4. Decisions Log

| # | 決策點 | 結論 | 推翻的選項 |
|---|--------|------|-----------|
| 1 | 焦點 | B 初始化精靈，但連動驗題流程簡化 | A / C / D |
| 2 | 驗題模型 | PR review = 驗題（無固定指派） | 模型 1（Code Review = 驗題）、模型 2（兩階段） |
| 3 | working tree 處置 | 路線 X：大砍特砍 | 路線 Y（保留欄位由 Action 自動寫）、Z |
| 4 | `/setup` 範圍 | (b) config.yml + 產生 `.github/` 模板 | (a) 太薄、(c) 多餘、(d) 風險高 |
| 5 | UX 形狀 | A2 + B2：多步驟 wizard、永遠可重入 | A1+B1 / A1+B2 / A2+B1 |
| 6a | `team.members` schema | (c) `github_username` + `display_name` + `specialty` | (a)(b) |
| 6b | CODEOWNERS | (a) 產生但留空 placeholder | (b)(c) |
| 6c | PR template | (a) 雙 checklist（出題人 + 驗題人） | (b)(c) |
| 6d | 清理冗餘欄位觸發 | (a) wizard 最後一步紅色 confirm | (b)(c) |

## 5. Architecture

```
Web UI (Flask, web-interface/app.py)
├── /setup/<step>          ← 5 步驟精靈（新）
│   ├── /setup/project     step 1: 專案基本資訊
│   ├── /setup/team        step 2: 團隊成員
│   ├── /setup/event       step 3: 比賽時程
│   ├── /setup/quota       step 4: 配額目標
│   └── /setup/finalize    step 5: review + 產生 .github + 清理冗餘
├── /                      ← Dashboard（不變）
├── /create                ← 建題（移除 reviewer 欄位）
├── /challenges, /settings ← 不變
└── /validation            ← ❌ 刪除

Backend services（純函數，與 Flask request 無耦合）
├── load_config() / save_config()        既有
├── generate_pr_template(config) → str   新
├── generate_codeowners(config) → str    新
├── generate_branch_protection_doc(config) → str  新
├── detect_legacy_validation_fields(challenges_root) → list[Path]  新
└── cleanup_legacy_validation_fields(challenges_root, dry_run=True) → ChangeReport  新

Scripts
├── scripts/create-challenge.py           改：移除 --reviewer、author fallback 順序反轉
└── scripts/cleanup-validation-fields.py  新：CLI 等價物
```

每個單元邊界明確：
- **Wizard 步驟**：表單 + POST handler，獨立可測（給定 form input → 斷言 `config.yml` 變化）
- **`.github/` 產生函數**：純函數，不依賴 Flask request
- **清理函數**：純函數，可獨立 CLI 呼叫，dry-run 與 apply 兩種模式

## 6. UX Flow

### 6.1 Wizard 5 步驟

每一步**讀現有 `config.yml` 預填**（idempotent）。Sidebar 顯示 5 步進度條，每步狀態：未填 / 部分填 / 完成。可任意跳到任一步。

| Step | 路徑 | 收集 | 寫入位置 |
|------|------|------|---------|
| 1 | `/setup/project` | `project.name`、`project.year`、`project.organization`、`project.flag_prefix`、`project.description`、`platform.gzctf_url`、`platform.ctfd_url`、`platform.zipline_url`、`deployment.host`、`deployment.docker_registry` | `config.yml` 對應 path |
| 2 | `/setup/team` | 動態列表（add/remove rows），每筆 `{github_username, display_name, specialty}`；另外 `default_author`（fallback 用，建議空著） | `config.yml` 的 `team.members[]` 與 `team.default_author` |
| 3 | `/setup/event` | `start_date`、`end_date`、`authoring_deadline`、`review_deadline`、`freeze_deadline`（HTML date input） | `config.yml` 的 `event.*` |
| 4 | `/setup/quota` | `by_category`（7 類別）、`by_difficulty`（5 難度）、`total_target`；UI 顯示「目前題數 / 目標」對照 | `config.yml` 的 `challenge_quota.*` |
| 5 | `/setup/finalize` | review 全部設定、選擇要產生的 `.github/` 檔案（checkbox）、顯示偵測到 N 題冗餘欄位、紅色 Confirm 按鈕 | 產生 `.github/`、批次清理 `challenges/` |

### 6.2 Idempotent 行為

- 進入任一步：`load_config()` 預填表單；空值 / 預設值欄位左邊顯示灰色「尚未設定」標籤
- step 5 的「清理冗餘」按鈕：先掃 `challenges/` 顯示「偵測到 N 題」；若 N=0 則灰色禁用
- 完成後 `/setup` 不會「鎖住」，使用者可隨時回來改

### 6.3 進度條判定

每步「完成」的判定（顯示綠色勾勾）：

- step 1: `project.name` 與 `project.flag_prefix` 非空（其他可選）
- step 2: `team.members` 至少 1 筆且每筆 `github_username` 非空
- step 3: `start_date` 與 `end_date` 非空
- step 4: `total_target > 0` 且 `by_category` 至少一個 > 0
- step 5: `.github/pull_request_template.md` 與 `.github/CODEOWNERS` 存在且偵測到的冗餘欄位 = 0

## 7. Data Model 變更

### 7.1 `config.yml` schema 變更

**新增** `team.members[]`：

```yaml
team:
  members:
    - github_username: "alice"
      display_name: "Alice Chen"
      specialty: "web"
    - github_username: "bob"
      display_name: "Bob Lin"
      specialty: "pwn"
  default_author: ""    # 保留作 author 的最後 fallback
```

**移除**：
- `team.reviewers`（語意被 `team.members` 取代）
- `team.authors`（語意被 `team.members` 取代）

**Backward compat**（在 `save_config()` 中）：若舊 config 仍有 `team.reviewers` / `team.authors`，自動 merge 到 `team.members`（`display_name` 暫設為 `github_username`、`specialty` 留空），日誌提示「已遷移舊欄位」。

### 7.2 `private.yml` / `public.yml` schema 變更

**移除**三個欄位：
- `reviewer`
- `validation_status`
- `internal_validation_notes`

### 7.3 `config.yml` 的 `security.sensitive_yaml_fields` 變更

把這三個欄位也加進敏感欄位清單，作為**防呆**：即使有舊題目漏清，build.sh 走 public release 流程時也會自動過濾。

## 8. `.github/` 產生物（step 5）

### 8.1 `.github/pull_request_template.md`（新建/覆蓋）

```markdown
## 題目資訊
- **Category**:
- **Difficulty**:
- **Title**:

## 出題人 Checklist（提 PR 前自我檢查）
- [ ] `private.yml` 已填妥 flag
- [ ] `public.yml` 描述清晰、無 spoiler
- [ ] 本機 `make validate` 通過
- [ ] 本機 `make scan` 無 CRITICAL/HIGH
- [ ] Docker（如有）`docker compose up` 可起、可解
- [ ] Writeup 已撰寫

## 驗題人 Checklist（review 時填寫）
- [ ] 已 `git checkout` 此 branch
- [ ] 已成功 build / 起服務
- [ ] 已實際解出 flag，且與 `private.yml` 一致
- [ ] 難度標示與實際解題感受一致
- [ ] 提示（hints）合理、不直接洩答
- [ ] 無公開資料中夾帶 flag

## 備註
<!-- 驗題遇到的問題、來回討論 -->
```

### 8.2 `.github/CODEOWNERS`（新建/覆蓋）

```
# 留空：本專案不指派固定 reviewer，任一團隊成員 approve 即可。
# 若需特定路徑由特定人審，自行加規則。
# 範例：
# /challenges/web/   @alice
```

### 8.3 `.github/branch-protection.md`（新建，僅文件）

純 markdown 步驟 + `gh` CLI 一鍵指令；**不**自動套用：

- 啟用 main branch protection
- Require 1 approval
- Require CI 通過（validate-challenge、security-scan、docker-build）
- Disallow force-push to main
- 包含 `gh api` / `gh repo edit` 指令範例

## 9. 清理冗餘欄位（step 5）

### 9.1 範圍

掃 `challenges/**/private.yml` 與 `challenges/**/public.yml`，移除三個 key（若存在）：
- `reviewer`
- `validation_status`
- `internal_validation_notes`

不動 `challenge-template/`（模板）。

### 9.2 實作

- 用既有的 **PyYAML**（已在 `pyproject.toml`）
- 兩種模式：
  - `dry_run=True`：回傳 `ChangeReport`（哪些檔案會改、會移除哪些 key），不寫檔
  - `dry_run=False`：實際寫檔，回傳 `ChangeReport`
- Web step 5 先 dry-run 顯示「將修改 N 個檔案」，使用者按紅色 Confirm 才呼叫 apply

**Trade-off**：PyYAML round-trip 會去除原本的 YAML comment。對 `challenges/**/private.yml`、`public.yml` 而言可接受（這兩個檔案多半由 `create-challenge.py` 產生、無 comment）；若未來發現有題目加了重要 comment，再評估是否引入 `ruamel.yaml`。

### 9.3 CLI 等價形式

```bash
uv run python scripts/cleanup-validation-fields.py --dry-run
uv run python scripts/cleanup-validation-fields.py --apply
```

## 10. `create-challenge.py` 變更

- **移除** `--reviewer` 參數與相關必填檢查
- **author 解析順序**改為：
  1. `--author` flag（最高優先）
  2. `git config --get user.name`
  3. `config.yml` 的 `team.default_author`（最後備援）
  4. 三者皆無 → 錯誤訊息「請設定 git user.name 或在 config.yml 填 team.default_author」
- **`private.yml` 模板**移除 `reviewer` / `validation_status` / `internal_validation_notes` 三鍵
- 既有的目錄結構建立、Docker 模板、writeup 框架不動

## 11. 移除的 Web 路由與檔案

- `/validation` GET 與 POST handlers（在 `web-interface/app.py`）
- `web-interface/templates/validation.html`
- 導航列「驗題」連結（`web-interface/templates/base.html`）

## 12. 文件更新

| 檔案 | 動作 |
|------|------|
| `docs/authoring-challenges.md` | 改寫「驗題」段落：用 PR review 方式描述，移除 `/validation` 分頁說明 |
| `docs/challenge-metadata-standard.md` | revert 三個欄位的新增 |
| `web-interface/USAGE.md` | 移除驗題分頁說明，加入 `/setup` 介紹 |
| `wiki/Web-GUI-Integration.md` | 同上 |
| `docs/ctf-challenge-workflow.md` | 階段 2.3 從「Code Review」改名「驗題」，描述更新 |
| `README.md` 初始化檢查清單 | 第一項改為「進入 Web `/setup` 完成設定」 |

## 13. 測試策略

### 13.1 Unit tests

- `tests/test_setup_helpers.py`
  - `generate_pr_template(config)` → 比對固定字串 fixture
  - `generate_codeowners(config)` → 比對固定字串 fixture
  - `generate_branch_protection_doc(config)` → 比對固定字串 fixture
  - `detect_legacy_validation_fields(fixture_path)` → 找到 N 個檔案
  - `cleanup_legacy_validation_fields(fixture_path, dry_run=True)` → 確認 ChangeReport 正確、檔案未變更
  - `cleanup_legacy_validation_fields(fixture_path, dry_run=False)` → 確認檔案內容已移除三個 key、其餘 key 與 comment 保留

### 13.2 Integration tests

- `tests/test_setup_flow.py`：起 Flask test client
  - GET `/setup/project` → 200，表單預填正確
  - POST `/setup/project` → `config.yml` 內容更新
  - GET `/setup/team` → 200，預填 members
  - POST `/setup/team` 加減 member → `config.yml` `team.members` 變化
  - GET `/setup/finalize` → 顯示偵測到的冗餘欄位數
  - POST `/setup/finalize` confirm → `.github/` 產生、`challenges/` 清理

### 13.3 Fixtures

- `tests/fixtures/legacy_challenge/private.yml`：含三個冗餘 key
- `tests/fixtures/legacy_challenge/public.yml`：含 `validation_status` key
- `tests/fixtures/clean_challenge/private.yml`：無冗餘 key（驗證 idempotent — apply 不應變更）

### 13.4 Backward compat tests

- 給定有 `team.reviewers` / `team.authors` 的舊 `config.yml`，呼叫 `load_config()` 後 `team.members` 自動填入。

## 14. 實作順序建議

1. **Phase 1：純函數層**（無 UI 改動，可獨立測試與 commit）
   - `generate_pr_template` / `generate_codeowners` / `generate_branch_protection_doc`
   - `detect_legacy_validation_fields` / `cleanup_legacy_validation_fields`
   - `scripts/cleanup-validation-fields.py` CLI
   - 單元測試
2. **Phase 2：CLI / metadata 清理**
   - `scripts/create-challenge.py` 移除 `--reviewer`、修正 author 順序
   - `config.yml` 的 `security.sensitive_yaml_fields` 加入三個欄位
   - revert `docs/challenge-metadata-standard.md` 中的新增段落
3. **Phase 3：Web `/setup` Wizard**
   - 5 個 route + 5 個 template
   - Sidebar 進度條 component
   - integration tests
4. **Phase 4：移除 `/validation` 與 reviewer UI**
   - 刪 `validation.html` / `app.py` 路由 / nav 連結
   - 從 `create_challenge.html` 移除 reviewer 欄位
5. **Phase 5：文件**
   - 6 份文件更新
   - README 檢查清單第一項改寫
6. **Phase 6：Backward compat**
   - `load_config()` 偵測舊 `team.reviewers` / `team.authors` 並 merge

每個 phase 結束後跑 `make validate-all` + `make test` 確認。

## 15. 風險與緩解

| 風險 | 影響 | 緩解 |
|------|------|------|
| 既有專案已 commit 帶 `validation_status` 的題目 | 升級時會看到突然出現的清理動作 | dry-run 預覽 + 紅色 Confirm；CLI 等價腳本可在 CI 中跑 |
| `team.reviewers` 被外部 workflow 引用 | 移除後 workflow 失效 | grep `.github/workflows/` 確認無引用；若有，更新 workflow 改讀 `team.members[].github_username` |
| Web GUI 沒 auth，任何人都能 trigger 清理 | 內部誤用 | 沿用現狀（README 已警告 GUI 內部使用）；清理前需要紅色 Confirm |
| YAML round-trip 去除 comment | 使用者若曾在 challenge YAML 加 comment 會丟失 | 多數題目 YAML 由腳本產生、無 comment；若未來真有需求再評估 `ruamel.yaml`（已在 9.2 註明） |

## 16. Open Questions

無 — 所有設計決策皆已透過 brainstorming 拍板。

## 17. 附錄：被砍掉的設計（為何留紀錄）

- **路線 Y（保留 `validation_status` 但用 GitHub Action 自動寫）**：被砍因為仍需要寫 Action、且資料 sync 仍是雙寫。若未來「離線環境也要看 review 紀錄」變成需求，可重啟此設計。
- **路線 d（用 GitHub API 自動套 branch protection）**：被砍因為 Web GUI 沒 auth、token 風險高。若未來加入 auth + token vault，可重啟。
- **模型 2（驗題與 Code Review 分開）**：被砍因為團隊沒 Code Review 角色。若團隊規模成長並引入 Code Review 角色，可重啟。
