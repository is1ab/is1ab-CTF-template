# Setup Wizard + 驗題流程簡化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 砍掉冗餘驗題機制（`reviewer` / `validation_status` / `internal_validation_notes` / Web `/validation`），新增 5 步驟 idempotent 初始化精靈 `/setup/<step>`，並產生 `.github/` 模板。

**Architecture:** 三層分離 — (1) `scripts/setup_helpers.py` 純函數模組（產生模板、偵測/清理冗餘欄位）；(2) `scripts/cleanup-validation-fields.py` 薄 CLI；(3) `web-interface/app.py` 5 個 wizard route + 5 個模板 + sidebar 進度條。共用模組由 web 與 CLI 同時 import，確保單一事實來源。

**Tech Stack:** Python 3.8+、PyYAML（既有）、Flask + Jinja2（既有）、pytest（既有）、Bulma CSS（既有 UI 風格）。

**Spec:** [`docs/superpowers/specs/2026-04-25-setup-wizard-and-validation-cleanup-design.md`](../specs/2026-04-25-setup-wizard-and-validation-cleanup-design.md)

> **Plan amendment (2026-04-25, after Task 1)**: repo 的 pre-commit hook 阻擋任何 `private.yml` 檔進 git。Fixture 改用 `tests/fixtures/yaml_strings.py` 內嵌四個 Python 字串常數（`LEGACY_PRIVATE_YML` / `LEGACY_PUBLIC_YML` / `CLEAN_PRIVATE_YML` / `CLEAN_PUBLIC_YML`）。Tasks 5-8 的測試範例若引用 `(FIXTURES / "legacy_challenge" / "private.yml").read_text()` 一律改為直接使用對應字串常數，並用 `(tmp_path / "private.yml").write_text(LEGACY_PRIVATE_YML)` 寫入 tmp_path。

---

## File Structure

### 新建檔案
| Path | 責任 |
|------|------|
| `scripts/setup_helpers.py` | 純函數：產生 `.github/` 模板、偵測/清理冗餘欄位 |
| `scripts/cleanup-validation-fields.py` | CLI 包裝（dry-run / apply） |
| `web-interface/templates/setup/_layout.html` | Wizard sidebar + 進度條 |
| `web-interface/templates/setup/project.html` | Step 1 |
| `web-interface/templates/setup/team.html` | Step 2 |
| `web-interface/templates/setup/event.html` | Step 3 |
| `web-interface/templates/setup/quota.html` | Step 4 |
| `web-interface/templates/setup/finalize.html` | Step 5 |
| `tests/test_setup_helpers.py` | unit tests |
| `tests/test_cleanup_cli.py` | CLI smoke test |
| `tests/test_setup_wizard.py` | Flask integration tests |
| `tests/fixtures/legacy_challenge/private.yml` | 含三冗餘 key 的 fixture |
| `tests/fixtures/legacy_challenge/public.yml` | 含 validation_status 的 fixture |
| `tests/fixtures/clean_challenge/private.yml` | 無冗餘 key 的 fixture |
| `tests/fixtures/clean_challenge/public.yml` | 無冗餘 key 的 fixture |

### 修改檔案
| Path | 修改重點 |
|------|---------|
| `scripts/create-challenge.py` | 移除 `--reviewer`；author fallback 順序反轉；`private.yml` 模板移除三鍵 |
| `web-interface/app.py` | 新 wizard 路由；移除 `/validation` 與 reviewer 相關方法；`load_config` 加 backward compat |
| `web-interface/templates/base.html` | 移除「驗題」nav 連結 |
| `web-interface/templates/create_challenge.html` | 移除 reviewer 表單欄位 |
| `web-interface/templates/setup.html` | 改為 redirect helper（保留以免外部連結 404）|
| `config.yml` | `security.sensitive_yaml_fields` 加三欄位 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 改寫為雙 checklist（出題人 + 驗題人） |
| `.github/CODEOWNERS` | 改為留空 placeholder |
| `.github/branch-protection.md` | 新建（指引文件） |
| `docs/authoring-challenges.md` | 改寫驗題段 |
| `docs/challenge-metadata-standard.md` | revert 三欄位新增段落 |
| `docs/ctf-challenge-workflow.md` | 階段 2.3 名稱更新 |
| `web-interface/USAGE.md` | 移除驗題分頁說明、加 `/setup` 介紹 |
| `wiki/Web-GUI-Integration.md` | 同上 |
| `README.md` | 初始化檢查清單第一項 |

### 刪除檔案
| Path | 理由 |
|------|------|
| `web-interface/templates/validation.html` | `/validation` 路由移除 |

---

## Phase 1：純函數層 + CLI（Tasks 1–8）

### Task 1：建立 fixtures 與測試骨架

**Files:**
- Create: `tests/fixtures/legacy_challenge/private.yml`
- Create: `tests/fixtures/legacy_challenge/public.yml`
- Create: `tests/fixtures/clean_challenge/private.yml`
- Create: `tests/fixtures/clean_challenge/public.yml`
- Create: `tests/test_setup_helpers.py`

- [ ] **Step 1: 建立 legacy_challenge/private.yml**

```yaml
title: Legacy Web
author: alice
reviewer: bob
validation_status: pending
internal_validation_notes: |
  [2026-04-01] bob: pending — 尚未驗題
difficulty: easy
category: web
points: 100
flag: is1abCTF{legacy_test_flag}
hints:
  - level: 1
    cost: 0
    content: hint
```

- [ ] **Step 2: 建立 legacy_challenge/public.yml**

```yaml
title: Legacy Web
author: alice
reviewer: bob
validation_status: pending
difficulty: easy
category: web
points: 100
hints:
  - level: 1
    cost: 0
    content: hint
```

- [ ] **Step 3: 建立 clean_challenge/private.yml**

```yaml
title: Clean Web
author: alice
difficulty: easy
category: web
points: 100
flag: is1abCTF{clean_test_flag}
hints:
  - level: 1
    cost: 0
    content: hint
```

- [ ] **Step 4: 建立 clean_challenge/public.yml**

```yaml
title: Clean Web
author: alice
difficulty: easy
category: web
points: 100
hints:
  - level: 1
    cost: 0
    content: hint
```

- [ ] **Step 5: 建立 tests/test_setup_helpers.py 骨架**

```python
"""Unit tests for scripts/setup_helpers.py"""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
```

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/legacy_challenge tests/fixtures/clean_challenge tests/test_setup_helpers.py
git commit -m "test: 加入驗題清理 fixtures 與測試骨架"
```

---

### Task 2：`generate_pr_template(config)`

**Files:**
- Create: `scripts/setup_helpers.py`
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫失敗測試**

加入到 `tests/test_setup_helpers.py`：

```python
def test_generate_pr_template_contains_dual_checklists():
    from setup_helpers import generate_pr_template

    config = {"project": {"name": "is1ab-CTF"}}
    text = generate_pr_template(config)

    # 雙 checklist 結構
    assert "## 出題人 Checklist" in text
    assert "## 驗題人 Checklist" in text
    # 出題人關鍵項目
    assert "make validate" in text
    assert "make scan" in text
    # 驗題人關鍵項目
    assert "git checkout" in text
    assert "已實際解出 flag" in text
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd /Users/guantou/Desktop/is1ab-CTF-template
uv run pytest tests/test_setup_helpers.py::test_generate_pr_template_contains_dual_checklists -v
```

Expected: `ImportError: No module named 'setup_helpers'` 或 FAIL。

- [ ] **Step 3: 建立 `scripts/setup_helpers.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py::test_generate_pr_template_contains_dual_checklists -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_helpers.py tests/test_setup_helpers.py
git commit -m "feat(setup): 加入 generate_pr_template() 純函數"
```

---

### Task 3：`generate_codeowners(config)`

**Files:**
- Modify: `scripts/setup_helpers.py`
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_generate_codeowners_is_empty_placeholder():
    from setup_helpers import generate_codeowners

    text = generate_codeowners({"team": {"members": []}})

    # spec 8.2: 留空 placeholder，不指派固定 reviewer
    assert "本專案不指派固定 reviewer" in text
    # 不應該預設 @admin / @senior-dev
    assert "@admin" not in text
    assert "@senior-dev" not in text
    # 必須是合法 CODEOWNERS（註解開頭 #）
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped == "":
            continue
        assert stripped.startswith("#"), f"非註解行不該預設指派: {line!r}"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_helpers.py::test_generate_codeowners_is_empty_placeholder -v
```

Expected: FAIL（function 未定義）。

- [ ] **Step 3: 在 `scripts/setup_helpers.py` 加入函數**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py::test_generate_codeowners_is_empty_placeholder -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_helpers.py tests/test_setup_helpers.py
git commit -m "feat(setup): 加入 generate_codeowners() 留空 placeholder"
```

---

### Task 4：`generate_branch_protection_doc(config)`

**Files:**
- Modify: `scripts/setup_helpers.py`
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_generate_branch_protection_doc_has_gh_cli_steps():
    from setup_helpers import generate_branch_protection_doc

    config = {"project": {"organization": "is1ab", "name": "2026-CTF"}}
    text = generate_branch_protection_doc(config)

    # 必含 gh CLI 指令
    assert "gh api" in text or "gh repo edit" in text
    # 必含 main 分支保護要點
    assert "main" in text
    assert "approval" in text.lower() or "approving_review" in text
    # 必含 require status check
    assert "status check" in text.lower() or "required_status_checks" in text
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_helpers.py::test_generate_branch_protection_doc_has_gh_cli_steps -v
```

- [ ] **Step 3: 在 `scripts/setup_helpers.py` 加入函數**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py::test_generate_branch_protection_doc_has_gh_cli_steps -v
```

- [ ] **Step 5: 加入「config 帶入 organization」的測試**

```python
def test_generate_branch_protection_doc_substitutes_organization():
    from setup_helpers import generate_branch_protection_doc

    text = generate_branch_protection_doc({
        "project": {"organization": "is1ab", "name": "2026-CTF"},
    })
    assert "ORG=\"is1ab\"" in text
    assert "REPO=\"2026-CTF\"" in text


def test_generate_branch_protection_doc_handles_missing_org():
    from setup_helpers import generate_branch_protection_doc

    text = generate_branch_protection_doc({})
    assert "your-org" in text
    assert "your-repo" in text
```

- [ ] **Step 6: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py -v -k branch_protection
```

- [ ] **Step 7: Commit**

```bash
git add scripts/setup_helpers.py tests/test_setup_helpers.py
git commit -m "feat(setup): 加入 generate_branch_protection_doc()"
```

---

### Task 5：`detect_legacy_validation_fields()`

