# 出題與驗題：CLI 與 Web GUI 雙管道

本專案支援**兩種方式**建立題目目錄與雛形：**命令列**（`scripts/create-challenge.py`）與 **Web 管理介面**（`web-interface/`）。兩者都會產生 `private.yml` + `public.yml`（欄位說明見 `docs/challenge-metadata-standard.md`）；驗題透過 GitHub PR review 進行（見第 4 章）。

## 1. 事前設定（團隊與配額）

在專案根目錄編輯 `config.yml`：


| 區塊                    | 用途                                                                    |
| --------------------- | --------------------------------------------------------------------- |
| `team.default_author` | 預設**出題人**；Web 表單會帶入此值；CLI 未帶 `--author` 時使用                           |
| `team.members`        | 團隊成員清單（github_username + display_name + specialty）；wizard 第 2 步維護              |
| `challenge_quota`     | 各**類型**（`by_category`）與各**難度**（`by_difficulty`）的**題目數量**計畫，供儀表板與建題時對照 |
| `event`               | **舉辦時間與死線**：開始/結束、出題截止、驗題截止、凍結截止；新專案建議先填，Web 也會提示 |


完成後再進行單題建立，避免作者／審查者資訊缺漏。

## 2. 方式 A：Web GUI

### 2.1 啟動

```bash
cd web-interface
uv sync
uv run python app.py
```

瀏覽器開啟 `http://localhost:8004`（詳見 `web-interface/USAGE.md`）。

### 2.2 建題步驟

1. 開啟導航列 **「創建挑戰」**（`/create`）。
2. 依表單填寫：**名稱、說明、類別、難度、分數、出題人、驗題人、題目類型** 等。
  - 出題人可仰賴 `team.default_author` 預填。
3. 送出後會在 `challenges/<category>/<name>/` 建立目錄與雛形。
4. 在本機實作題面、測試後，提 PR 由團隊成員 review（見第 4 章）。

> Web GUI 僅作開發團隊內部使用；正式環境請加認證與 HTTPS（見 `wiki/Web-GUI-Integration.md`）。

## 3. 方式 B：CLI

在**專案根目錄**執行（須能讀寫 `challenges/`）：

```bash
uv run python scripts/create-challenge.py <category> <name> <difficulty> \
  --author "出題人"
```

- `--author` 可省，則依序使用 `config.yml` 的 `team.default_author`，或 `git config user.name`（兩者皆空則**失敗**）。
- `--type` 可指定題目類型，否則依分類推斷（與舊行為相同）。

產生結構與 Web 建題一致。

## 4. 驗題流程

驗題透過 **GitHub Pull Request review** 進行：

1. 出題人推 branch 並開 PR
2. 任一其他團隊成員自願擔任驗題人，將 branch checkout 到本地
3. 跑起 Docker / 解題、確認 flag 與 `private.yml` 一致
4. 在 PR 上 approve（或留言請出題人修正）
5. CI 通過 + 至少 1 approval → 可 merge

PR template 提供雙 checklist（出題人填一份、驗題人填一份），由 `/setup` 精靈產生於 `.github/PULL_REQUEST_TEMPLATE.md`。

驗題人**不固定指派**：CODEOWNERS 留空、不強制特定路徑由特定人審。

## 5. 相關文件

- `web-interface/USAGE.md` — 介面啟動與 `/setup` 精靈說明
- `wiki/Web-GUI-Integration.md` — Web 與安全流程的關係
- `docs/ctf-challenge-workflow.md` — 整體 CTF 工作流程
- `docs/challenge-metadata-standard.md` — YAML 欄位規範
- `.github/branch-protection.md` — branch protection 設定指引（由 `/setup` 產生）

