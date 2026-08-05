# is1ab_authoring — dev CTFd 出題系統

把一台**共用的 dev CTFd** 變成出題開發中樞:PM 規劃配額並指派、出題者在前台建題 →
匯出 `public.yml`/`private.yml` → 本機部署測試 + 驗 exploit → commit/PR 回 repo。

> ⚠️ 這是**開發用**的 CTFd,**不是正式比賽站**。dev 上放 flag / 官方解沒問題
> (看得到的就是能看 `private.yml` 的那群出題人,同一個信任邊界)。
> 完整規格與架構決策見 [../docs/dev-ctfd-authoring-spec.md](../docs/dev-ctfd-authoring-spec.md)。

---

## 快速起步（admin,一次性）

```bash
cd ctfd-plugin
docker compose -f docker-compose.dev.yml up -d
# 開 http://localhost:8010 → 跑一次 CTFd 安裝精靈（建 admin 帳號、賽名）
```

安裝精靈完成後,建議把全站設成**登入才可見**(避免匿名亂看):CTFd 後台
`/admin/config` → Visibility,把 Challenge / Account / Score / Registration 都設 **private**。

**建出題者帳號**:CTFd 後台 `/admin/users` → 由 admin 建(註冊已關)。出題者帳號的
`name` 建議直接用 **GitHub username**(這樣指派驗題時的 `gh` review request 才對得上)。

確認外掛載入:

```bash
docker compose -f docker-compose.dev.yml logs ctfd | grep is1ab_authoring
```

---

## 角色與頁面

**出題者**(非 admin)→ 前台 `/is1ab/*`:

| 頁面 | 路徑 | 做什麼 |
|---|---|---|
| 出題清單 | `/is1ab` | 我看得到的題;新增題目 / 匯入 YAML |
| 新增 / 編輯 | `/is1ab/new`、`/is1ab/challenges/<id>/edit` | 一頁填原生欄位（名稱/分類/分數/flag/tags/hints）+ 富欄位 + 開發進度 + 協作者 |
| 匯出 | 題目頁的「匯出」 | 產 `public.yml`/`private.yml` 供複製/下載,附本機驗題指令 |
| 我的題目 | `/is1ab/mine` | 我出/協作的題 + 指派給我出題/驗題 |
| 團隊 | `/is1ab/team` | 每位成員的負載 |
| 儀表板 | `/is1ab/dashboard` | 題目分布（配額幾題就幾個方格）+ 工單 + 在途 PR |

**PM**(= CTFd admin)→ 同上,外加儀表板頂端的管理列:**配額 / 指派 / CTFd 後台 / 帳號管理**
(只有 admin 看得到)。點 CTFd 齒輪會直接落在儀表板。

---

## 出題者流程

1. **接指派**（PM 指派後,在「我的題目」看到「指派給我出題」）。
2. **建題**:`/is1ab` → 新增題目,填原生欄位 + flag/tags/hints + 富欄位 blob(官方解/測試帳密/學習目標…)+ 開發進度。
3. **匯出**:題目頁「匯出」→ 複製 `public.yml`/`private.yml` 到自己 clone 的 `challenges/<分類>/<slug>/`。
4. **寫 code**:在 repo/IDE 完成 `src/` `docker/` `solution/exploit.py`(契約見 [scripts/verify-solution.py](../scripts/verify-solution.py))。
5. **本機驗題**（匯出頁會帶好指令）:

   ```bash
   make verify-solution ARGS="challenges/<分類>/<slug>"
   ```

   會起服務 → 跑官方解 → 比對 flag（含 flag drift 偵測）。綠燈才算過。
6. **commit + PR**:在自己的 clone 把 code + YAML 一起 commit、push、開 PR → review → merge 回 repo。

> plugin **不**代你 push / 開 PR（架構決策 Ⓐ）——git 由你在自己的 clone 做,單一工作副本、不打架。

## PM 流程

1. **配額**:各分類 × 難度設目標題數。
2. **指派**:建工單,指派出題者(+ 驗題者);題目建好後回填「對應題目」。
3. **追蹤**:儀表板的題目分布——每格依配額拆成 N 個方格,顯示「指派的出題者(未建)」/「題目連結(已建,可點進編輯)」/「缺」。

---

## 反向匯入（repo YAML → CTFd）

既有題目(例如去年的、或用 `make new-challenge` 建的)可載進 dev CTFd 編輯/試玩:
`/is1ab` →「匯入 YAML」→ 貼上 `public.yml` + `private.yml`。會建出 CTFd 題目 +
flag/tags/hints + 富欄位,`public.yml` 的 `id`(durable uid)與 `status` 會正確還原。
匯出 → 匯入 → 再匯出是**無損** round-trip。

---

## 環境變數（選配）

| 變數 | 用途 |
|---|---|
| `GITHUB_REPO`（`owner/repo`）+ `GITHUB_TOKEN` | 儀表板「在途 PR」看板;指派 reviewer 時 best-effort 發 `gh` review request（假設 CTFd `user.name` == GitHub username） |

在 `docker-compose.dev.yml` 的 `ctfd` service 的 `environment` 加即可;沒設就優雅略過。

## 版本

CTFd 版本 pin 在 `docker-compose.dev.yml` 的 `image: ctfd/ctfd:3.7.5`（單一處）。
外掛依 CTFd 內部 API,升版可能要小修。

## 收掉 / 重置

```bash
docker compose -f docker-compose.dev.yml down       # 保留資料
docker compose -f docker-compose.dev.yml down -v    # 連資料清掉（下次重跑安裝精靈）
```

---

## 目錄

```
ctfd-plugin/
├── docker-compose.dev.yml   # CTFd 3.7.5 + mariadb + redis + 掛外掛 + 啟動裝 PyYAML
└── is1ab_authoring/
    └── __init__.py          # 外掛本體（model / 出題表單 / 匯出匯入 / ACL / 配額指派 / 儀表板）
```

轉換器 [scripts/ctfd_convert.py](../scripts/ctfd_convert.py) 為 CTFd↔YAML 雙向純函式,plugin 與 CLI 共用。