**Files:**
- Modify: `scripts/setup_helpers.py`
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_detect_legacy_finds_legacy_files(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    # 複製 legacy fixture 到臨時 challenges/ 目錄
    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    (challenges / "private.yml").write_text(
        (FIXTURES / "legacy_challenge" / "private.yml").read_text()
    )
    (challenges / "public.yml").write_text(
        (FIXTURES / "legacy_challenge" / "public.yml").read_text()
    )

    paths = detect_legacy_validation_fields(tmp_path / "challenges")

    # 兩個檔都該被偵測（private 含三 key、public 含 validation_status）
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert names == {"private.yml", "public.yml"}


def test_detect_legacy_skips_clean_files(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "clean"
    challenges.mkdir(parents=True)
    (challenges / "private.yml").write_text(
        (FIXTURES / "clean_challenge" / "private.yml").read_text()
    )
    (challenges / "public.yml").write_text(
        (FIXTURES / "clean_challenge" / "public.yml").read_text()
    )

    paths = detect_legacy_validation_fields(tmp_path / "challenges")
    assert paths == []


def test_detect_legacy_handles_missing_root(tmp_path):
    from setup_helpers import detect_legacy_validation_fields

    paths = detect_legacy_validation_fields(tmp_path / "does_not_exist")
    assert paths == []
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_helpers.py -v -k detect_legacy
```

- [ ] **Step 3: 在 `scripts/setup_helpers.py` 加入函數**

```python
LEGACY_KEYS = ("reviewer", "validation_status", "internal_validation_notes")


def detect_legacy_validation_fields(challenges_root: Path) -> List[Path]:
    """掃 challenges_root 下的 private.yml / public.yml，回傳含有冗餘 key 的檔案路徑。

    冗餘 key：reviewer, validation_status, internal_validation_notes
    """
    challenges_root = Path(challenges_root)
    if not challenges_root.exists():
        return []

    found: List[Path] = []
    for yml_path in sorted(challenges_root.rglob("*.yml")):
        if yml_path.name not in {"private.yml", "public.yml"}:
            continue
        try:
            with yml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        if any(key in data for key in LEGACY_KEYS):
            found.append(yml_path)
    return found
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py -v -k detect_legacy
```

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_helpers.py tests/test_setup_helpers.py
git commit -m "feat(setup): 加入 detect_legacy_validation_fields()"
```

---

### Task 6：`cleanup_legacy_validation_fields(dry_run=True)` — 預覽模式

**Files:**
- Modify: `scripts/setup_helpers.py`
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_cleanup_dry_run_does_not_modify_files(tmp_path):
    from setup_helpers import cleanup_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    private_yml = challenges / "private.yml"
    public_yml = challenges / "public.yml"
    private_yml.write_text(
        (FIXTURES / "legacy_challenge" / "private.yml").read_text()
    )
    public_yml.write_text(
        (FIXTURES / "legacy_challenge" / "public.yml").read_text()
    )

    private_before = private_yml.read_text()
    public_before = public_yml.read_text()

    report = cleanup_legacy_validation_fields(tmp_path / "challenges", dry_run=True)

    # 檔案內容未動
    assert private_yml.read_text() == private_before
    assert public_yml.read_text() == public_before

    # 報告內容
    assert report.dry_run is True
    assert len(report.files_changed) == 2
    assert any("reviewer" in keys for keys in report.keys_removed.values())
    assert any("validation_status" in keys for keys in report.keys_removed.values())
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_helpers.py::test_cleanup_dry_run_does_not_modify_files -v
```

- [ ] **Step 3: 在 `scripts/setup_helpers.py` 加入 ChangeReport 與函數**

```python
@dataclass
class ChangeReport:
    """cleanup_legacy_validation_fields 的回傳結果。"""
    dry_run: bool
    files_changed: List[Path] = field(default_factory=list)
    keys_removed: Dict[Path, List[str]] = field(default_factory=dict)


def cleanup_legacy_validation_fields(
    challenges_root: Path,
    dry_run: bool = True,
) -> ChangeReport:
    """從 challenges_root 下的 private.yml / public.yml 移除冗餘 key。

    dry_run=True：只回報、不寫檔。
    dry_run=False：實際寫檔。
    """
    challenges_root = Path(challenges_root)
    report = ChangeReport(dry_run=dry_run)

    for yml_path in detect_legacy_validation_fields(challenges_root):
        try:
            with yml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue

        removed_keys: List[str] = []
        for key in LEGACY_KEYS:
            if key in data:
                removed_keys.append(key)
                data.pop(key, None)

        if not removed_keys:
            continue

        report.files_changed.append(yml_path)
        report.keys_removed[yml_path] = removed_keys

        if not dry_run:
            with yml_path.open("w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

    return report
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py::test_cleanup_dry_run_does_not_modify_files -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_helpers.py tests/test_setup_helpers.py
git commit -m "feat(setup): 加入 cleanup_legacy_validation_fields() dry-run 模式"
```

---

### Task 7：`cleanup_legacy_validation_fields(apply)` — 實際寫檔

**Files:**
- Test: `tests/test_setup_helpers.py`

- [ ] **Step 1: 寫測試（function 已能 apply，但驗證行為）**

```python
def test_cleanup_apply_removes_keys(tmp_path):
    from setup_helpers import cleanup_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    private_yml = challenges / "private.yml"
    public_yml = challenges / "public.yml"
    private_yml.write_text(
        (FIXTURES / "legacy_challenge" / "private.yml").read_text()
    )
    public_yml.write_text(
        (FIXTURES / "legacy_challenge" / "public.yml").read_text()
    )

    report = cleanup_legacy_validation_fields(tmp_path / "challenges", dry_run=False)

    assert report.dry_run is False
    assert len(report.files_changed) == 2

    private_after = yaml.safe_load(private_yml.read_text())
    public_after = yaml.safe_load(public_yml.read_text())

    # 三個 key 都應該被移除
    for key in ("reviewer", "validation_status", "internal_validation_notes"):
        assert key not in private_after
        assert key not in public_after

    # 其他 key 應保留
    assert private_after["title"] == "Legacy Web"
    assert private_after["author"] == "alice"
    assert private_after["flag"] == "is1abCTF{legacy_test_flag}"


def test_cleanup_apply_idempotent_on_clean_files(tmp_path):
    from setup_helpers import cleanup_legacy_validation_fields

    challenges = tmp_path / "challenges" / "web" / "clean"
    challenges.mkdir(parents=True)
    private_yml = challenges / "private.yml"
    public_yml = challenges / "public.yml"
    private_yml.write_text(
        (FIXTURES / "clean_challenge" / "private.yml").read_text()
    )
    public_yml.write_text(
        (FIXTURES / "clean_challenge" / "public.yml").read_text()
    )

    private_before = private_yml.read_text()
    public_before = public_yml.read_text()

    report = cleanup_legacy_validation_fields(tmp_path / "challenges", dry_run=False)

    # 沒有冗餘欄位 → 不應該變動
    assert report.files_changed == []
    assert private_yml.read_text() == private_before
    assert public_yml.read_text() == public_before
```

- [ ] **Step 2: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_helpers.py -v -k cleanup_apply
```

Expected: 兩個都 PASS（function 在 Task 6 已經實作）。

- [ ] **Step 3: Commit**

```bash
git add tests/test_setup_helpers.py
git commit -m "test(setup): 加入 cleanup_legacy_validation_fields apply 與 idempotent 測試"
```

---

### Task 8：`scripts/cleanup-validation-fields.py` CLI

**Files:**
- Create: `scripts/cleanup-validation-fields.py`
- Create: `tests/test_cleanup_cli.py`

- [ ] **Step 1: 寫失敗測試**

```python
"""Smoke test for scripts/cleanup-validation-fields.py CLI."""
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
CLI = REPO_ROOT / "scripts" / "cleanup-validation-fields.py"


def _setup_legacy_repo(tmp_path: Path) -> Path:
    challenges = tmp_path / "challenges" / "web" / "legacy"
    challenges.mkdir(parents=True)
    shutil.copy(FIXTURES / "legacy_challenge" / "private.yml", challenges / "private.yml")
    shutil.copy(FIXTURES / "legacy_challenge" / "public.yml", challenges / "public.yml")
    return tmp_path


def test_cli_dry_run_does_not_modify(tmp_path):
    repo = _setup_legacy_repo(tmp_path)
    private_before = (repo / "challenges/web/legacy/private.yml").read_text()

    result = subprocess.run(
        [sys.executable, str(CLI), "--dry-run", "--root", str(repo / "challenges")],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "DRY RUN" in result.stdout or "dry-run" in result.stdout.lower()
    assert (repo / "challenges/web/legacy/private.yml").read_text() == private_before


def test_cli_apply_removes_keys(tmp_path):
    repo = _setup_legacy_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(CLI), "--apply", "--root", str(repo / "challenges")],
        capture_output=True,
        text=True,
        check=True,
    )

    private_after = yaml.safe_load(
        (repo / "challenges/web/legacy/private.yml").read_text()
    )
    assert "reviewer" not in private_after
    assert "validation_status" not in private_after
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_cleanup_cli.py -v
```

Expected: FAIL（CLI 不存在）。

- [ ] **Step 3: 建立 `scripts/cleanup-validation-fields.py`**

```python
#!/usr/bin/env python3
"""CLI: 移除 challenges 中冗餘的 reviewer / validation_status / internal_validation_notes 欄位。

Usage:
    uv run python scripts/cleanup-validation-fields.py --dry-run
    uv run python scripts/cleanup-validation-fields.py --apply
    uv run python scripts/cleanup-validation-fields.py --apply --root path/to/challenges
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 讓 setup_helpers 可被 import
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from setup_helpers import cleanup_legacy_validation_fields  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="只預覽，不寫檔")
    mode.add_argument("--apply", action="store_true", help="實際寫檔")
    parser.add_argument(
        "--root",
        default=str(SCRIPT_DIR.parent / "challenges"),
        help="challenges 目錄路徑（預設 ./challenges）",
    )
    args = parser.parse_args()

    challenges_root = Path(args.root).resolve()
    if not challenges_root.exists():
        print(f"❌ challenges 目錄不存在: {challenges_root}")
        return 1

    report = cleanup_legacy_validation_fields(
        challenges_root,
        dry_run=args.dry_run,
    )

    label = "DRY RUN" if report.dry_run else "APPLIED"
    print(f"=== {label} ===")
    print(f"掃描根目錄: {challenges_root}")
    print(f"受影響檔案: {len(report.files_changed)}")
    for path in report.files_changed:
        keys = ", ".join(report.keys_removed.get(path, []))
        rel = path.relative_to(challenges_root)
        print(f"  {rel}  →  移除 {keys}")
    if report.dry_run and report.files_changed:
        print("\n💡 確認無誤後請改用 --apply 實際寫檔。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 確保腳本可執行**

```bash
chmod +x scripts/cleanup-validation-fields.py
```

- [ ] **Step 5: 跑測試確認通過**

```bash
uv run pytest tests/test_cleanup_cli.py -v
```

- [ ] **Step 6: 手動驗證一次（在 repo 自身上 dry-run）**

```bash
uv run python scripts/cleanup-validation-fields.py --dry-run
```

Expected: 顯示 `DRY RUN`，不修改任何檔案。

- [ ] **Step 7: Commit**

```bash
git add scripts/cleanup-validation-fields.py tests/test_cleanup_cli.py
git commit -m "feat(setup): 加入 cleanup-validation-fields.py CLI"
```

---

## Phase 2：CLI 與 metadata 清理（Tasks 9–12）

### Task 9：`create-challenge.py` 移除 `--reviewer` 並反轉 author fallback 順序

**Files:**
- Modify: `scripts/create-challenge.py:64-95`
- Modify: `scripts/create-challenge.py:191-250`（移除三鍵）— 由 Task 10 處理
- Modify: `scripts/create-challenge.py:810-825`（CLI argparse）

- [ ] **Step 1: 寫測試（建立題目時 author 從 git 抓）**

加入 `tests/test_create_challenge.py`（新檔）：

```python
"""Tests for scripts/create-challenge.py author fallback."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "create-challenge.py"


@pytest.fixture
def isolated_repo(tmp_path, monkeypatch):
    """建立有 config.yml 的隔離工作目錄。"""
    (tmp_path / "challenges").mkdir()
    (tmp_path / "config.yml").write_text(
        "project:\n"
        "  name: test\n"
        "  flag_prefix: testCTF\n"
        "team:\n"
        "  default_author: ConfigDefault\n"
        "points:\n"
        "  easy: 100\n"
    )
    # 模擬 git config user.name = "GitUser"
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "GitUser"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "git@example.com"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_author_prefers_git_user_over_config_default(isolated_repo):
    """author 順序：--author > git user.name > team.default_author"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "test_chall", "easy"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (isolated_repo / "challenges/web/test_chall/private.yml").read_text()
    # 應該是 GitUser，不是 ConfigDefault
    assert "author: GitUser" in private_yml
    assert "ConfigDefault" not in private_yml


def test_explicit_author_flag_wins(isolated_repo):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "explicit_chall", "easy",
         "--author", "ExplicitFlag"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (isolated_repo / "challenges/web/explicit_chall/private.yml").read_text()
    assert "author: ExplicitFlag" in private_yml


def test_falls_back_to_config_when_git_user_missing(tmp_path, monkeypatch):
    """git user.name 未設時 fallback 到 config 的 default_author"""
    (tmp_path / "challenges").mkdir()
    (tmp_path / "config.yml").write_text(
        "project:\n  name: t\n  flag_prefix: testCTF\n"
        "team:\n  default_author: FallbackUser\n"
        "points:\n  easy: 100\n"
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    # 注意：不設 user.name
    monkeypatch.chdir(tmp_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "fallback_chall", "easy"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = (tmp_path / "challenges/web/fallback_chall/private.yml").read_text()
    assert "author: FallbackUser" in private_yml


def test_reviewer_flag_no_longer_exists(isolated_repo):
    """--reviewer 應該已被移除"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert "--reviewer" not in result.stdout
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_create_challenge.py -v
```

Expected: 多個 FAIL（順序錯、`--reviewer` 仍存在）。

- [ ] **Step 3: 修改 `scripts/create-challenge.py:64-95`**

把 `create_challenge` method 中的 author / reviewer 邏輯整段替換：

```python
    def create_challenge(self, category, name, difficulty, author='', challenge_type=None):
        """創建新題目"""
        try:
            # author 解析順序：--author > git config user.name > team.default_author
            if not author:
                # 1. 試 git user.name
                try:
                    proc = subprocess.run(
                        ["git", "config", "--get", "user.name"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if proc.returncode == 0:
                        author = (proc.stdout or "").strip()
                except Exception:
                    author = ""
            if not author:
                # 2. 退回 config.yml 的 team.default_author
                if isinstance(self.config, dict):
                    author = self.config.get('team', {}).get('default_author', '') or ''
                    author = author.strip() if isinstance(author, str) else ''
            if not author:
                print("❌ 無法決定出題人。請以下列任一方式指定：")
                print("   • 命令列: --author \"YourName\"")
                print("   • git: git config user.name \"YourName\"")
                print("   • config.yml: team.default_author")
                return False

            # 輸入驗證
            if not self.validate_inputs(category, name, difficulty):
                return False

            print(f"🚀 Creating challenge: {category}/{name}")

            # 決定題目類型
            if not challenge_type:
                challenge_type = self.detect_challenge_type(category)

            # 建立目錄結構
            challenge_path = Path(f"challenges/{category}/{name}")
            if challenge_path.exists():
                print(f"❌ Error: Challenge {category}/{name} already exists")
                return False

            self.create_directory_structure(challenge_path, challenge_type)

            # 建立配置檔案
            private_config = self.create_private_config(
                name, category, difficulty, author, challenge_type
            )
            self.save_private_config(challenge_path, private_config)
```

- [ ] **Step 4: 修改 `scripts/create-challenge.py` 的 argparse 段（約第 810 行）**

找到並移除 `--reviewer` 參數定義；同步更新 `creator.create_challenge(...)` 呼叫端不再傳 `args.reviewer`：

```python
        parser.add_argument('--author', default='',
                           help='出題人（未填則使用 git user.name，再退回 config.yml team.default_author）')
        parser.add_argument('--type',
                           choices=['static_attachment', 'static_container',
                                    'dynamic_attachment', 'dynamic_container', 'nc_challenge'],
                           help='Challenge type (auto-detect if not specified)')
        parser.add_argument('--config', default='config.yml', help='Config file path')

        args = parser.parse_args()

        if not Path(args.config).exists():
            print(f"⚠️  Config file {args.config} not found, using default settings")

        creator = ChallengeCreator(args.config)
        success = creator.create_challenge(
            args.category, args.name, args.difficulty, args.author, args.type
        )
```

- [ ] **Step 5: 修改 `scripts/create-challenge.py:191`（method signature）**

```python
    def create_private_config(self, name, category, difficulty, author, challenge_type):
        """建立 private.yml 配置（包含敏感資訊如 flag）"""
```

（移除 `reviewer=''` 參數；本任務先改 signature，下一個 task 再清三個欄位。）

- [ ] **Step 6: 跑測試確認通過**

```bash
uv run pytest tests/test_create_challenge.py -v
```

- [ ] **Step 7: Commit**

```bash
git add scripts/create-challenge.py tests/test_create_challenge.py
git commit -m "refactor(create-challenge): 反轉 author fallback 順序、移除 --reviewer

git user.name 優先於 config.yml team.default_author，貼合
「個別出題人開 branch」場景。--reviewer 移除，驗題改由 PR review 處理。"
```

---

### Task 10：`create-challenge.py` 移除 `private.yml` 三鍵

**Files:**
- Modify: `scripts/create-challenge.py:191-243`
- Modify: `scripts/create-challenge.py:268-280`

- [ ] **Step 1: 寫測試（產生的 private.yml 不含三鍵）**

加到 `tests/test_create_challenge.py`：

```python
def test_generated_private_yml_has_no_validation_keys(isolated_repo):
    import yaml as _yaml

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "web", "no_validation", "easy"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    private_yml = isolated_repo / "challenges/web/no_validation/private.yml"
    data = _yaml.safe_load(private_yml.read_text())
    assert "reviewer" not in data
    assert "validation_status" not in data
    assert "internal_validation_notes" not in data
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_create_challenge.py::test_generated_private_yml_has_no_validation_keys -v
```

- [ ] **Step 3: 修改 `scripts/create-challenge.py:191-243`**

從 `create_private_config()` 的 dict 中移除三鍵：

```python
    def create_private_config(self, name, category, difficulty, author, challenge_type):
        """建立 private.yml 配置（包含敏感資訊如 flag）"""
        flag_prefix = self.config['project']['flag_prefix']
        config = {
            'title': name.replace('_', ' ').replace('-', ' ').title(),
            'author': author,
            'difficulty': difficulty,
            'category': category,
            'description': 'TODO: Add challenge description here',
            'challenge_type': challenge_type,
            'source_code_provided': False,
            'files': [],
            'status': 'planning',
            'points': self.config['points'].get(difficulty, 100),
            'tags': [category],
            'created_at': datetime.now().isoformat(),
            'flag': f'{flag_prefix}{{TODO_replace_with_actual_flag}}',
            'flag_description': 'TODO: 描述如何獲得這個 flag',
            'solution_steps': [
                'TODO: 第一步解題步驟',
                'TODO: 第二步解題步驟',
                'TODO: 第三步解題步驟'
            ],
            'internal_notes': 'TODO: 內部開發筆記，測試要點等',
            'deploy_info': {
                'port': None,
                'url': None,
                'requires_build': True
            },
            'hints': [
                {'level': 1, 'cost': 0, 'content': 'TODO: 第一個免費提示 - 引導參賽者思考方向'},
                {'level': 2, 'cost': 10, 'content': 'TODO: 第二個提示 - 提供具體的技術線索'},
                {'level': 3, 'cost': 25, 'content': 'TODO: 第三個提示 - 給出關鍵步驟或工具'},
            ],
        }

        if challenge_type == 'nc_challenge':
            config['deploy_info'].update({
                'nc_port': 9999,
                'timeout': 60,
                'connection_type': 'nc',
            })

        return config
```

- [ ] **Step 4: 修改 `generate_public_from_private()` (`scripts/create-challenge.py:268-280`)**

把 `internal_validation_notes` 從 sensitive_fields 拿掉（已不存在於 private dict），同時加入三個新名稱以防將來加回時忘記：

```python
    def generate_public_from_private(self, private_config):
        """從 private.yml 生成 public.yml (移除敏感資訊)"""
        public_config = private_config.copy()
        sensitive_fields = [
            'flag', 'flag_description', 'solution_steps', 'internal_notes',
        ]
        for field in sensitive_fields:
            public_config.pop(field, None)
        return public_config
```

- [ ] **Step 5: 跑測試確認通過**

```bash
uv run pytest tests/test_create_challenge.py -v
```

- [ ] **Step 6: 跑全部現有測試**

```bash
uv run pytest -v
```

Expected: 全部 PASS（沒有破壞既有 test）。

- [ ] **Step 7: Commit**

```bash
git add scripts/create-challenge.py tests/test_create_challenge.py
git commit -m "refactor(create-challenge): 從 private.yml 模板移除驗題三鍵"
```

---

### Task 11：`config.yml` 加入三欄位至 `sensitive_yaml_fields`（防呆）

**Files:**
- Modify: `config.yml:140-162`

- [ ] **Step 1: 讀現有 sensitive_yaml_fields**

```bash
grep -n "sensitive_yaml_fields" -A 25 config.yml
```

- [ ] **Step 2: 在 `config.yml` 的 `security.sensitive_yaml_fields` 清單加入三項**

修改：

```yaml
  sensitive_yaml_fields:
    - "flag"
    - "flags"
    - "real_flag"
    - "actual_flag"
    - "flag_description"
    - "flag_type"
    - "dynamic_flag"
    - "solution_steps"
    - "solution"
    - "solutions"
    - "internal_notes"
    - "internal_note"
    - "private_notes"
    - "test_credentials"
    - "credentials"
    - "admin_password"
    - "deploy_secrets"
    - "secrets"
    - "secret_key"
    - "verified_solutions"
    - "exploits"
    # 防呆：舊版驗題流程的三欄位（新流程已移除，但若舊題目殘留則不公開）
    - "reviewer"
    - "validation_status"
    - "internal_validation_notes"
```

- [ ] **Step 3: 驗證 yaml 仍可解析**

```bash
uv run python -c "import yaml; yaml.safe_load(open('config.yml'))" && echo OK
```

- [ ] **Step 4: 跑現有 scan-secrets 測試**

```bash
uv run pytest tests/test_scan_secrets.py -v
```

- [ ] **Step 5: Commit**

```bash
git add config.yml
git commit -m "chore(config): 加入舊驗題欄位至 sensitive_yaml_fields 作為公開過濾防呆"
```

---

### Task 12：revert `docs/challenge-metadata-standard.md` 中的三欄位段

**Files:**
- Modify: `docs/challenge-metadata-standard.md`

- [ ] **Step 1: 找到要 revert 的段落**

```bash
grep -n "reviewer\|validation_status\|internal_validation_notes" docs/challenge-metadata-standard.md
```

- [ ] **Step 2: 刪除三段（第 33-35 行的 reviewer / validation_status，第 107-110 行的 internal_validation_notes）**

精確修改：

第一段 — 把：
```
author: "AuthorName"                 # 必填：題目作者（出題人）
reviewer: "ReviewerName"            # 建議：驗題負責人（團隊內約定，與出題人可分離）
validation_status: "pending"         # 建議：pending | approved | rejected（納入驗題流程的題目）
points: 100                          # 必填：題目分數
```

改回：
```
author: "AuthorName"                 # 必填：題目作者
points: 100                          # 必填：題目分數
```

第二段 — 把：
```
flag: "is1abCTF{actual_flag_here}"  # 必填：實際的 flag
flag_type: "static"                 # 必填：static | dynamic | regex

# 驗題內部紀錄（不進 public）
internal_validation_notes: |       # 可選：驗題通過/退回的時間序備註（Web 驗題分頁會 append）
  [2026-01-01T00:00:00] reviewer: approve — 敘述
```

改回：
```
flag: "is1abCTF{actual_flag_here}"  # 必填：實際的 flag
flag_type: "static"                 # 必填：static | dynamic | regex
```

- [ ] **Step 3: 確認沒有殘留**

```bash
grep -E "reviewer|validation_status|internal_validation_notes" docs/challenge-metadata-standard.md
```

Expected: 無輸出。

- [ ] **Step 4: Commit**

```bash
git add docs/challenge-metadata-standard.md
git commit -m "docs: revert challenge-metadata-standard 中已廢除的驗題三欄位"
```

---

## Phase 3：Web `/setup` Wizard（Tasks 13–23）

### Task 13：`CTFManager` — `team.members` schema + backward compat

**Files:**
- Modify: `web-interface/app.py:70-151`（`load_config`）
- Test: `tests/test_setup_wizard.py`（新檔）

- [ ] **Step 1: 寫失敗測試**

建立 `tests/test_setup_wizard.py`：

```python
"""Integration tests for /setup wizard and team.members schema."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web-interface"
sys.path.insert(0, str(WEB_DIR))


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yml"
    monkeypatch.setattr("app.CONFIG_FILE", cfg)
    monkeypatch.setattr("app.BASE_DIR", tmp_path)
    monkeypatch.setattr("app.CHALLENGES_DIR", tmp_path / "challenges")
    (tmp_path / "challenges").mkdir()
    return cfg


def test_load_config_migrates_old_reviewers_authors(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "testCTF"},
        "team": {
            "default_author": "alice",
            "reviewers": ["bob", "carol"],
            "authors": ["alice", "dave"],
        },
        "points": {"easy": 100},
    }))

    from app import CTFManager  # 重 import 以重置狀態
    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()

    members = mgr.config.get("members") or []
    usernames = {m["github_username"] for m in members}
    # 預期：合併 reviewers + authors + default_author，去重
    assert usernames == {"alice", "bob", "carol", "dave"}
    # display_name 預設等於 github_username
    for m in members:
        assert m.get("display_name") == m["github_username"]
        assert m.get("specialty", "") == ""


def test_load_config_reads_native_members(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "testCTF"},
        "team": {
            "members": [
                {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
                {"github_username": "bob", "display_name": "Bob", "specialty": "pwn"},
            ],
        },
        "points": {"easy": 100},
    }))

    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()

    members = mgr.config.get("members") or []
    assert len(members) == 2
    assert members[0]["github_username"] == "alice"
    assert members[0]["specialty"] == "web"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v
