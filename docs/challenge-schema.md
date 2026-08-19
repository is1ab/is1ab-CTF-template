# 題目 Schema 定案（canonical）

> **這份是單一真相（single source of truth）**。定案後將**取代** `docs/challenge-metadata-standard.md`，
> 並作為 `challenge-template/*.yml.template`、5 個範例、`is1ab_authoring` plugin、`validate-challenge.py`
> 對齊的基準。**本文件只定規格，尚未動任何碼**（實作待排期）。

## 設計原則

過去有**四套**互相打架的 schema（template / metadata-standard.md / examples / plugin）。定案方向：

1. **精簡優先。** 只保留「玩家需要」或「pipeline 真的據以動作」的欄位；純參考、純備註一律移出 schema，改寫進 `writeup/`。
2. **正交拆分。** 一個欄位只表達一件事：交付方式 ≠ flag 分發 ≠ flag 比對（見 §決策 1）。
3. **文件歸文件、碼歸碼。** 解題說明是**文件**（`writeup/`）與**可跑的碼**（`solution/exploit.py`），不塞進 YAML 清單。
4. **敏感資訊不進 repo/CTFd DB。** 密鑰屬 `.env`/secret manager（既有鐵律）。

---

## public.yml — canonical

### 必填

| 欄位 | 型別 | 合法值 / 說明 |
|---|---|---|
| `title` | str | 顯示給參賽者的題名 |
| `author` | str | 作者（GitHub username）。**唯一的人員欄位**（原 `owners`/`assignee` 已廢） |
| `difficulty` | str | `baby \| easy \| middle \| hard \| impossible` |
| `category` | str（**自由填寫**） | 不是固定 enum——作者自填，避免「值不在清單」硬失敗。表單給建議值 `web / pwn / reverse / crypto / forensic / misc / osint / general`，但**允許任意值**；存檔統一轉小寫，validator 對非建議值**只警告不擋**（見 §決策 8） |
| `description` | str（多行） | 給參賽者的題目說明 |
| `deploy_type` | str | `attachment \| container \| none`。**只講「有沒有服務」**（取代 `challenge_type`，見 §決策 1）。`none` = 純知識/quiz/OSINT，無部署無附件 |
| `source_code_provided` | bool | 是否附原始碼 |

> **連線方式在 `deploy_info.connection_type`**：真實題庫把 xinetd/frp 的 pwn 也叫「靜態容器」，`nc` 不是交付類型、只是「怎麼連」。
> 所以 `container` 題用 `deploy_info.connection_type`（`nc \| http \| https`）表達玩家怎麼連。
>
> **`files` 與 `deploy_type` 正交**：`container` 題也能附檔案（如 pwn 給 binary + 連線服務）。
> `attachment` 只用在「唯一交付物就是檔案」的題；有服務時用 `container`，附檔照樣放 `files`。

### 選填

| 欄位 | 型別 | 誰在讀 | 備註 |
|---|---|---|---|
| `points` | int | sync-to-ctfd、viewer | 未填由 config 預設 |
| `tags` | list[str] | sync、viewer、CTFd | |
| `files` | list[str] | build、release | 檔名清單，如 `["crackme"]` |
| `status` | str | viewer | `planning \| developing \| testing \| completed \| deployed` |
| `ready_for_release` | bool | build、release、scan | 預設 `false` |
| `created_at` / `updated_at` | str(date) | viewer | |
| `deploy_info` | map | sync、部署 | `port / url / requires_build / version / nc_port / timeout / connection_type / resources{memory,cpu}` |
| `hints` | list[{level,cost,content}] | sync、CTFd | |
| `allowed_files` | list[glob] | sync-to-public、prepare-public-release | 公開 repo 檔案白名單（有安全用途，保留） |

**已廢除（public）**：`owners`（→ 用 `author`）、`assignee`（指派是 PM/plugin DB 的事，不進 commit 的 YAML）、
`learning_objectives`、`required_skills`、`recommended_tools`、`references`、`metadata.*`（純參考，要寫就寫進 `writeup/`）。

---

## private.yml — canonical

> **不重複 public 的基本資訊**；一致性由 durable `id` 對齊，不靠複製。

### 必填

