#!/usr/bin/env bash
# 把本 repo 指定分支的內容同步到 VM100 的 dev CTFd /repo（overlay 解壓）。
#
# 為什麼需要：VM100 的 /opt/is1ab-ctf-template 是 git archive 解出來的副本（沒有 .git，
# 不能 git pull）。repo 更新後，dev CTFd 掛進去的 /repo（ctfd_convert / challenge_schema /
# is1ab_authoring 等）不會自動跟上——必須手動重鋪，否則會漂移（見 docs/dev-ctfd-ops.md）。
#
# 做法：overlay 解壓（覆蓋 repo 追蹤的檔，不動未追蹤檔——例如 VM100 上的 .env 會被保留）。
#
# 用法（在本 repo 任一 checkout 內執行）：
#   ./ctfd-plugin/sync-dev-vm.sh                # 用預設分支/主機
#   BRANCH=main ./ctfd-plugin/sync-dev-vm.sh    # 指定分支
#
# 可用環境變數覆蓋（預設為目前拓樸）：
#   BRANCH   要同步的 git 分支（預設 feat/dev-ctfd-authoring）
#   JUMP     PVE 跳板 ssh 目標（預設 root@10.8.0.6，管理 WG 可達）
#   VM       VM100 ssh 目標（預設 root@10.10.10.146，vmbr1 內網）
#   REPO_DIR VM100 上的 repo 路徑（預設 /opt/is1ab-ctf-template）
#   PROJECT  compose project 名（預設 ctfd-dev）
set -euo pipefail

BRANCH="${BRANCH:-feat/dev-ctfd-authoring}"
JUMP="${JUMP:-root@10.8.0.6}"
VM="${VM:-root@10.10.10.146}"
REPO_DIR="${REPO_DIR:-/opt/is1ab-ctf-template}"
PROJECT="${PROJECT:-ctfd-dev}"

cd "$(git rev-parse --show-toplevel)"
git rev-parse --verify "$BRANCH" >/dev/null 2>&1 || { echo "✗ 找不到分支：$BRANCH"; exit 1; }

echo "→ 同步 [$BRANCH] 到 $VM:$REPO_DIR（經跳板 $JUMP，project=$PROJECT）"
git archive --format=tar "$BRANCH" | gzip | base64 | \
  ssh -o ConnectTimeout=15 "$JUMP" "ssh -o ConnectTimeout=12 $VM 'set -e; \
    base64 -d | gzip -d | tar -xf - -C \"$REPO_DIR\"; \
    cd \"$REPO_DIR/ctfd-plugin\"; \
    test -f .env || echo \"WARN: $REPO_DIR/ctfd-plugin/.env 不存在，compose 缺 CTFD_DEV_SECRET_KEY 會失敗（見 .env.dev-vm.example）\"; \
    docker compose -p \"$PROJECT\" -f docker-compose.dev-vm.yml up -d'"

echo "✓ 同步完成。驗證："
echo "   ssh $JUMP ssh $VM 'cd $REPO_DIR/ctfd-plugin && docker compose -p $PROJECT -f docker-compose.dev-vm.yml logs --since 30s ctfd | grep -i \"plugin loaded\"'"