```

Expected: FAIL（`members` key 尚不存在於 config）。

- [ ] **Step 3: 修改 `web-interface/app.py:70-151`（`load_config`）**

在 `team` block 之後加入 members 解析與遷移邏輯，並把 `members` 加到回傳 dict：

```python
            team = raw_config.get("team", {}) or {}
            reviewers = team.get("reviewers") or []
            if isinstance(reviewers, list):
                reviewers = [r for r in reviewers if r and str(r).strip()]
            else:
                reviewers = []

            authors = team.get("authors") or []
            if isinstance(authors, list):
                authors = [a for a in authors if a and str(a).strip()]
            else:
                authors = []

            # team.members（新 schema）
            raw_members = team.get("members") or []
            members: List[Dict[str, str]] = []
            seen_usernames: set[str] = set()
            if isinstance(raw_members, list):
                for entry in raw_members:
                    if not isinstance(entry, dict):
                        continue
                    username = str(entry.get("github_username") or "").strip()
                    if not username or username in seen_usernames:
                        continue
                    seen_usernames.add(username)
                    members.append({
                        "github_username": username,
                        "display_name": str(entry.get("display_name") or username).strip(),
                        "specialty": str(entry.get("specialty") or "").strip(),
                    })

            # Backward compat: 若 members 為空但舊欄位有值，自動遷移
            if not members:
                default_author = (team.get("default_author") or "").strip()
                migrate_pool = list(reviewers) + list(authors)
                if default_author:
                    migrate_pool.append(default_author)
                for username in migrate_pool:
                    username = str(username).strip()
                    if not username or username in seen_usernames:
                        continue
                    seen_usernames.add(username)
                    members.append({
                        "github_username": username,
                        "display_name": username,
                        "specialty": "",
                    })