| 欄位 | 型別 | 合法值 / 說明 |
|---|---|---|
| `flag` | str **或 list[str]** | 實際 flag。**陣列 = 多個可接受 flag**（任一命中即解，用於替代答案 / 多階段）。`flag_match: regex` 時放 regex 本體；`flag_load: dynamic` 時放 template/generator 產出的樣式或種子來源 |

### flag 三軸（選填，皆有預設；三者正交，見 §決策 1）

| 欄位 | 合法值 | 預設 | 說明 |
|---|---|---|---|
| `flag_load` | `static \| dynamic` | `static` | 內建 vs 部署時從 `.env`/generator **注入** |
| `flag_scope` | `shared \| per_team` | `shared` | 統一（所有人同一）vs 唯一（每隊不同） |
| `flag_match` | `exact \| regex` | `exact` | 比對方式 → 對應 CTFd flag type |

> **約束**：`flag_scope: per_team` 隱含 `flag_load: dynamic`（唯一 flag 必然是注入的）。validator 應擋掉 `static + per_team`。
> **四種有效組合**：static+shared（經典內建）、dynamic+shared（部署注入但統一，可不重建就換 flag）、dynamic+per_team（每隊注入不同）、static+shared+regex（樣式比對）。

### 其他選填

| 欄位 | 型別 | 誰在讀 | 備註 |
|---|---|---|---|
| `dynamic_flag` | {template,salt} | 部署 | 僅 `flag_load: dynamic`；描述注入樣式/種子 |
| `internal_notes` | str | plugin | 開發筆記 |
| `testing` | {tested_by,last_tested,test_status} | viewer、update-readme | 驗題記錄 |

**已廢除（private）**：
- `solution_steps` → 移除。解題 = `solution/exploit.py`（可跑）+ `writeup/README.md`（文件）（見 §決策 4）。
- `flag_description` → 移除，writeup 已涵蓋 flag 位置/取法。
- `flag_type` → 拆成 `flag_mode` + `flag_match`（見 §決策 1）。
- `deploy_secrets` → 密鑰屬 `.env`/secret manager，不進 YAML、不進 CTFd DB。
- `test_credentials` → 若題目需要測試帳密，寫進 `writeup/`，不進 schema。
- `verified_solutions` / `test_cases` / `difficulty_assessment` / `known_issues` / `docker_internal` / `crypto_params` → 移除（實務已被 `solution/exploit.py` + `make verify-solution` 取代；個別範例自創欄位無人讀）。

---

## 解題與說明的歸屬（取代原本塞在 YAML 的欄位）

| 內容 | 放哪 | 格式 |
|---|---|---|
| 可自動驗證的官方解 | `solution/exploit.py` | 依 `verify-solution.py` 契約（`--connection-info`） |
| 給出題團隊的解題說明 / flag 位置 / 測試帳密 | `writeup/README.md` | Markdown 文件 |
| 學習目標 / 所需技能 / 推薦工具 / 參考資料 | `writeup/README.md`（想寫再寫） | Markdown，非 schema |

---

## 正交性：`deploy_type` × flag 三軸

交付方式與 flag 完全獨立——**靜態附件題也能配動態/每隊 flag**。舊的 5 個 `challenge_type` 其實就是這種硬編組合：

| 舊 `challenge_type` | 新表達（deploy_type + flag_load/flag_scope + connection_type） |
|---|---|
| `static_attachment` | `attachment` + static / shared |
| `dynamic_attachment` | `attachment` + dynamic / per_team（每隊不同附件，flag 烙進各自檔案） |
| `static_container` | `container` + static / shared |
| `dynamic_container` | `container` + dynamic / per_team |
| `nc_challenge` | `container` + `connection_type: nc` + static / shared（通常） |

> 注入的**機制**依交付方式而異（附件題靠 build/generator 產檔、容器題靠啟動注入/服務端），
> 但 schema 用同一組軸表達，不再為每種交付各開一個 enum。拆軸後還多出舊 enum 表達不了的組合（如 `dynamic`+`shared`、任意交付 × `regex`）。
> 真實 2025 題庫 30 題全落在 `container`/`attachment` 兩類、flag 全 static/shared——動態軸與 `none` 是留給未來的彈性。

## container 題 → k3s image build/push（build-images + sync-to-ctfd）

