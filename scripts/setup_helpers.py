"""Pure functions for /setup wizard and CLI cleanup.

Shared between web-interface/app.py and scripts/cleanup-validation-fields.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


PR_TEMPLATE = """## 題目資訊
- **Category**:
- **Difficulty**:
- **Title**:

## 出題人 Checklist（提 PR 前自我檢查）
- [ ] `private.yml` 已填妥 flag
- [ ] `public.yml` 描述清晰、無 spoiler
- [ ] 本機 `make validate` 通過
- [ ] 本機 `make scan` 無 CRITICAL/HIGH
- [ ] Docker（如有）`docker compose up` 可起、可解
- [ ] Writeup 已撰寫

## 驗題人 Checklist（review 時填寫）
- [ ] 已 `git checkout` 此 branch
- [ ] 已成功 build / 起服務
- [ ] 已實際解出 flag，且與 `private.yml` 一致
- [ ] 難度標示與實際解題感受一致
- [ ] 提示（hints）合理、不直接洩答
- [ ] 無公開資料中夾帶 flag

## 備註
<!-- 驗題遇到的問題、來回討論 -->
"""


def generate_pr_template(config: Dict[str, Any]) -> str:
    """產生 .github/PULL_REQUEST_TEMPLATE.md 的內容。

    `config` 目前未使用，保留以利未來依專案個性化（例如 flag_prefix）。
    """
    return PR_TEMPLATE


CODEOWNERS_TEMPLATE = """# CODEOWNERS — 留空 placeholder
#
# 本專案不指派固定 reviewer，任一團隊成員 approve PR 即可（驗題流程）。
# 若需要特定路徑由特定人審，自行加規則，例如：
#
# /challenges/web/   @alice
# /challenges/pwn/   @bob
"""


def generate_codeowners(config: Dict[str, Any]) -> str:
    """產生 .github/CODEOWNERS 留空 placeholder。

    `config` 目前未使用，保留以利未來依 team.members 自動產生範例規則。
    """
    return CODEOWNERS_TEMPLATE


BRANCH_PROTECTION_DOC_TEMPLATE = """# Branch Protection 設定指引

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
ORG="{organization}"
REPO="{repo_name}"

gh api -X PUT "repos/$ORG/$REPO/branches/main/protection" \\
  -F required_status_checks.strict=true \\
  -F required_status_checks.contexts[]=validate-challenge \\
  -F required_status_checks.contexts[]=security-scan \\
  -F required_status_checks.contexts[]=docker-build \\
  -F enforce_admins=false \\
  -F required_pull_request_reviews.required_approving_review_count=1 \\
  -F restrictions=
```

## 驗證

```bash
gh api "repos/$ORG/$REPO/branches/main/protection" | jq '.required_pull_request_reviews'
```

應該看到 `required_approving_review_count: 1`。
"""


def generate_branch_protection_doc(config: Dict[str, Any]) -> str:
    """產生 .github/branch-protection.md 指引文件。"""
    project = (config.get("project") or {}) if isinstance(config, dict) else {}
    organization = (project.get("organization") or "your-org").strip() or "your-org"
    repo_name = (project.get("name") or "your-repo").strip() or "your-repo"
    return BRANCH_PROTECTION_DOC_TEMPLATE.format(
        organization=organization,
        repo_name=repo_name,
    )
