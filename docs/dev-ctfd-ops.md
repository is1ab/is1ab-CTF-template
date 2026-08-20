# dev CTFd 營運手冊（is1ab_authoring 出題站）

團隊共用的 **dev CTFd** 是出題開發中樞（`is1ab_authoring` 外掛），跑在 **VM100**（校內 `10.10.10.146`），
用 `ctfd-plugin/docker-compose.dev-vm.yml` 起。**它不是比賽用 CTFd**，只給團隊內部出題／驗題。

> 比賽用 CTFd 是另一組（`ctf.is1ab.com`，走 Cloudflare Tunnel）。兩者無關，別混。

## ⚠️ 最重要的一條：dev CTFd 不是題目的 source of truth

題目的**正本永遠在 repo**（`challenges/<cat>/<slug>/{public,private}.yml`）。dev CTFd 只是一個
「編輯器 + 一鍵部署測試台」。**在 dev UI 建好／改好題目，要立刻用「匯出 YAML」把 `public.yml`/
`private.yml` 存回你的 clone 並 commit。** 否則那份工作只活在 VM100 的 DB volume 裡，volume 一掛就沒了。

- dev DB 存的是：草稿、metadata（owner/進度/uid）、配額、類型/難度設定（`is1ab_categories` 等 config）。
- 這些用 `backup-dev-vm.sh` 定期備份保命，但**不取代**「匯出 → commit」。

## 首次架設 / 換機

```bash
cd /opt/is1ab-ctf-template/ctfd-plugin
cp .env.dev-vm.example .env
# 編輯 .env：至少設 CTFD_DEV_SECRET_KEY（openssl rand -hex 32）
docker compose -p ctfd-dev -f docker-compose.dev-vm.yml up -d
```

- 綁 `0.0.0.0:8010` → 校內網直接連 `http://10.10.10.146:8010`。
- 遠端（管理 WG）存取：`ssh -L 18010:10.10.10.146:8010 root@10.8.0.6` → 開 `http://localhost:18010`。
  （用非 8010 的本機埠，避免被本機 OrbStack 之類佔用。）
- 首次進後台會被自動導到「is1ab 設定」設類型/配額（設或略過一次後不再提示）。
- **建 admin 帳號要人自己跑安裝精靈**（`/setup`）；本專案工具不代建帳號/設密碼。

## repo 更新後同步到 dev（重要，會漂移）

VM100 的 `/opt/is1ab-ctf-template` 是 `git archive` 解出來的副本（**沒有 `.git`，不能 `git pull`**）。
repo 一更新，dev CTFd 掛進去的 `/repo`（`ctfd_convert` / `challenge_schema` / 外掛本體）**不會自動跟上**。
用同步腳本重鋪（overlay，不動 VM100 上未追蹤的 `.env`）：

```bash
# 在本機 repo checkout 內
BRANCH=feat/dev-ctfd-authoring ./ctfd-plugin/sync-dev-vm.sh
```

> 建議 repo 有動到 `scripts/`、`ctfd-plugin/` 時就跑一次；或在 VM100 掛 cron 定期同步某分支。

## 備份

```bash
# 在 VM100 上
bash /opt/is1ab-ctf-template/ctfd-plugin/backup-dev-vm.sh
# → /root/dev-ctfd-backups/ctfd-dev-db-*.sql.gz + uploads（保留最近 14 份）
```

建議在 VM100 掛 cron，例如每日：
```cron
0 4 * * * bash /opt/is1ab-ctf-template/ctfd-plugin/backup-dev-vm.sh >> /var/log/dev-ctfd-backup.log 2>&1
```

## 安全備註（內網 ≠ 安全）

- dev CTFd 綁 `0.0.0.0:8010` 且掛 `docker.sock`（`user: root`）供「一鍵部署」→ **容器 ≈ VM100 root**。
  校內網任何人都連得到 → **dev admin 密碼務必夠強**；不常用一鍵部署時可考慮拿掉 socket 掛載。
- `.env` 的 `CTFD_DEV_SECRET_KEY` 不進 repo（能偽造 session）。