```

並在最終 `config = {...}` 中加入：

```python
                "default_author": (team.get("default_author") or "").strip(),
                "reviewers": reviewers,
                "authors": authors,
                "members": members,
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k load_config
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/app.py tests/test_setup_wizard.py
git commit -m "feat(web): load_config 解析 team.members 並從舊欄位自動遷移"
```

---

### Task 14：`CTFManager.compute_step_status()` — 進度條判定

**Files:**
- Modify: `web-interface/app.py`（`CTFManager` 類別內，`is_setup_complete` 之後）
- Test: `tests/test_setup_wizard.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_compute_step_status_empty_config(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "", "flag_prefix": ""},
        "team": {},
        "event": {},
        "challenge_quota": {},
        "points": {"easy": 100},
    }))

    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()

    statuses = mgr.compute_step_status()
    assert statuses == {
        "project": "pending",
        "team": "pending",
        "event": "pending",
        "quota": "pending",
        "finalize": "pending",
    }


def test_compute_step_status_all_done(temp_config):
    # 預先建立 .github 檔案模擬 finalize 已跑過
    gh_dir = temp_config.parent / ".github"
    gh_dir.mkdir()
    (gh_dir / "PULL_REQUEST_TEMPLATE.md").write_text("dummy")
    (gh_dir / "CODEOWNERS").write_text("dummy")

    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "is1ab-CTF", "flag_prefix": "is1abCTF"},
        "team": {
            "members": [{"github_username": "alice", "display_name": "Alice"}],
        },
        "event": {"start_date": "2026-05-01", "end_date": "2026-05-30"},
        "challenge_quota": {
            "by_category": {"web": 6},
            "by_difficulty": {"easy": 10},
            "total_target": 16,
        },
        "points": {"easy": 100},
    }))

    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()

    statuses = mgr.compute_step_status()
    assert statuses["project"] == "done"
    assert statuses["team"] == "done"
    assert statuses["event"] == "done"
    assert statuses["quota"] == "done"
    assert statuses["finalize"] == "done"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k compute_step_status
```

- [ ] **Step 3: 在 `CTFManager` 類別中加入 method**

```python
    def compute_step_status(self) -> Dict[str, str]:
        """為 wizard 5 步驟計算進度條狀態。

        回傳 dict： step_name → "pending" | "done"
        判定依據詳見 spec 6.3。
        """
        statuses: Dict[str, str] = {}

        # Step 1: project
        project_name = (self.config.get("competition_name") or "").strip()
        # flag_prefix 從 raw config 讀（normalized config 沒帶）
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw_cfg = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw_cfg = {}
        flag_prefix = ((raw_cfg.get("project") or {}).get("flag_prefix") or "").strip()
        statuses["project"] = "done" if (project_name and flag_prefix) else "pending"

        # Step 2: team
        members = self.config.get("members") or []
        statuses["team"] = "done" if any(
            (m.get("github_username") or "").strip() for m in members
        ) else "pending"

        # Step 3: event
        event = self.config.get("event") or {}
        statuses["event"] = "done" if (
            event.get("start_date", "").strip() and event.get("end_date", "").strip()
        ) else "pending"

        # Step 4: quota
        quota = self.config.get("challenge_quota") or {}
        by_category = quota.get("by_category") or {}
        total_target = quota.get("total_target") or 0
        statuses["quota"] = "done" if (
            total_target and any(v > 0 for v in by_category.values())
        ) else "pending"

        # Step 5: finalize（.github 兩檔案存在 + 偵測到的冗餘欄位 = 0）
        gh_dir = BASE_DIR / ".github"
        pr_tmpl = gh_dir / "PULL_REQUEST_TEMPLATE.md"
        codeowners = gh_dir / "CODEOWNERS"
        if pr_tmpl.exists() and codeowners.exists():
            # 還要確認沒有 legacy 欄位
            try:
                from setup_helpers import detect_legacy_validation_fields
                legacy_count = len(
                    detect_legacy_validation_fields(CHALLENGES_DIR)
                )
            except Exception:
                legacy_count = 0
            statuses["finalize"] = "done" if legacy_count == 0 else "pending"
        else:
            statuses["finalize"] = "pending"

        return statuses
```

並在 `app.py` 頂部加入 sys.path 設定，讓 `setup_helpers` 可以 import：

```python
# 讓 scripts/setup_helpers.py 可被 import
import sys as _sys
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPTS_DIR))
```

放在現有的 `from typing import...` 之後、Flask import 之前。

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k compute_step_status
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/app.py tests/test_setup_wizard.py
git commit -m "feat(web): 加入 compute_step_status() 計算 wizard 進度條狀態"
```

---

### Task 15：`save_setup_step(step_name, data)` — 拆解 save_setup

**Files:**
- Modify: `web-interface/app.py:207-300`（`save_setup`）
- Test: `tests/test_setup_wizard.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_save_step_project_writes_only_project_fields(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "old"},
        "team": {"default_author": "preserved"},
    }))

    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()
    result = mgr.save_setup_step("project", {
        "project_name": "new-name",
        "organization": "is1ab",
        "flag_prefix": "is1abCTF",
        "year": "2026",
        "description": "desc",
    })

    assert result["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["project"]["name"] == "new-name"
    assert raw["project"]["flag_prefix"] == "is1abCTF"
    # team 區塊不被改動
    assert raw["team"]["default_author"] == "preserved"


def test_save_step_team_replaces_members_list(temp_config):
    temp_config.write_text(yaml.safe_dump({"team": {}}))

    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()
    result = mgr.save_setup_step("team", {
        "members": [
            {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
            {"github_username": "bob", "display_name": "Bob", "specialty": ""},
        ],
        "default_author": "",
    })

    assert result["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["team"]["members"] == [
        {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
        {"github_username": "bob", "display_name": "Bob", "specialty": ""},
    ]


def test_save_step_invalid_step_returns_error(temp_config):
    temp_config.write_text(yaml.safe_dump({}))
    import importlib, app as app_module
    importlib.reload(app_module)
    mgr = app_module.CTFManager()
    result = mgr.save_setup_step("not_a_step", {})
    assert result["status"] == "error"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k save_step
```

- [ ] **Step 3: 在 `CTFManager` 加入 `save_setup_step`**

放在現有 `save_setup` 之後（保留 `save_setup` 但讓它呼叫新方法以維持 backward compat）：

```python
    VALID_SETUP_STEPS = {"project", "team", "event", "quota"}

    def save_setup_step(self, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """寫入單一 wizard 步驟的欄位至 config.yml。"""
        if step not in self.VALID_SETUP_STEPS:
            return {
                "status": "error",
                "message": f"無效步驟: {step}（合法: {sorted(self.VALID_SETUP_STEPS)}）",
            }

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}

        raw.setdefault("project", {})
        raw.setdefault("team", {})
        raw.setdefault("event", {})
        raw.setdefault("challenge_quota", {})

        if step == "project":
            project = raw["project"]
            project["name"] = (data.get("project_name") or project.get("name") or "").strip()
            project["organization"] = (data.get("organization") or project.get("organization") or "").strip()
            project["description"] = (data.get("description") or project.get("description") or "").strip()
            project["flag_prefix"] = (data.get("flag_prefix") or project.get("flag_prefix") or "").strip()
            year = (data.get("year") or "").strip()
            if year:
                project["year"] = int(year) if year.isdigit() else year
            # platform / deployment 欄位可一起在這步寫
            raw.setdefault("platform", {})
            raw.setdefault("deployment", {})
            for k in ("gzctf_url", "ctfd_url", "zipline_url"):
                if k in data:
                    raw["platform"][k] = (data.get(k) or "").strip()
            for k in ("host", "docker_registry"):
                if k in data:
                    raw["deployment"][k] = (data.get(k) or "").strip()

        elif step == "team":
            team = raw["team"]
            team["default_author"] = (data.get("default_author") or "").strip()
            members_raw = data.get("members") or []
            cleaned: List[Dict[str, str]] = []
            seen: set = set()
            for entry in members_raw:
                if not isinstance(entry, dict):
                    continue
                username = str(entry.get("github_username") or "").strip()
                if not username or username in seen:
                    continue
                seen.add(username)
                cleaned.append({
                    "github_username": username,
                    "display_name": str(entry.get("display_name") or username).strip(),
                    "specialty": str(entry.get("specialty") or "").strip(),
                })
            team["members"] = cleaned

        elif step == "event":
            event = raw["event"]
            for k in ("start_date", "end_date", "authoring_deadline", "review_deadline", "freeze_deadline"):
                event[k] = (data.get(k) or "").strip()

        elif step == "quota":
            quota = raw["challenge_quota"]
            quota["by_category"] = {
                str(k).strip(): int(v)
                for k, v in (data.get("by_category") or {}).items()
                if str(k).strip() and str(v).isdigit()
            }
            quota["by_difficulty"] = {
                str(k).strip(): int(v)
                for k, v in (data.get("by_difficulty") or {}).items()
                if str(k).strip() and str(v).isdigit()
            }
            tt = (data.get("total_target") or "").strip()
            if tt and tt.isdigit():
                quota["total_target"] = int(tt)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self.config = self.load_config()
        return {"status": "success", "message": f"已儲存 {step} 設定"}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k save_step
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/app.py tests/test_setup_wizard.py
git commit -m "feat(web): 加入 save_setup_step() 處理單步驟寫入"
```

---

### Task 16：`/setup/<step>` 路由骨架

**Files:**
- Modify: `web-interface/app.py:1281-1289`（既有 `/setup` 路由）
- Test: `tests/test_setup_wizard.py`

