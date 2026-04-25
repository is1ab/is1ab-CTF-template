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
