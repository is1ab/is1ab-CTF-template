# 題目流程 pipeline —— 實作交接與待辦

給接手開發的人。完整設計與決策在 **is1abCTF(私有 repo)`challenge-pipeline-design.md`**;
這份只列「已做 / 待做 / 怎麼接手」。

## 骨架（一句話）
`template = staging`(出題/投稿/退修/試解/審核),`is1abCTF = prod`(接收已驗版本、部署/釋出)。
晉升 = 跨 repo 帶「同一產物 digest + 證據」,不重建、不整庫 merge。

## 已完成
| 項目 | 分支 | 內容 |
|---|---|---|
| **增量① 產物基礎** | `feat/build-digest` | 內容雜湊 tag（`challenge_schema.content_hash`/`image_tag`,排除 private.yml/solution/writeup）、`build-images` 加 `--platform=linux/amd64` + push 後取回 `@sha256` digest、`sync-to-ctfd` 用同一支 `image_tag`（build/sync tag 一致）。全套 174 測試過 |
| **題面送審/退修協作** | `codex/authoring-collaboration` | is1ab_authoring 的成員授權/提案工單/接案/裁判確認/建草稿/固定版本送審/退修/題面確認;版本鎖、未結問題跨版延續、作者不能自結、過期表單保留、指紋偵測後台直改。165+27 測試過。詳見該分支 `docs/authoring-collaboration.md` |

> 注意界線:**「題面確認」≠ 正式驗題通過**。下面增量②③④才是「可晉升 prod」的資格。

## 待做（依設計依賴順序;每個都可獨立 PR）
- **② `verify-solution.py --via ctfd`**:對 staging CTFd 開 instance→等可連→跑官解→**交 flag round-trip**;附件題下載 CTFd 附件跑解。exit 契約沿用 `0/1/2/4`。
  - 純邏輯（連線資訊解析、flag 抽取、exit code）先單測;round-trip 用 `ctfd/ctfd:3.7.5` 一次性容器測（同現有整合測試法）。
- **③ verified 產物紀錄**:verify 通過→在 registry 打 `verified-<hash>` 或簽發驗證紀錄;晉升時要求存在(§7.2)。
- **④ `reviewed-and-solved` 閘門**:approve 者在 reviewer 名單 **且** staging 上該 uid 真有 solve(§6.2/§7.2)。
- **⑤ 產物 manifest**:uid/revision/主+sidecar digests/有效設定指紋/工具版本(§7.1)。
- **⑥ 跨 repo promotion**:template 合併→在 is1abCTF 開晉升 PR（只帶題目+`promotions/` 證據,同 digest,不重建）;prod plan-diff + 三條不變量（賽中拒部署 / 已解題不得改 flag / 先 plan）。
- **⑦ intake bot（非 git 入口）**:plugin「送出審核」→ self-hosted workflow 匯出 export→開 PR。plugin 不自持 git（規格 §13.2 Ⓐ）。

## 環境/基礎設施待辦（賽後,詳見 is1abCTF `network-dns-architecture.md`）
- OPNsense 的選手 WG（wgctf）從手工腳本遷 **原生 WireGuard**（免 start 腳本+路由看門狗）。
- **重建 wgmgmt 管理 VPN**（server 私鑰+peer 已遺失、無備份,需新金鑰+管理員換發 conf）。
- 刪 `wg0`（誤設 10.8.0.6 撞 PVE）。
- OPNsense wgctf 防火牆 `.60` 收斂到 NodePort 埠 `30000-32767`（現放行所有埠含 :22/:6443）。
- （選）題目 NodePort → MetalLB per-instance IP + per-pod NetworkPolicy（每人只碰自己環境）。

## 怎麼接手
- 測試:`uv run --extra dev pytest tests -q`（純函式）;整合測試見各分支 `docs/`。
- 共用規則單一真相:`scripts/challenge_schema.py`（image tag/registry/schema）——build 與 sync 都讀它,改這裡兩邊自動一致。
- 開新增量請**開新分支**,別疊在 `feat/build-digest` / `codex/authoring-collaboration` 上。

## 待團隊裁決
- ② round-trip 測哪個 CTFd:`ctfd/ctfd:3.7.5` 容器(推薦、CI 可重現) vs 真 dev/staging。
- uid 存 CTFd:tag `uid:<…>`(零 schema 變更) vs k3s plugin 加欄位。
- 何時把 template `scripts/` 套件化成 `is1ab_ctf` + `ctf` 指令(is1abCTF 改依賴)。