- [ ] **Step 1: 寫失敗測試**

```python
@pytest.fixture
def client(temp_config):
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "tCTF"},
        "team": {"members": []},
        "event": {},
        "challenge_quota": {},
        "points": {"easy": 100},
    }))
    import importlib, app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_get_setup_root_redirects_to_project(client):
    resp = client.get("/setup")
    assert resp.status_code in (301, 302)
    assert "/setup/project" in resp.location


def test_get_setup_step_returns_200(client):
    for step in ("project", "team", "event", "quota", "finalize"):
        resp = client.get(f"/setup/{step}")
        assert resp.status_code == 200, f"{step} returned {resp.status_code}"


def test_get_setup_unknown_step_returns_404(client):
    resp = client.get("/setup/bogus")
    assert resp.status_code == 404
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k "setup_root or setup_step or setup_unknown"
```

- [ ] **Step 3: 改寫 `/setup` 路由**

把既有 `web-interface/app.py:1281-1289` 改為：

```python
SETUP_STEPS = ["project", "team", "event", "quota", "finalize"]


@app.route("/setup")
def setup_root():
    from flask import redirect, url_for
    return redirect(url_for("setup_step", step="project"))


@app.route("/setup/<step>", methods=["GET"])
def setup_step(step: str):
    from flask import abort
    if step not in SETUP_STEPS:
        abort(404)
    statuses = manager.compute_step_status()
    return render_template(
        f"setup/{step}.html",
        step=step,
        steps=SETUP_STEPS,
        statuses=statuses,
        config=manager.config,
    )


@app.route("/setup/<step>", methods=["POST"])
def setup_step_save(step: str):
    from flask import abort, jsonify
    if step not in SETUP_STEPS:
        abort(404)
    data = request.get_json(silent=True) or request.form.to_dict(flat=False)
    if step == "finalize":
        return jsonify(_handle_setup_finalize(data))
    # 把 form list 攤平
    if isinstance(data, dict):
        flat = {}
        for k, v in data.items():
            flat[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
        data = flat
    result = manager.save_setup_step(step, data or {})
    return jsonify(result)


def _handle_setup_finalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Step 5: 產生 .github/ 模板 + 清理冗餘欄位（依 data 中的 flag）。"""
    from setup_helpers import (
        cleanup_legacy_validation_fields,
        generate_branch_protection_doc,
        generate_codeowners,
        generate_pr_template,
    )

    config = manager.config
    raw_for_doc = {"project": {
        "organization": config.get("organization", ""),
        "name": config.get("competition_name", ""),
    }}
    actions: List[str] = []

    if data.get("generate_pr_template"):
        path = BASE_DIR / ".github" / "PULL_REQUEST_TEMPLATE.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_pr_template(config), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("generate_codeowners"):
        path = BASE_DIR / ".github" / "CODEOWNERS"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_codeowners(config), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("generate_branch_protection_doc"):
        path = BASE_DIR / ".github" / "branch-protection.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(generate_branch_protection_doc(raw_for_doc), encoding="utf-8")
        actions.append(f"產生 {path.relative_to(BASE_DIR)}")

    if data.get("cleanup_legacy"):
        report = cleanup_legacy_validation_fields(CHALLENGES_DIR, dry_run=False)
        actions.append(f"清理 {len(report.files_changed)} 個含冗餘欄位的檔案")

    return {"status": "success", "actions": actions}
```

並暫時建立每個 template 的最小骨架以避免 render 錯（下一個 task 會擴充）：

```bash
mkdir -p web-interface/templates/setup
for step in project team event quota finalize; do
  cat > web-interface/templates/setup/$step.html <<EOF
{% extends "base.html" %}
{% set title = "初始化 - $step" %}
{% block content %}
<section class="section">
  <h1 class="title">Step: $step</h1>
  <p>Placeholder, will be filled in next task.</p>
</section>
{% endblock %}
EOF
done
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k "setup_root or setup_step or setup_unknown"
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/app.py web-interface/templates/setup/ tests/test_setup_wizard.py
git commit -m "feat(web): 加入 /setup/<step> 5 步驟 wizard 路由骨架"
```

---

### Task 17：Sidebar 進度條 layout

**Files:**
- Create: `web-interface/templates/setup/_layout.html`
- Modify: `web-interface/templates/setup/project.html`（之後拿來示範）

- [ ] **Step 1: 建立 `_layout.html`**

```html
{% extends "base.html" %}
{% set title = title or "初始化精靈" %}

{% set step_labels = {
  "project": "專案資訊",
  "team": "團隊成員",
  "event": "比賽時程",
  "quota": "配額目標",
  "finalize": "產生與清理"
} %}

{% block content %}
<section class="section">
  <div class="container">
    <h1 class="title">
      <i class="fas fa-wand-magic-sparkles mr-2"></i>
      初始化精靈
    </h1>
    <p class="subtitle">完成 5 個步驟即可開始建立題目；任一欄位都可隨時回來調整。</p>

    <div class="columns">
      <aside class="column is-one-quarter">
        <aside class="menu">
          <p class="menu-label">步驟</p>
          <ul class="menu-list">
            {% for s in steps %}
            <li>
              <a href="{{ url_for('setup_step', step=s) }}"
                 class="{{ 'is-active' if s == step else '' }}">
                {% if statuses[s] == 'done' %}
                  <i class="fas fa-circle-check has-text-success mr-2"></i>
                {% else %}
                  <i class="far fa-circle has-text-grey mr-2"></i>
                {% endif %}
                {{ loop.index }}. {{ step_labels[s] }}
              </a>
            </li>
            {% endfor %}
          </ul>
        </aside>
      </aside>

      <main class="column">
        {% block step_body %}{% endblock %}
      </main>
    </div>
  </div>
</section>
{% endblock %}
```

- [ ] **Step 2: 把骨架改用 `_layout.html`**

修改 `web-interface/templates/setup/project.html`：

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 專案資訊" %}
{% block step_body %}
<div class="card">
  <header class="card-header">
    <p class="card-header-title">
      <i class="fas fa-rocket mr-2"></i> 專案基本資訊
    </p>
  </header>
  <div class="card-content">
    <p class="content has-text-grey">這一步會寫入 <code>config.yml</code> 的 <code>project</code> / <code>platform</code> / <code>deployment</code> 區塊。</p>
    <p>表單將在 Task 18 加入。</p>
  </div>