`deploy_type: container` 的題目由 CTFd 的 `k3s_challenges` 插件用 k3s pod 起容器，
所以同步前要先把題目 build 成 image、push 到私有 registry，sync 再把 image ref 指進去。

### registry 與 image ref

- **registry 位址**：`config.yml` 的 `deployment.docker_registry`，可用環境變數 `IS1AB_REGISTRY` 覆蓋。
- **image ref 慣例**：`{registry}/{category}/{slug}:{version}`
  - `slug` = 題目目錄名（轉小寫、docker 合法字元）
  - `version` = `deploy_info.version`（見下）
  - **registry 未設時**：退回純本地 tag `{category}/{slug}:{version}`，`build-images` 只 build 不 push（會警告，不會 crash）。

### `deploy_info.version`

| 欄位 | 型別 | 預設 | 說明 |
|---|---|---|---|
| `version` | str | `v1` | 即 image tag。**改 image（換底包、改題邏輯）時 bump**（`v1`→`v2`…），讓部署端拉到新版而不是吃到快取的舊 image。 |

### build-images（`make build-images ARGS="…"`）

只處理 `deploy_type == container` 且 `deploy_info.requires_build` 的題目，其餘略過：

```bash
make build-images                                  # build + push 全部（略過 examples/）
make build-images ARGS="--path challenges/web/x"   # 只做單一題目
make build-images ARGS="--dry-run"                 # 只印會做什麼，不呼叫 docker
make build-images ARGS="--no-push"                 # 只 build 不 push
```

build 慣例同範例 `docker/docker-compose.yml`（`context: ..`、`dockerfile: docker/Dockerfile`）：
context = 題目根目錄、dockerfile = `docker/Dockerfile`，即
`docker build -f <chal>/docker/Dockerfile -t <ref> <chal>`。

### sync-to-ctfd 的對接

`sync-to-ctfd` 遇到 `deploy_type == container` 會把題目建成 `type: k3s` 並帶上插件欄位
（`image` / `port` / `protocol` / `memory` / `cpu` / `flag_format`…）：

- `image` = 上述 image ref（與 build-images 同一套規則算出）
- `port` = `nc` 題用 `deploy_info.nc_port`，否則 `deploy_info.port`（都沒填就用插件預設 1337）
- `protocol` = `connection_type` 為 http/https → `http`，其餘（含 nc/pwn）→ `tcp`
- `memory` / `cpu` = `deploy_info.resources`（缺則不送、用插件預設）
- `flag_format` = `config.yml` 的 `project.flag_prefix` 組（例 `is1abCTF{%s}`）

其餘 k3s 欄位（`ttl_minutes`/`max_renews`/`flag_mode`/`flag_path`…）交給插件預設；
`attachment` / `none` 題維持 `type: standard`。**作者要覆蓋任何欄位，用 `public.yml` 的
`ctfd:` 區塊**（在 adapter 之後 merge，一律優先）。動態/每隊 flag 仍由插件發放，
`sync-to-ctfd` 不為 container 題建靜態 flag。

## 逐條衝突裁決

| # | 議題 | 裁決 | 理由 |
|---|---|---|---|
| 1 | 題型與 flag 混在一起（`challenge_type` 5 值 + `flag_type` 3 值） | **拆成正交軸**：交付 `deploy_type`（attachment/container/none）＋連線 `deploy_info.connection_type`；flag `flag_load`（static/dynamic）× `flag_scope`（shared/per_team）× `flag_match`（exact/regex） | 交付方式、連線方式、flag 載入、flag 分發、flag 比對是**多件獨立的事**；舊 `dynamic_container` 同時編碼「容器」與「每隊 flag」，舊 `flag_type` 把載入/分發/比對三合一，都無法單獨表達 |
| 2 | flag 可靜態或動態載入、且可唯一或統一 | **載入與分發拆兩軸**：`flag_load`(static/dynamic) 獨立於 `flag_scope`(shared/per_team) | 「動態載入但統一」= `dynamic`+`shared`，舊的單一 mode 表達不出；兩軸正交才涵蓋四種組合 |
| 3 | learning/skills/tools/references | **全刪**，改寫 `writeup/` | 除 plugin 表單外無人讀，屬純參考 |
| 4 | `solution_steps` | **移除**，解題 = `solution/exploit.py` + `writeup/README.md` | 解題該是可跑的碼 + 文件，不是 YAML 清單；`writeup/` 本來就是必要目錄 |
| 5 | `flag_description` | **移除** | writeup 已涵蓋 |
| 6 | `owners` vs `author` | **只留 `author`** | 直觀；單一人員欄位 |
| 7 | `assignee` | **移除** | 指派是 PM/plugin DB 狀態，不屬 commit 的 public.yml |
| 8 | `category` 固定 enum vs 自由填 | **自由填寫**（建議值 + 小寫正規化 + 未知值只警告） | 真實題庫出現 enum 外的 `OSINT`；固定 enum 會硬失敗。自由填 + 正規化兼顧「不缺值」與「分組不散」 |
| 9 | `difficulty` 真實值 `Medium` ≠ enum `middle` | 保持控制詞彙（供排序/配額），但**正規化別名**：`medium→middle`、大小寫不敏感 | 難度要排序，不能純自由填；但需容錯真實寫法 |

