# Branch Protection 設定指引

> 此文件由 `/setup` 精靈產生。請手動執行下方步驟，將你的 Private Repo
> 的 main 分支保護規則設定起來。

## 為什麼需要 Branch Protection？

驗題流程依賴 GitHub PR approval 作為 single source of truth。
沒有 branch protection 的話，PR 可能被未經驗題就直接 merge。

## 必備規則

- **Require pull request reviews before merging**：1 個 approval
- **Require status checks to pass**：勾選下列 checks
  - `validate-challenge`
  - `security-scan`
  - `docker-build`
- **Require branches to be up to date before merging**
- **Disallow force pushes to main**
- **Disallow deletions of main**

## 用 GitHub 網頁設定（推薦給第一次的人）

1. 進入 repo → Settings → Branches → Add rule
2. Branch name pattern: `main`
3. 勾選上述規則 → Save changes

## 用 `gh` CLI 一鍵設定

```bash
ORG="is1ab"
REPO="is1ab-CTF-2026"

gh api -X PUT "repos/$ORG/$REPO/branches/main/protection" \
  -F required_status_checks.strict=true \
  -F required_status_checks.contexts[]=validate-challenge \
  -F required_status_checks.contexts[]=security-scan \
  -F required_status_checks.contexts[]=docker-build \
  -F enforce_admins=false \
  -F required_pull_request_reviews.required_approving_review_count=1 \
  -F restrictions=
```

## 驗證

```bash
gh api "repos/$ORG/$REPO/branches/main/protection" | jq '.required_pull_request_reviews'
```

應該看到 `required_approving_review_count: 1`。
