# is1ab_authoring — dev CTFd 出題系統

把一台**共用的 dev CTFd** 變成出題開發中樞:PM 規劃配額並指派、出題者在前台建題 →
匯出 `public.yml`/`private.yml` → 本機部署測試 + 驗 exploit → commit/PR 回 repo。

此插件用於 **template / staging**；is1abCTF 是 production。一般註冊帳號不會自動取得出題權限，PM、裁判、驗題人也不因角色取得 flag 或官解。管理員保有 CTFd 後台最高權限。

目前操作與限制以 [出題協作操作與權限](../docs/authoring-collaboration.md) 為準；[原始設計](../docs/dev-ctfd-authoring-spec.md) 保留作為歷史背景。

---

## 快速起步（admin,一次性）

```bash
cd ctfd-plugin
# 先在私有環境設定 IS1AB_REVIEW_FINGERPRINT_KEY；產生方式見下方環境變數說明
docker compose -f docker-compose.dev.yml up -d
# 開 http://localhost:8010 → 跑一次 CTFd 安裝精靈（建 admin 帳號、賽名）
```

安裝精靈完成後,建議把全站設成**登入才可見**(避免匿名亂看):CTFd 後台
`/admin/config` → Visibility,把 Challenge / Account / Score / Registration 都設 **private**。

**建立工作帳號**：CTFd 後台 `/admin/users` 建立一般帳號，再到 `/is1ab/members` 啟用並授予工作角色；同人可以兼任。GitHub 身分映射尚未接通，不必為 staging 接案改用 GitHub username。

確認外掛載入:

```bash
docker compose -f docker-compose.dev.yml logs ctfd | grep is1ab_authoring
```

---

## 角色與頁面

**出題者**(非 admin)→ 前台 `/is1ab/*`:

| 頁面 | 路徑 | 做什麼 |
|---|---|---|
| 我的待辦 | `/is1ab/work` | 提案、本人接案、指派及題面審閱進度；登入後從這裡開始 |
| 工單 | `/is1ab/work/<id>` | PM 安排作者／驗題人、截止與工時；裁判確認提案 |
| 成員與角色 | `/is1ab/members` | 僅管理員可授予／撤銷角色 |
| 出題清單 | `/is1ab` | 我看得到的題;新增題目 / 匯入 YAML |
| 新增 / 編輯 | `/is1ab/new`、`/is1ab/challenges/<id>/edit` | 一頁填原生欄位（名稱/分類/分數/flag/tags/hints）+ 富欄位 + 開發進度 + 協作者 |
| 匯出 | 題目頁的「匯出」 | 產 `public.yml`/`private.yml` 供複製/下載,附本機驗題指令 |
| 我的題目 | `/is1ab/mine` | 我出/協作的題 + 指派給我出題/驗題 |
| 送審與版本 | `/is1ab/challenges/<id>/reviews` | 主作者固定題面送審；依指派權限查看歷史 |
| 此版審閱 | `/is1ab/reviews/<id>` | 驗題人提出／結案問題，作者回覆；退修再送審 |
| 團隊 | `/is1ab/team` | PM／裁判查看成員的題目與工單概況 |
| 儀表板 | `/is1ab/dashboard` | PM／裁判查看配額、工單與在途 PR |

**PM 是獨立工作角色**，可規劃與追蹤，不能授權成員或編輯他人的私有題目。CTFd 後台與帳號管理仍屬平台管理員。

---

## 出題者流程

1. **接案與提案確認**：「我的待辦」→ 本人確認接案 → 補提案 → 送裁判確認。指定驗題人也須本人接案。
2. **建題與題面審閱**：裁判確認後，從工單建立隱藏草稿；主作者送出題面審閱。驗題人回報問題，作者修正再送，驗題人確認結案。官解與測試帳密寫入私有 `writeup/README.md`，不要放在題敘／討論。
3. **匯出**:題目頁「匯出」→ 複製 `public.yml`/`private.yml` 到自己 clone 的 `challenges/<分類>/<slug>/`。
4. **寫 code**:在 repo/IDE 完成 `src/` `docker/` `solution/exploit.py`(契約見 [scripts/verify-solution.py](../scripts/verify-solution.py))。
5. **本機驗題**（匯出頁會帶好指令）:

   ```bash
   make verify-solution ARGS="challenges/<分類>/<slug>"
   ```

   會起服務 → 跑官方解 → 比對 flag（含 flag drift 偵測）。此結果是本機檢查；尚未接入同版本獨立試解與正式發布核准。
6. **commit + PR**:在自己的 clone 把 code + YAML 一起 commit、push、開 PR → review → merge 回 repo。

> plugin **不**代你 push / 開 PR（架構決策 Ⓐ）——git 由你在自己的 clone 做,單一工作副本、不打架。

## PM 流程

1. **配額**:各分類 × 難度設目標題數。
2. **指派**：工單安排出題者、獨立驗題人、截止日期與預估工時；等待本人接案。從工單建立題目會自動連結，舊題可由 PM 指定 ID 連結。
3. **追蹤**：「我的待辦」顯示提案與題面審閱下一步。變更人員／時程需重新接案與確認；PM 不代替驗題人結案。

---

## 反向匯入（repo YAML → CTFd）

既有題目(例如去年的、或用 `make new-challenge` 建的)可載進 dev CTFd 編輯：
`/is1ab` →「匯入 YAML」→ 貼上 `public.yml` + `private.yml`。會建出 CTFd 題目 +
flag/tags/hints + 富欄位,`public.yml` 的 `id`(durable uid)與 `status` 會正確還原。
匯出 → 匯入 → 再匯出是**無損** round-trip。

---

## 環境變數

| 變數 | 用途 |
|---|---|
| `IS1AB_REVIEW_FINGERPRINT_KEY` | 送審必填；獨立隨機值至少 32 字元，可用 `openssl rand -hex 32` 產生。保存在私有環境設定、跨副本與重啟一致，不提交 Git、不重用 session／簽署金鑰；輪換後須重新送審 |
| `GITHUB_REPO`（`owner/repo`）+ `GITHUB_TOKEN` | 選配：儀表板「在途 PR」看板；協作工單尚未接通 Git 身分映射與 review request |

兩份開發 Compose 已轉入審閱金鑰；VM 範例見 `.env.dev-vm.example`。未設定金鑰時可編輯草稿，送審會提示維運完成設定。插件直接操作 Docker 的舊入口已停用，Compose 不再掛載主機 Docker socket；正式執行器與 production 發布尚未接通。

## 版本

CTFd 本機建置版本 pin 在 `docker-compose.dev.yml` 的 `build.args.CTFD_VERSION: "3.7.5"`；VM 設定須同步核對。
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
