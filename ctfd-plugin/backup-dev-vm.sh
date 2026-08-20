#!/usr/bin/env bash
# 備份 dev CTFd（VM100 的 ctfd-dev stack）：DB dump + uploads volume。
#
# ⚠️ 提醒：dev CTFd 的 DB 不是題目的 source of truth——題目正本在 repo（見 docs/dev-ctfd-ops.md）。
#    這份備份是保命用（避免 volume 掛掉丟掉 metadata/config/未匯出草稿），不是取代「匯出→commit」。
#
# 在 VM100 上執行（此檔會隨 repo 同步到 /opt/is1ab-ctf-template/ctfd-plugin/）：
#   bash /opt/is1ab-ctf-template/ctfd-plugin/backup-dev-vm.sh
#
# 可用環境變數：
#   PROJECT  compose project 名（預設 ctfd-dev）
#   OUT      備份輸出目錄（預設 /root/dev-ctfd-backups）
#   KEEP     保留最近幾份（預設 14，較舊的刪除）
set -euo pipefail

PROJECT="${PROJECT:-ctfd-dev}"
OUT="${OUT:-/root/dev-ctfd-backups}"
KEEP="${KEEP:-14}"
HERE="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$HERE/docker-compose.dev-vm.yml"
TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

echo "→ DB dump …"
docker compose -p "$PROJECT" -f "$COMPOSE" exec -T db \
  sh -c 'exec mysqldump -uroot -p"${MARIADB_ROOT_PASSWORD:-ctfd}" --single-transaction --routines --databases ctfd' \
  | gzip > "$OUT/ctfd-dev-db-$TS.sql.gz"

echo "→ uploads volume …"
docker run --rm \
  -v "${PROJECT}_ctfd_dev_uploads:/u:ro" \
  -v "$OUT:/out" \
  alpine tar czf "/out/ctfd-dev-uploads-$TS.tar.gz" -C /u . 2>/dev/null \
  || echo "  （uploads volume 空或不存在，略過）"

# 輪替：只留最近 $KEEP 份
ls -1t "$OUT"/ctfd-dev-db-*.sql.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
ls -1t "$OUT"/ctfd-dev-uploads-*.tar.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f

echo "✓ 備份完成："
ls -lh "$OUT"/ctfd-dev-*-"$TS".* 2>/dev/null || true
echo "   還原 DB：zcat <檔> | docker compose -p $PROJECT -f docker-compose.dev-vm.yml exec -T db mysql -uroot -pctfd"
