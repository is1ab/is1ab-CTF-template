# 出題與驗題：CLI 與 Web GUI 雙管道

本專案支援**兩種方式**建立題目目錄與雛形：**命令列**（`scripts/create-challenge.py`）與 **Web 管理介面**（`web-interface/`）。兩者都會產生 `private.yml` + `public.yml`，並寫入出題人、驗題人、驗題狀態等欄位（見 `docs/challenge-metadata-standard.md`）。

## 1. 事前設定（團隊與配額）

在專案根目錄編輯 `config.yml`：


| 區塊                    | 用途                                                                    |
| --------------------- | --------------------------------------------------------------------- |
| `team.default_author` | 預設**出題人**；Web 表單會帶入此值；CLI 未帶 `--author` 時使用                           |
| `team.reviewers`      | 建議**驗題人**名單（GitHub 帳號或慣用暱稱）；Web 表單以 datalist 建議、可手改                   |
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
  - 驗題人為**必填**；可從 `team.reviewers` 建議名單選取或自填。
3. 送出後會在 `challenges/<category>/<name>/` 建立目錄，並寫入 `validation_status: pending`。
4. 在本機實作題面、測試後，到 **「驗題」**（`/validation`）對該題執行 **通過** / **退回** / **改回待驗**（需輸入執行人與可選備註）。

> Web GUI 僅作開發團隊內部使用；正式環境請加認證與 HTTPS（見 `wiki/Web-GUI-Integration.md`）。

## 3. 方式 B：CLI

在**專案根目錄**執行（須能讀寫 `challenges/`）：

```bash
uv run python scripts/create-challenge.py <category> <name> <difficulty> \
  --author "出題人" \
  --reviewer "驗題人"
```

- `--author` 可省，則使用 `config.yml` 的 `team.default_author`（兩者皆空則**失敗**）。  
- `--reviewer` 可省，則使用 `team.reviewers` 的**第一位**（清單為空則**失敗**）。  
- `--type` 可指定題目類型，否則依分類推斷（與舊行為相同）。

產生結構與 Web 建題一致，含 `validation_status: pending` 與 `reviewer` 欄位。

## 4. 驗題與欄位說明

- `**author`**：出題人。  
- `**reviewer**`：指派之驗題負責人（團隊約定，非參賽者介面用語）。  
- `**validation_status**`：可為 `pending`、`approved`、`rejected` 等，同步於 `public.yml`（`internal_validation_notes` 僅在 `private.yml`）。  
- 舊題目若沒有 `validation_status`，不會出現在 Web「驗題」清單；若要把舊題納入流程，可手動在 `public.yml` 加上 `validation_status: pending` 與 `reviewer` 欄位。

## 5. 相關文件

- `web-interface/USAGE.md` — 介面啟動與目錄說明  
- `wiki/Web-GUI-Integration.md` — 與安全流程、權限建議  
- `docs/ctf-challenge-workflow.md` — 整體 CTF 工作流程  
- `docs/challenge-metadata-standard.md` — YAML 欄位規範（請同步維護）