---

## 必填清單（給 validate-challenge.py）

`title`、`author`、`difficulty`、`category`、`description`、`deploy_type`、`source_code_provided`（public）＋ `flag`（private）。
flag 三軸（`flag_load`/`flag_scope`/`flag_match`）皆選填有預設；validator 需擋 `static + per_team` 的非法組合。

---

## 遷移清單 + 衝擊面（實作時各檔要改什麼）

> **實作進度**：✅ Stage 1（template + validator）、✅ Stage 2（helper `scripts/challenge_schema.py` + 5 範例 + create-challenge + pipeline 消費端 + CI pr-policy）已完成，115 測試綠。
> ⏳ Stage 3（plugin）未做。消費端一律透過 `challenge_schema.py` 新舊相容，遷移期間新舊題目都讀得動。
>
> ⚠️ 精簡方向會動到 **pipeline 與 CI**，不是只改文件。以下標「衝擊：大/中/小」。

| 對象 | 動作 | 衝擊 |
|---|---|---|
| `deploy_type` 取代 `challenge_type` | 改 7 個消費端：`verify-solution` / `sync-to-ctfd` / `validate-challenge` / `generate-dashboard` / `validate-all-challenges` / `update-readme` / plugin | **大** |
| `flag_load`+`flag_scope`+`flag_match` 取代 `flag_type` | 改 5 個消費端：`verify-solution` / `sync-to-ctfd`（flag_match→CTFd type）/ `generate-viewer-data` / `scan-secrets` / plugin；plugin flag UI 改三個下拉 | **大** |
| `flag` 支援 str 或 list、`deploy_type: none` | plugin `_sync_flag` 改迴圈支援多 flag；converter/validator 接受兩型；validate 允許 `none` | 中 |
| 廢 `owners`/`assignee` | 改 `generate-viewer-data`（by_member 改用 author）、CI `pr-policy-check`、`setup_helpers` | **中** |
| `challenge-template/*.yml.template` | 依 canonical 重寫（大幅刪欄） | 中 |
| `docs/challenge-metadata-standard.md` | 廢除，改導向本文件 | 小 |
| `challenges/examples/**`（5 題） | 補 `deploy_type` + flag 三軸；刪 solution_steps/flag_description/learning_*/自創欄位；解題移進 `writeup/` | 中 |
| `is1ab_authoring` plugin | 表單砍掉已廢欄位；flag UI 改 flag_mode+flag_match；匯出對齊 | 中 |
| `validate-challenge.py` | 必填改為新清單；加 `deploy_type` 合法值 + flag 三軸 + `static+per_team` 非法檢查；`category` 自由填（未知值只警告）；`difficulty` 正規化別名（medium→middle） | 小 |

---

## 潛伏 bug（實作階段一起修）

- **A｜5 範例缺 flag 分發標記。** 目前只有 `flag_format`（將廢），沒有 load/scope 標記，靠 `sync-to-ctfd` fallback 到 static 剛好都對。→ 補 flag 三軸（多數就是 `static`/`shared`/`exact`）。
- **B｜plugin 與 pipeline 的人員欄位脫節。** 廢 owners/assignee 後，viewer/CI 需一律改讀 `author`。