</div>
{% endblock %}
```

對其他 4 個 placeholder 也改 `extends "setup/_layout.html"` 並把內容包在 `{% block step_body %}`，但只放 placeholder card（會在 Task 19-22 補滿）。

- [ ] **Step 3: 啟 Flask 視覺驗證（可選）**

```bash
cd web-interface && uv run python app.py &
sleep 2
curl -s http://localhost:8004/setup | grep -i "初始化精靈"
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add web-interface/templates/setup/
git commit -m "feat(web): 加入 wizard sidebar 進度條 layout"
```

---

### Task 18：Step 1 表單 — 專案資訊

**Files:**
- Modify: `web-interface/templates/setup/project.html`

- [ ] **Step 1: 寫 integration 測試**

```python
def test_post_setup_project_writes_config(client, temp_config):
    resp = client.post("/setup/project", data={
        "project_name": "is1ab-CTF-2026",
        "organization": "is1ab",
        "flag_prefix": "is1abCTF",
        "year": "2026",
        "description": "annual CTF",
        "gzctf_url": "http://gzctf.example",
        "host": "10.0.0.1",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["project"]["name"] == "is1ab-CTF-2026"
    assert raw["project"]["flag_prefix"] == "is1abCTF"
    assert raw["platform"]["gzctf_url"] == "http://gzctf.example"
    assert raw["deployment"]["host"] == "10.0.0.1"
```

- [ ] **Step 2: 跑測試確認失敗**（多半是表單沒送對名稱）

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_project
```

- [ ] **Step 3: 完整撰寫 `web-interface/templates/setup/project.html`**

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 專案資訊" %}
{% block step_body %}
<form id="step-project-form" method="POST" action="{{ url_for('setup_step_save', step='project') }}">
  <div class="card">
    <header class="card-header">
      <p class="card-header-title"><i class="fas fa-rocket mr-2"></i> 專案基本資訊</p>
    </header>
    <div class="card-content">
      <div class="field">
        <label class="label">競賽名稱 *</label>
        <input class="input" name="project_name" value="{{ config.competition_name or '' }}" required>
      </div>
      <div class="columns">
        <div class="column">
          <div class="field">
            <label class="label">主辦組織</label>
            <input class="input" name="organization" value="{{ config.organization or '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">年份</label>
            <input class="input" type="number" name="year" value="{{ config.year or '' }}" min="2020" max="2099">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">Flag Prefix *</label>
            <input class="input" name="flag_prefix" value="{{ config.project_flag_prefix or 'is1abCTF' }}" required>
            <p class="help">參賽者送出的 flag 必須以此開頭，例如 <code>is1abCTF{...}</code></p>
          </div>
        </div>
      </div>
      <div class="field">
        <label class="label">描述</label>
        <textarea class="textarea" name="description">{{ config.description or '' }}</textarea>
      </div>
    </div>
  </div>

  <div class="card mt-4">
    <header class="card-header">
      <p class="card-header-title"><i class="fas fa-server mr-2"></i> 平台與部署（可選）</p>
    </header>
    <div class="card-content">
      <div class="columns">
        <div class="column">
          <div class="field">
            <label class="label">GZCTF URL</label>
            <input class="input" name="gzctf_url" value="{{ config.platform.gzctf_url if config.platform else '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">CTFd URL</label>
            <input class="input" name="ctfd_url" value="{{ config.platform.ctfd_url if config.platform else '' }}">
          </div>
        </div>
      </div>
      <div class="columns">
        <div class="column">
          <div class="field">
            <label class="label">部署主機</label>
            <input class="input" name="host" value="{{ config.deployment.host if config.deployment else '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">Docker Registry</label>
            <input class="input" name="docker_registry" value="{{ config.deployment.docker_registry if config.deployment else '' }}">
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="field is-grouped mt-4">
    <p class="control">
      <button type="submit" class="button is-link">儲存並下一步</button>
    </p>
    <p class="control">
      <a class="button is-text" href="{{ url_for('setup_step', step='team') }}">略過此步</a>
    </p>
  </div>
</form>

<script>
document.getElementById('step-project-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const resp = await fetch(form.action, {method: 'POST', body: fd});
  const result = await resp.json();
  if (result.status === 'success') {
    window.location.href = "{{ url_for('setup_step', step='team') }}";
  } else {
    alert(result.message || '儲存失敗');
  }
});
</script>
{% endblock %}
```

注意：`config.project_flag_prefix` 不存在於現有 normalized config — 需要在 `load_config` 補一個欄位回傳，或表單直接讀 raw config。最簡單：在 `load_config` 加一行：

```python
                "project_flag_prefix": (project.get("flag_prefix") or "").strip(),
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_project
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/app.py web-interface/templates/setup/project.html
git commit -m "feat(web): wizard step 1 - 專案資訊表單"
```

---

### Task 19：Step 2 表單 — 團隊成員（動態列表）

**Files:**
- Modify: `web-interface/templates/setup/team.html`

- [ ] **Step 1: 寫 integration 測試**

```python
def test_post_setup_team_replaces_members(client, temp_config):
    payload = {
        "default_author": "alice",
        "members": [
            {"github_username": "alice", "display_name": "Alice", "specialty": "web"},
            {"github_username": "bob", "display_name": "Bob", "specialty": "pwn"},
        ],
    }
    resp = client.post("/setup/team", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["team"]["default_author"] == "alice"
    assert len(raw["team"]["members"]) == 2
    assert raw["team"]["members"][1]["github_username"] == "bob"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_team
```

- [ ] **Step 3: 撰寫 `web-interface/templates/setup/team.html`**

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 團隊成員" %}
{% block step_body %}
<div class="card">
  <header class="card-header">
    <p class="card-header-title"><i class="fas fa-users mr-2"></i> 團隊成員</p>
  </header>
  <div class="card-content">
    <p class="content has-text-grey">
      列出所有會在這個 repo 出題或驗題的人。寫入 <code>team.members</code>。
      不指派固定驗題人；任一成員都可以 review 任一題的 PR。
    </p>

    <div class="field">
      <label class="label">預設出題人 (fallback)</label>
      <input class="input" id="default-author" type="text"
             value="{{ config.default_author or '' }}"
             placeholder="當 git user.name 也沒設時的 fallback；建議留空">
      <p class="help">建議讓每位出題人各自 <code>git config user.name</code>，這欄留空即可。</p>
    </div>

    <hr>

    <table class="table is-fullwidth" id="members-table">
      <thead>
        <tr>
          <th>GitHub username *</th>
          <th>顯示名稱</th>
          <th>專長</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for m in (config.members or []) %}
        <tr>
          <td><input class="input member-username" value="{{ m.github_username }}"></td>
          <td><input class="input member-display" value="{{ m.display_name }}"></td>
          <td>
            <div class="select is-fullwidth">
              <select class="member-specialty">
                <option value="" {{ 'selected' if not m.specialty else '' }}>—</option>
                {% for s in ["web", "pwn", "crypto", "reverse", "forensic", "misc", "general"] %}
                <option value="{{ s }}" {{ 'selected' if m.specialty == s else '' }}>{{ s }}</option>
                {% endfor %}
              </select>
            </div>
          </td>
          <td><button type="button" class="button is-small is-danger remove-row">移除</button></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <button type="button" class="button is-light" id="add-member-row">
      <i class="fas fa-plus mr-1"></i> 新增成員
    </button>
  </div>
</div>

<div class="field is-grouped mt-4">
  <p class="control">
    <button type="button" class="button is-link" id="save-team-btn">儲存並下一步</button>
  </p>
  <p class="control">
    <a class="button is-text" href="{{ url_for('setup_step', step='project') }}">回上一步</a>
  </p>
</div>

<script>
const tbody = document.querySelector('#members-table tbody');

function addRow(data = {}) {
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input class="input member-username" value="${data.github_username || ''}"></td>
    <td><input class="input member-display" value="${data.display_name || ''}"></td>
    <td><div class="select is-fullwidth"><select class="member-specialty">
      <option value="">—</option>
      <option value="web">web</option><option value="pwn">pwn</option>
      <option value="crypto">crypto</option><option value="reverse">reverse</option>
      <option value="forensic">forensic</option><option value="misc">misc</option>
      <option value="general">general</option>
    </select></div></td>
    <td><button type="button" class="button is-small is-danger remove-row">移除</button></td>`;
  if (data.specialty) tr.querySelector('.member-specialty').value = data.specialty;
  tbody.appendChild(tr);
}

document.getElementById('add-member-row').addEventListener('click', () => addRow());
tbody.addEventListener('click', (e) => {
  if (e.target.classList.contains('remove-row')) e.target.closest('tr').remove();
});

document.getElementById('save-team-btn').addEventListener('click', async () => {
  const members = Array.from(tbody.querySelectorAll('tr')).map(tr => ({
    github_username: tr.querySelector('.member-username').value.trim(),
    display_name: tr.querySelector('.member-display').value.trim(),
    specialty: tr.querySelector('.member-specialty').value.trim(),
  })).filter(m => m.github_username);

  const payload = {
    default_author: document.getElementById('default-author').value.trim(),
    members: members,
  };
  const resp = await fetch("{{ url_for('setup_step_save', step='team') }}", {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const result = await resp.json();
  if (result.status === 'success') {
    window.location.href = "{{ url_for('setup_step', step='event') }}";
  } else {
    alert(result.message || '儲存失敗');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_team
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/templates/setup/team.html
git commit -m "feat(web): wizard step 2 - 團隊成員動態列表"
```

---

### Task 20：Step 3 表單 — 比賽時程

**Files:**
- Modify: `web-interface/templates/setup/event.html`

- [ ] **Step 1: 寫測試**

```python
def test_post_setup_event_writes_dates(client, temp_config):
    resp = client.post("/setup/event", data={
        "start_date": "2026-05-01",
        "end_date": "2026-05-30",
        "authoring_deadline": "2026-04-15",
        "review_deadline": "2026-04-25",
        "freeze_deadline": "2026-04-28",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["event"]["start_date"] == "2026-05-01"
    assert raw["event"]["freeze_deadline"] == "2026-04-28"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_event
```

- [ ] **Step 3: 撰寫 `web-interface/templates/setup/event.html`**

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 比賽時程" %}
{% block step_body %}
<form id="step-event-form" method="POST" action="{{ url_for('setup_step_save', step='event') }}">
  <div class="card">
    <header class="card-header">
      <p class="card-header-title"><i class="fas fa-calendar-days mr-2"></i> 比賽時程與死線</p>
    </header>
    <div class="card-content">
      <div class="columns">
        <div class="column">
          <div class="field">
            <label class="label">比賽開始</label>
            <input class="input" type="date" name="start_date" value="{{ config.event.start_date or '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">比賽結束</label>
            <input class="input" type="date" name="end_date" value="{{ config.event.end_date or '' }}">
          </div>
        </div>
      </div>
      <hr>
      <div class="columns">
        <div class="column">
          <div class="field">
            <label class="label">出題截止</label>
            <input class="input" type="date" name="authoring_deadline" value="{{ config.event.authoring_deadline or '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">驗題截止</label>
            <input class="input" type="date" name="review_deadline" value="{{ config.event.review_deadline or '' }}">
          </div>
        </div>
        <div class="column">
          <div class="field">
            <label class="label">凍結截止</label>
            <input class="input" type="date" name="freeze_deadline" value="{{ config.event.freeze_deadline or '' }}">
          </div>
        </div>
      </div>
      <p class="help">死線僅用於提醒，目前不會 enforce。</p>
    </div>
  </div>

  <div class="field is-grouped mt-4">
    <p class="control"><button type="submit" class="button is-link">儲存並下一步</button></p>
    <p class="control"><a class="button is-text" href="{{ url_for('setup_step', step='team') }}">回上一步</a></p>
  </div>
</form>

<script>
document.getElementById('step-event-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const fd = new FormData(e.target);
  const resp = await fetch(e.target.action, {method: 'POST', body: fd});
  const result = await resp.json();
  if (result.status === 'success') {
    window.location.href = "{{ url_for('setup_step', step='quota') }}";
  } else {
    alert(result.message || '儲存失敗');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_event
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/templates/setup/event.html
git commit -m "feat(web): wizard step 3 - 比賽時程"
```

---

### Task 21：Step 4 表單 — 配額目標

**Files:**
- Modify: `web-interface/templates/setup/quota.html`

- [ ] **Step 1: 寫測試**

```python
def test_post_setup_quota_writes_dict(client, temp_config):
    payload = {
        "by_category": {"web": 6, "pwn": 4, "crypto": 3},
        "by_difficulty": {"easy": 8, "middle": 5},
        "total_target": "13",
    }
    resp = client.post("/setup/quota", json=payload)
    assert resp.status_code == 200
    raw = yaml.safe_load(temp_config.read_text())
    assert raw["challenge_quota"]["by_category"] == {"web": 6, "pwn": 4, "crypto": 3}
    assert raw["challenge_quota"]["total_target"] == 13
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_quota
```

- [ ] **Step 3: 撰寫 `web-interface/templates/setup/quota.html`**

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 配額目標" %}
{% block step_body %}
<div class="card">
  <header class="card-header">
    <p class="card-header-title"><i class="fas fa-bullseye mr-2"></i> 題目配額</p>
  </header>
  <div class="card-content">
    <p class="content has-text-grey">設定每個分類與難度的目標題數。儀表板會用此數字顯示「目前 / 目標」。</p>

    <h4 class="title is-5">按分類</h4>
    <div class="columns is-multiline" id="cat-fields">
      {% for cat in ["web", "pwn", "crypto", "reverse", "forensic", "misc", "general"] %}
      <div class="column is-3">
        <div class="field">
          <label class="label">{{ cat }}</label>
          <input class="input cat-input" type="number" min="0" data-key="{{ cat }}"
                 value="{{ (config.challenge_quota.by_category or {}).get(cat, 0) }}">
        </div>
      </div>
      {% endfor %}
    </div>

    <h4 class="title is-5">按難度</h4>
    <div class="columns" id="diff-fields">
      {% for d in ["baby", "easy", "middle", "hard", "impossible"] %}
      <div class="column">
        <div class="field">
          <label class="label">{{ d }}</label>
          <input class="input diff-input" type="number" min="0" data-key="{{ d }}"
                 value="{{ (config.challenge_quota.by_difficulty or {}).get(d, 0) }}">
        </div>
      </div>
      {% endfor %}
    </div>

    <div class="field">
      <label class="label">總目標題數</label>
      <input class="input" type="number" min="0" id="total-target"
             value="{{ config.challenge_quota.total_target or 0 }}">
    </div>
  </div>
</div>

<div class="field is-grouped mt-4">
  <p class="control"><button type="button" class="button is-link" id="save-quota-btn">儲存並下一步</button></p>
  <p class="control"><a class="button is-text" href="{{ url_for('setup_step', step='event') }}">回上一步</a></p>
</div>

<script>
document.getElementById('save-quota-btn').addEventListener('click', async () => {
  const collect = (sel) => {
    const out = {};
    document.querySelectorAll(sel).forEach(el => {
      const v = parseInt(el.value, 10);
      if (!isNaN(v) && v > 0) out[el.dataset.key] = v;
    });
    return out;
  };
  const payload = {
    by_category: collect('.cat-input'),
    by_difficulty: collect('.diff-input'),
    total_target: document.getElementById('total-target').value,
  };
  const resp = await fetch("{{ url_for('setup_step_save', step='quota') }}", {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const result = await resp.json();
  if (result.status === 'success') {
    window.location.href = "{{ url_for('setup_step', step='finalize') }}";
  } else {
    alert(result.message || '儲存失敗');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k post_setup_quota
```

- [ ] **Step 5: Commit**

```bash
git add web-interface/templates/setup/quota.html
git commit -m "feat(web): wizard step 4 - 配額目標"
```

---

### Task 22：Step 5 — finalize 表單（產生 .github + 清理）

**Files:**
- Modify: `web-interface/templates/setup/finalize.html`

- [ ] **Step 1: 加入「偵測冗餘欄位」endpoint**

在 `web-interface/app.py` 加：

```python
@app.route("/api/setup/legacy-count", methods=["GET"])
def api_setup_legacy_count():
    from setup_helpers import detect_legacy_validation_fields
    paths = detect_legacy_validation_fields(CHALLENGES_DIR)
    return jsonify({
        "count": len(paths),
        "files": [str(p.relative_to(BASE_DIR)) for p in paths],
    })
```

- [ ] **Step 2: 寫整合測試**

```python
def test_finalize_generates_github_files(client, temp_config, tmp_path):
    resp = client.post("/setup/finalize", json={
        "generate_pr_template": True,
        "generate_codeowners": True,
        "generate_branch_protection_doc": True,
        "cleanup_legacy": False,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success"
    pr_tmpl = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md"
    codeowners = tmp_path / ".github" / "CODEOWNERS"
    bp_doc = tmp_path / ".github" / "branch-protection.md"
    assert pr_tmpl.exists()
    assert codeowners.exists()
    assert bp_doc.exists()
    assert "出題人 Checklist" in pr_tmpl.read_text()


def test_legacy_count_endpoint_returns_zero_for_clean_repo(client):
    resp = client.get("/api/setup/legacy-count")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 0
```

- [ ] **Step 3: 跑測試確認失敗**

```bash
uv run pytest tests/test_setup_wizard.py -v -k "finalize_generates or legacy_count"
```

- [ ] **Step 4: 撰寫 `web-interface/templates/setup/finalize.html`**

```html
{% extends "setup/_layout.html" %}
{% set title = "初始化 - 完成" %}
{% block step_body %}
<div class="card">
  <header class="card-header">
    <p class="card-header-title"><i class="fas fa-flag-checkered mr-2"></i> 完成設定</p>
  </header>
  <div class="card-content">
    <h4 class="title is-5">將要產生的檔案</h4>
    <p class="content has-text-grey">這些檔案會寫入專案的 <code>.github/</code> 目錄。可重複執行（會覆蓋）。</p>

    <div class="field">
      <label class="checkbox">
        <input type="checkbox" id="opt-pr" checked>
        <code>.github/PULL_REQUEST_TEMPLATE.md</code> — 雙 checklist（出題人 + 驗題人）
      </label>
    </div>
    <div class="field">
      <label class="checkbox">
        <input type="checkbox" id="opt-co" checked>
        <code>.github/CODEOWNERS</code> — 留空 placeholder
      </label>
    </div>
    <div class="field">
      <label class="checkbox">
        <input type="checkbox" id="opt-bp" checked>
        <code>.github/branch-protection.md</code> — 設定指引（含 gh CLI 指令）
      </label>
    </div>

    <hr>
    <h4 class="title is-5 has-text-danger">清理冗餘驗題欄位（不可逆）</h4>
    <div class="notification is-warning is-light">
      <p id="legacy-status">偵測中…</p>
    </div>
    <div class="field">
      <label class="checkbox" id="cleanup-label" style="display:none">
        <input type="checkbox" id="opt-cleanup">
        執行清理（將從 challenges/ 下的 private.yml/public.yml 移除
        <code>reviewer</code>、<code>validation_status</code>、<code>internal_validation_notes</code> 三個 key）
      </label>
    </div>
  </div>
</div>

<div class="field is-grouped mt-4">
  <p class="control">
    <button type="button" class="button is-danger" id="run-finalize">執行</button>
  </p>
  <p class="control"><a class="button is-text" href="{{ url_for('setup_step', step='quota') }}">回上一步</a></p>
</div>

<div id="finalize-result" class="mt-4"></div>

<script>
async function loadLegacy() {
  const resp = await fetch("{{ url_for('api_setup_legacy_count') }}");
  const body = await resp.json();
  const status = document.getElementById('legacy-status');
  const label = document.getElementById('cleanup-label');
  if (body.count > 0) {
    status.innerHTML = `偵測到 <strong>${body.count}</strong> 個檔案含舊驗題欄位：<ul>` +
      body.files.map(f => `<li><code>${f}</code></li>`).join('') + '</ul>';
    label.style.display = 'block';
  } else {
    status.textContent = '未偵測到含舊欄位的檔案 — 此步可跳過。';
    label.style.display = 'none';
  }
}

document.getElementById('run-finalize').addEventListener('click', async () => {
  const payload = {
    generate_pr_template: document.getElementById('opt-pr').checked,
    generate_codeowners: document.getElementById('opt-co').checked,
    generate_branch_protection_doc: document.getElementById('opt-bp').checked,
    cleanup_legacy: document.getElementById('opt-cleanup')?.checked ?? false,
  };
  if (payload.cleanup_legacy && !confirm('確定要執行清理？這會從現有 YAML 中移除三個 key，不可逆。')) {
    return;
  }
  const resp = await fetch("{{ url_for('setup_step_save', step='finalize') }}", {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const result = await resp.json();
  const out = document.getElementById('finalize-result');
  out.innerHTML = `<div class="notification is-success"><strong>完成。</strong><ul>` +
    (result.actions || []).map(a => `<li>${a}</li>`).join('') + '</ul></div>';
  loadLegacy();
});

loadLegacy();
</script>
{% endblock %}
```

- [ ] **Step 5: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k "finalize or legacy_count"
```

- [ ] **Step 6: Commit**

```bash
git add web-interface/app.py web-interface/templates/setup/finalize.html tests/test_setup_wizard.py
git commit -m "feat(web): wizard step 5 - finalize 產生 .github/ 與清理冗餘欄位"
```

---

### Task 23：手動驗證整個 Wizard 流程

**Files:**（無，純驗證）

- [ ] **Step 1: 啟服務**

```bash
cd /Users/guantou/Desktop/is1ab-CTF-template/web-interface
uv run python app.py
```

- [ ] **Step 2: 在瀏覽器走過 5 步**

開 `http://localhost:8004/setup`，驗證：

- 自動 redirect 到 `/setup/project`
- Sidebar 顯示 5 步驟 + 灰圈圈
- Step 1 填完按下一步 → step 1 變綠 + 跳到 step 2
- Step 2 加 / 移除 member → 儲存 → 重 load 仍預填正確
- Step 3-4 同上
- Step 5 顯示「未偵測到舊欄位」（正常情況）
- 按執行 → `.github/` 出現三個檔案

- [ ] **Step 3: 還原 .github（避免汙染 repo）**

```bash
cd /Users/guantou/Desktop/is1ab-CTF-template
# 若 .github/PULL_REQUEST_TEMPLATE.md 與 CODEOWNERS 是新版（在 Phase 4 才正式覆蓋），
# 可以用 git restore 還原；若是新檔則保留並在 Phase 5 commit
git status .github/
```

- [ ] **Step 4: Commit（無代碼變動，只是 milestone 紀錄）**

跳過 commit，這是純手測 step。

---

## Phase 4：移除 `/validation` 與 reviewer UI（Tasks 24–28）

### Task 24：移除 `CTFManager` 中的驗題方法

**Files:**
- Modify: `web-interface/app.py:559-668`

- [ ] **Step 1: 從 `app.py` 刪除三個 method**

刪除：
- `get_validation_queue()` (line 559-571)
- `review_challenge()` (line 573-649)
- `_append_internal_log()` (line 651-667)

- [ ] **Step 2: 確認沒有其他呼叫**

```bash
grep -n "get_validation_queue\|review_challenge\|_append_internal_log" /Users/guantou/Desktop/is1ab-CTF-template/web-interface/app.py
```

Expected: 應只剩下要在 task 25 移除的 route 引用。

- [ ] **Step 3: Commit（與 task 25 一起 commit）**

跳過，下一個 task 一起 commit。

---

### Task 25：移除 `/validation` 路由與 template

**Files:**
- Modify: `web-interface/app.py:1264-1280`（移除 `/validation` GET）
- Modify: `web-interface/app.py:1393-1411`（移除 `api_review_challenge`）
- Delete: `web-interface/templates/validation.html`

- [ ] **Step 1: 寫測試確認 route 已移除**

```python
def test_validation_route_returns_404(client):
    resp = client.get("/validation")
    assert resp.status_code == 404


def test_api_review_route_returns_404(client):
    resp = client.post("/api/challenges/web/foo/review", json={"action": "approve", "actor": "x"})
    assert resp.status_code == 404
```

- [ ] **Step 2: 跑測試確認失敗**（route 還在）

```bash
uv run pytest tests/test_setup_wizard.py -v -k "validation_route or api_review"
```

- [ ] **Step 3: 從 `web-interface/app.py` 刪除**

刪除整段：

```python
@app.route("/validation")
def validation_queue():
    ...
```

```python
@app.route(
    "/api/challenges/<string:category>/<string:name>/review", methods=["POST"]
)
def api_review_challenge(category: str, name: str):
    ...
```

- [ ] **Step 4: 刪除 template 檔**

```bash
git rm /Users/guantou/Desktop/is1ab-CTF-template/web-interface/templates/validation.html
```

- [ ] **Step 5: 跑測試確認通過**

```bash
uv run pytest tests/test_setup_wizard.py -v -k "validation_route or api_review"
```

- [ ] **Step 6: Commit（連同 Task 24）**

```bash
git add web-interface/app.py tests/test_setup_wizard.py
git commit -m "refactor(web): 移除 /validation 路由、review_challenge 與 validation.html

驗題流程改由 GitHub PR review 處理，不再於 Web GUI 維護 validation_status。"
```

---

### Task 26：移除 nav 列「驗題」連結

**Files:**
- Modify: `web-interface/templates/base.html`

- [ ] **Step 1: 找到 nav 連結**

```bash
grep -n "驗題\|validation" /Users/guantou/Desktop/is1ab-CTF-template/web-interface/templates/base.html
```

- [ ] **Step 2: 從 `base.html` 刪除「驗題」`<a>`**

具體刪除整個包含 `url_for('validation_queue')` 或文字「驗題」的 `<a class="navbar-item">` 元素（保留其他導覽項）。

- [ ] **Step 3: 啟服務驗證**

```bash
cd web-interface && uv run python app.py &
sleep 2
curl -s http://localhost:8004/ | grep -c "驗題"
kill %1
```

Expected: 0（已不再出現）。

- [ ] **Step 4: Commit**

```bash
git add web-interface/templates/base.html
git commit -m "refactor(web): 從 nav 移除「驗題」連結"
```

---

### Task 27：從 `create_challenge.html` 移除 reviewer 欄位

**Files:**
- Modify: `web-interface/templates/create_challenge.html:25,221-238`
- Modify: `web-interface/app.py`（`create_challenge` method 中的 reviewer 處理）

- [ ] **Step 1: 找到 reviewer 相關 HTML**

```bash
grep -n "reviewer" /Users/guantou/Desktop/is1ab-CTF-template/web-interface/templates/create_challenge.html
```

- [ ] **Step 2: 刪除這幾段**

從 `create_challenge.html` 移除：

- 描述段中提到 `team.reviewers` 的字句（line 25 附近）
- 整個 `<div class="field">` 內含 `name="reviewer"` 與其 datalist（line 215-240 附近）

- [ ] **Step 3: 從 `app.py` 的 `create_challenge` method 移除 reviewer 處理**

找到 `web-interface/app.py:795-1108`（`def create_challenge(self, challenge_data)`），刪除所有：
- `reviewer = challenge_data.get("reviewer", "")`
- 寫入 `private.yml` 時的 `reviewer` / `validation_status` / `internal_validation_notes` 三 key

- [ ] **Step 4: 寫測試**

```python
def test_web_create_challenge_does_not_write_reviewer(client, temp_config, tmp_path):
    # 預先 setup
    temp_config.write_text(yaml.safe_dump({
        "project": {"name": "t", "flag_prefix": "tCTF"},
        "team": {"members": [{"github_username": "alice", "display_name": "Alice"}]},
        "points": {"easy": 100},
    }))
    import importlib, app as app_module
    importlib.reload(app_module)
    c = app_module.app.test_client()

    resp = c.post("/api/challenges", json={
        "category": "web",
        "name": "test_no_reviewer",
        "difficulty": "easy",
        "author": "alice",
    })
    assert resp.status_code in (200, 201)
    private_yml = tmp_path / "challenges/web/test_no_reviewer/private.yml"
    if private_yml.exists():
        data = yaml.safe_load(private_yml.read_text())
        assert "reviewer" not in data
        assert "validation_status" not in data
```

- [ ] **Step 5: 跑測試**

```bash
uv run pytest tests/test_setup_wizard.py -v -k web_create_challenge
```

- [ ] **Step 6: Commit**

```bash
git add web-interface/templates/create_challenge.html web-interface/app.py tests/test_setup_wizard.py
git commit -m "refactor(web): /create 表單與 API 移除 reviewer 欄位處理"
```

---

### Task 28：舊 `/setup` 單頁邏輯收尾

**Files:**
- Modify: `web-interface/app.py`（既有 `save_setup` 可保留 or 標 deprecated）
- Delete or rewrite: `web-interface/templates/setup.html`

- [ ] **Step 1: 確認 `save_setup` 還有沒有被其他 route 用**

```bash
grep -n "save_setup" /Users/guantou/Desktop/is1ab-CTF-template/web-interface/app.py
```

- [ ] **Step 2: 若仍有 `/api/setup` 之類舊 endpoint，刪除或改成 redirect**

如果有 `@app.route("/api/setup", methods=["POST"])` 把 form 整批 POST 進來，現在改用 5 步驟即可。刪除這個 endpoint 與 `save_setup` method。

- [ ] **Step 3: 刪除舊 `setup.html`**

```bash
git rm /Users/guantou/Desktop/is1ab-CTF-template/web-interface/templates/setup.html
```

（注意：`/setup` 路由已在 Task 16 改為 redirect 到 `/setup/project`，不再 render `setup.html`）

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "chore(web): 移除舊單頁 /setup 與 save_setup（已被 wizard 取代）"
```

---

## Phase 5：文件更新（Tasks 29–32）

### Task 29：`docs/authoring-challenges.md` 改寫驗題段

**Files:**
- Modify: `docs/authoring-challenges.md`

- [ ] **Step 1: 重寫驗題段落**

把第 4 章（驗題與欄位說明）替換為：

```markdown
## 4. 驗題流程

驗題透過 **GitHub Pull Request review** 進行：

1. 出題人推 branch 並開 PR
2. 任一其他團隊成員自願擔任驗題人，將 branch checkout 到本地
3. 跑起 Docker / 解題、確認 flag 與 `private.yml` 一致
4. 在 PR 上 approve（或留言請出題人修正）
5. CI 通過 + 至少 1 approval → 可 merge

PR template 提供雙 checklist（出題人填一份、驗題人填一份），由 `/setup` 精靈產生於 `.github/PULL_REQUEST_TEMPLATE.md`。

驗題人**不固定指派**：CODEOWNERS 留空、不強制特定路徑由特定人審。

## 5. 相關文件

- `web-interface/USAGE.md` — 介面啟動與 `/setup` 精靈說明
- `wiki/Web-GUI-Integration.md` — Web 與安全流程的關係
- `docs/ctf-challenge-workflow.md` — 整體 CTF 工作流程
- `docs/challenge-metadata-standard.md` — YAML 欄位規範
- `.github/branch-protection.md` — branch protection 設定指引（由 `/setup` 產生）
```

並把第 1 章的 `team.reviewers` 改為 `team.members`，第 2 章 Web GUI 描述去掉「驗題」分頁、加上「初始化精靈 5 步驟」。

- [ ] **Step 2: 確認沒有殘留**

```bash
grep -E "/validation|reviewer 必填|validation_status|internal_validation_notes" docs/authoring-challenges.md
```

Expected: 無輸出。

- [ ] **Step 3: Commit**

```bash
git add docs/authoring-challenges.md
git commit -m "docs(authoring): 改寫驗題段為 PR review 流程"
```

---

### Task 30：`web-interface/USAGE.md` + `wiki/Web-GUI-Integration.md`

**Files:**
- Modify: `web-interface/USAGE.md`
- Modify: `wiki/Web-GUI-Integration.md`

- [ ] **Step 1: 改寫 `web-interface/USAGE.md`**

把「驗題與配額」段改成「**初始化精靈** `/setup`」段：

```markdown
## 🧙 初始化精靈

第一次使用請先進入 `/setup` 精靈完成 5 步驟設定：

| Step | 路徑 | 內容 |
|------|------|------|
| 1 | `/setup/project` | 競賽名稱、flag prefix、平台 URL |
| 2 | `/setup/team` | 團隊成員（github_username / 顯示名 / 專長） |
| 3 | `/setup/event` | 比賽時程與死線 |
| 4 | `/setup/quota` | 各類別 / 難度的目標題數 |
| 5 | `/setup/finalize` | 產生 `.github/` 模板（PR template / CODEOWNERS / branch-protection 指引），可選清理舊版驗題欄位 |

可隨時回任一步調整（idempotent）。

## ✅ 驗題流程

驗題透過 **GitHub Pull Request review** 進行（不在 Web GUI 中操作）。
PR template 由 `/setup/finalize` 產生於 `.github/PULL_REQUEST_TEMPLATE.md`，含出題人與驗題人雙 checklist。

詳細流程：[docs/authoring-challenges.md](../docs/authoring-challenges.md)。
```

並移除原文中提到 `/validation` 與 `validation_status` 的段落。

- [ ] **Step 2: 同樣方式改寫 `wiki/Web-GUI-Integration.md`**

- [ ] **Step 3: Commit**

```bash
git add web-interface/USAGE.md wiki/Web-GUI-Integration.md
git commit -m "docs(web): USAGE 與 Web-GUI-Integration 改寫為 wizard + PR review 流程"
```

---

### Task 31：`docs/ctf-challenge-workflow.md` — 階段名稱更新

**Files:**
- Modify: `docs/ctf-challenge-workflow.md`

- [ ] **Step 1: 找到「2.3 Code Review」**

```bash
grep -n "Code Review" docs/ctf-challenge-workflow.md | head -10
```

- [ ] **Step 2: 把章節標題與內文「Code Review」改名「驗題」**

不只換標題，把段落內描述（「審查者需要檢查」、「審查者注意事項」等）改成驗題語境：

```markdown
### 2.3 驗題

任一團隊成員（不固定指派）擔任驗題人：

#### 驗題人檢查項目

- [ ] 已將 PR branch checkout 到本地
- [ ] 起 Docker（或建置）成功
- [ ] 實際解出 flag，與 `private.yml` 一致
- [ ] 難度標示與實際解題感受一致
- [ ] 提示（hints）合理、不直接洩答
- [ ] Writeup 完整可讀
- [ ] 沒有 flag 洩漏到 `public.yml` / 公開檔案中

#### Approve 與 Merge

驗題人在 GitHub PR 上 approve；CI 通過 + 1 個 approval 即可 merge。
若有問題可在 PR 留言請出題人修正後再次 push。
```

- [ ] **Step 3: Commit**

```bash
git add docs/ctf-challenge-workflow.md
git commit -m "docs(workflow): 將「Code Review」改名為「驗題」並更新檢查清單"
```

---

### Task 32：`README.md` 初始化檢查清單

**Files:**
- Modify: `README.md:135-145`

- [ ] **Step 1: 找到檢查清單**

```bash
grep -n "初始化檢查清單" README.md
```

- [ ] **Step 2: 替換清單**

把：

```markdown
## 初始化檢查清單

使用 Template 建立私有 repo 後，完成以下設定：

- [ ] `make setup` — 安裝 Git Hooks + 驗證環境
- [ ] 編輯 `config.yml` — 設定 flag_prefix、平台 URL
- [ ] 編輯 `.github/CODEOWNERS` — 替換 `@admin`/`@senior-dev` 為實際用戶名
- [ ] 設定 GitHub Secrets — 參閱 [GitHub Secrets 指南](wiki/GitHub-Secrets-Setup.md)
- [ ] 設定分支保護 — 參閱 [分支保護指南](wiki/Branch-Protection-Setup.md)
- [ ] （推薦）設定 GPG 簽名 — 參閱 [Commit 簽名指南](wiki/Commit-Signing-Guide.md)
```

改為：

```markdown
## 初始化檢查清單

使用 Template 建立私有 repo 後，完成以下設定：

- [ ] `make setup` — 安裝 Git Hooks + 驗證環境
- [ ] 啟動 `cd web-interface && uv run python app.py`，進入 `http://localhost:8004/setup` 走完 **5 步驟初始化精靈**
  - 步驟 5 會自動產生 `.github/PULL_REQUEST_TEMPLATE.md`、`CODEOWNERS`、`branch-protection.md`
- [ ] 依 `.github/branch-protection.md` 在 GitHub 設定 main 分支保護
- [ ] 設定 GitHub Secrets — 參閱 [GitHub Secrets 指南](wiki/GitHub-Secrets-Setup.md)
- [ ] （推薦）設定 GPG 簽名 — 參閱 [Commit 簽名指南](wiki/Commit-Signing-Guide.md)

> 沒有 Web GUI？也可手動編輯 `config.yml`，並執行 `uv run python scripts/cleanup-validation-fields.py --dry-run`（如有舊版題目需清理）。
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): 初始化檢查清單改為 /setup 精靈引導"
```

---

## Phase 6：覆蓋既有 `.github/` 檔案（Tasks 33–34）

### Task 33：覆蓋 `.github/PULL_REQUEST_TEMPLATE.md` 與 `CODEOWNERS`

**Files:**
- Modify: `.github/PULL_REQUEST_TEMPLATE.md`
- Modify: `.github/CODEOWNERS`
- Create: `.github/branch-protection.md`

- [ ] **Step 1: 用 helper 產生新內容並覆蓋**

```bash
cd /Users/guantou/Desktop/is1ab-CTF-template
uv run python -c "
import sys
sys.path.insert(0, 'scripts')
from setup_helpers import generate_pr_template, generate_codeowners, generate_branch_protection_doc
import yaml
config = yaml.safe_load(open('config.yml'))
open('.github/PULL_REQUEST_TEMPLATE.md', 'w').write(generate_pr_template(config))
open('.github/CODEOWNERS', 'w').write(generate_codeowners(config))
open('.github/branch-protection.md', 'w').write(generate_branch_protection_doc(config))
print('OK')
"
```

- [ ] **Step 2: 確認新內容無誤**

```bash
head -20 .github/PULL_REQUEST_TEMPLATE.md
head -10 .github/CODEOWNERS
head -10 .github/branch-protection.md
```

- [ ] **Step 3: Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE.md .github/CODEOWNERS .github/branch-protection.md
git commit -m "chore(github): 覆蓋 PR template / CODEOWNERS、新增 branch-protection 指引"
```

---

### Task 34：最後一輪整合測試 + push

**Files:**（無，純驗證）

- [ ] **Step 1: 全測試**

```bash
cd /Users/guantou/Desktop/is1ab-CTF-template
uv run pytest -v
```

Expected: 全部 PASS。

- [ ] **Step 2: 全題目 validate**

```bash
make validate-all
```

Expected: 全部 PASS（清理冗餘欄位後不該破壞既有 validate）。

- [ ] **Step 3: scan-secrets**

```bash
make scan
```

Expected: 沒有 CRITICAL / HIGH 新問題。

- [ ] **Step 4: 啟 Web GUI 走完 wizard 一遍**

```bash
cd web-interface && uv run python app.py
```

開瀏覽器走 `/setup` → 5 步全部 done → 看到 finalize 顯示「完成」。

- [ ] **Step 5: 確認沒有殘留 reviewer / validation_status**

```bash
grep -rE "validation_status|internal_validation_notes" --include='*.yml' --include='*.py' --include='*.md' . | grep -v '.git\|.venv\|tests/fixtures\|docs/superpowers'
```

Expected: 只有 spec / plan 文件中的歷史紀錄出現（fixtures 是預期的）。

- [ ] **Step 6: 最終 commit（清理 todo）+ push**

```bash
# 若無 file 變動，跳過 commit
git status
git push  # 若 user 同意才 push
```

---

## 完成驗收

跑完所有 task 後應達到：

- ✅ `web-interface/app.py` 中無 `validation_queue` / `review_challenge` / `_append_internal_log` / `/validation`
- ✅ `scripts/create-challenge.py` 無 `--reviewer`、author 順序：flag > git > config
- ✅ 新增題目產出的 `private.yml` 不含 `reviewer` / `validation_status` / `internal_validation_notes`
- ✅ Web `/setup/project|team|event|quota|finalize` 5 路由皆可用、idempotent
- ✅ `.github/PULL_REQUEST_TEMPLATE.md` 為雙 checklist 內容
- ✅ `.github/CODEOWNERS` 為留空 placeholder
- ✅ `.github/branch-protection.md` 存在含 gh CLI 指令
- ✅ `config.yml` 的 `sensitive_yaml_fields` 含三個防呆欄位
- ✅ 文件 6 份皆已更新
- ✅ `tests/` 下測試全部 PASS
- ✅ 既有題目（如 `challenges/examples/`）若曾被 reviewer 機制汙染，可用 cleanup CLI 清掉

---

## 風險檢查清單

實作過程中若遇到：

- **`importlib.reload(app_module)` 在 pytest 中行為怪異** — 改用 `pytest-flask` 或在 fixture 裡直接 monkeypatch `app.config` 而非 reload
- **`team.members` 遷移後舊欄位仍在 config.yml** — 可選擇保留（向後相容）或在 Task 13 增加遷移後移除舊欄位的邏輯（spec 沒要求，可不做）
- **PyYAML round-trip 順序變動** — `sort_keys=False` 已設，但 dict insertion order 仍會被尊重（Python 3.7+）
- **Flask `request.get_json()` 對 form 不適用** — Task 16 的 fallback 邏輯已處理（`request.get_json(silent=True) or request.form.to_dict(flat=False)`）
- **既有 web 測試 fixture 互相干擾** — 用 `monkeypatch` 隔離，必要時加 `pytest-xdist` 或 `pytest-isolate`

---

## 不在此 plan 內（未來工作）

- 配額 / 死線的 CI enforcement
- GitHub API 自動套 branch protection
- Web GUI auth / HTTPS
- 「待驗 PR 儀表板」（讀 GitHub API）
