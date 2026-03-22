#!/usr/bin/env python3
"""Generate viewer-only artifact data.

This script builds a safe, read-only dataset for the internal progress viewer.
It intentionally copies ONLY:
- challenges/**/public.yml (sanitized)
- challenges/**/README.md
- a derived attachment metadata list from challenges/**/files/

Output layout (default: viewer/data):
  viewer/data/
    index.json
    progress.json
    challenges/<category>/<name>/{public.yml,README.md,files.json}

This output is designed to be committed to the CI-managed `viewer-data` branch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


DEFAULT_STATUSES = ["planning", "developing", "testing", "completed", "deployed"]
DEFAULT_DIFFICULTIES = ["baby", "easy", "middle", "hard", "impossible"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return load_yaml(path)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def safe_copy_file(src: Path, dst: Path) -> None:
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)


def file_size(path: Path) -> int:
    return path.stat().st_size


def file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_public_yml(data: Dict[str, Any], extra_sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    # Defense-in-depth: even though we only read public.yml, strip any sensitive keys.
    sensitive_keys = {
        "flag",
        "flags",
        "real_flag",
        "actual_flag",
        "flag_description",
        "flag_type",
        "dynamic_flag",
        "solution_steps",
        "solution",
        "solutions",
        "internal_notes",
        "internal_note",
        "private_notes",
        "test_credentials",
        "credentials",
        "admin_password",
        "deploy_secrets",
        "secrets",
        "secret_key",
        "verified_solutions",
        "exploits",
        "token",
        "password",
        "api_key",
    }
    if extra_sensitive_keys:
        sensitive_keys.update(extra_sensitive_keys)

    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if key in sensitive_keys:
            continue
        sanitized[key] = value

    return sanitized


def list_attachments(files_dir: Path) -> List[Dict[str, Any]]:
    if not files_dir.exists() or not files_dir.is_dir():
        return []

    items: List[Dict[str, Any]] = []
    for p in sorted(files_dir.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file():
            continue
        items.append(
            {
                "name": p.name,
                "size": file_size(p),
                "modified_at": file_mtime_iso(p),
            }
        )
    return items


@dataclass(frozen=True)
class ChallengeEntry:
    category: str
    name: str
    title: str
    difficulty: str
    status: str
    points: int
    owners: List[str]
    assignee: str
    ready_for_release: bool
    author: str
    updated_at: str
    rel_path: str


def coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)]


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def normalize_username(s: str) -> str:
    return s.strip().lstrip("@").strip()


def collect_challenges(challenges_dir: Path) -> List[Tuple[Path, Path]]:
    pairs: List[Tuple[Path, Path]] = []
    if not challenges_dir.exists():
        return pairs

    for category_dir in sorted(challenges_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        for challenge_dir in sorted(category_dir.iterdir()):
            if not challenge_dir.is_dir():
                continue
            public_yml = challenge_dir / "public.yml"
            readme = challenge_dir / "README.md"
            if public_yml.exists() and readme.exists():
                pairs.append((public_yml, readme))
    return pairs


def build_entries(
    config: Dict[str, Any],
    challenges_dir: Path,
    output_data_dir: Path,
) -> Tuple[List[ChallengeEntry], Dict[str, Any]]:
    extra_sensitive_keys = config.get("security", {}).get("sensitive_yaml_fields", [])

    entries: List[ChallengeEntry] = []

    pairs = collect_challenges(challenges_dir)
    for public_yml_path, readme_path in pairs:
        challenge_dir = public_yml_path.parent
        category = challenge_dir.parent.name
        name = challenge_dir.name

        public_raw = load_yaml(public_yml_path)
        public_data = sanitize_public_yml(public_raw, extra_sensitive_keys=extra_sensitive_keys)

        title = str(public_data.get("title") or name)
        difficulty = str(public_data.get("difficulty") or "")
        status = str(public_data.get("status") or "planning")
        points = coerce_int(public_data.get("points"))
        author = str(public_data.get("author") or "")
        owners = [normalize_username(x) for x in coerce_str_list(public_data.get("owners"))]
        assignee = normalize_username(str(public_data.get("assignee") or ""))
        ready_for_release = coerce_bool(public_data.get("ready_for_release"))
        updated_at = str(public_data.get("updated_at") or public_data.get("created_at") or "")

        rel_path = f"challenges/{category}/{name}"

        # Write per-challenge files into viewer/data
        out_dir = output_data_dir / "challenges" / category / name
        ensure_dir(out_dir)

        safe_copy_file(readme_path, out_dir / "README.md")
        safe_write_text(out_dir / "public.yml", yaml.safe_dump(public_data, sort_keys=False, allow_unicode=True))

        attachments = list_attachments(challenge_dir / "files")
        safe_write_text(out_dir / "files.json", json.dumps({"items": attachments}, ensure_ascii=False, indent=2) + "\n")

        entries.append(
            ChallengeEntry(
                category=category,
                name=name,
                title=title,
                difficulty=difficulty,
                status=status,
                points=points,
                owners=owners,
                assignee=assignee,
                ready_for_release=ready_for_release,
                author=author,
                updated_at=updated_at,
                rel_path=rel_path,
            )
        )

    # Derive progress stats
    quota = config.get("challenge_quota", {})
    team_quota = config.get("team_quota", {})

    by_category: Dict[str, Any] = {}
    by_difficulty: Dict[str, Any] = {}
    by_status: Dict[str, int] = {k: 0 for k in DEFAULT_STATUSES}
    by_member: Dict[str, Any] = {}

    for e in entries:
        by_status[e.status] = by_status.get(e.status, 0) + 1

        by_category.setdefault(e.category, {"count": 0})
        by_category[e.category]["count"] += 1

        by_difficulty.setdefault(e.difficulty or "", {"count": 0})
        by_difficulty[e.difficulty or ""]["count"] += 1

        # member stats (use assignee as primary)
        if e.assignee:
            by_member.setdefault(e.assignee, {"assigned": 0, "completed": 0, "by_category": {}, "by_difficulty": {}})
            by_member[e.assignee]["assigned"] += 1
            if e.status in {"completed", "deployed"}:
                by_member[e.assignee]["completed"] += 1
            by_member[e.assignee]["by_category"].setdefault(e.category, 0)
            by_member[e.assignee]["by_category"][e.category] += 1
            by_member[e.assignee]["by_difficulty"].setdefault(e.difficulty or "", 0)
            by_member[e.assignee]["by_difficulty"][e.difficulty or ""] += 1

    # Attach quotas for UI
    by_category_quota = quota.get("by_category", {})
    for cat, obj in by_category.items():
        obj["quota"] = int(by_category_quota.get(cat, 0) or 0)

    by_difficulty_quota = quota.get("by_difficulty", {})
    for diff, obj in by_difficulty.items():
        if not diff:
            obj["quota"] = 0
        else:
            obj["quota"] = int(by_difficulty_quota.get(diff, 0) or 0)

    by_member_quota = team_quota.get("by_member", {})
    for member, obj in by_member.items():
        quota_obj = by_member_quota.get(member, {})
        obj["quota_total"] = int(quota_obj.get("total", 0) or 0)
        obj["quota_by_category"] = quota_obj.get("by_category", {}) or {}
        obj["quota_by_difficulty"] = quota_obj.get("by_difficulty", {}) or {}

    stats: Dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "total": len(entries),
        "by_status": by_status,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "by_member": by_member,
        "quota": {
            "by_category": by_category_quota,
            "by_difficulty": by_difficulty_quota,
            "total_target": int(quota.get("total_target", 0) or 0),
        },
        "team_quota": team_quota,
    }

    return entries, stats


def write_index(output_data_dir: Path, entries: List[ChallengeEntry]) -> None:
    # sorted for stable output
    entries_sorted = sorted(entries, key=lambda e: (e.category, e.name))

    payload = {
        "generated_at": utc_now_iso(),
        "items": [
            {
                "category": e.category,
                "name": e.name,
                "title": e.title,
                "difficulty": e.difficulty,
                "status": e.status,
                "points": e.points,
                "owners": e.owners,
                "assignee": e.assignee,
                "ready_for_release": e.ready_for_release,
                "author": e.author,
                "updated_at": e.updated_at,
                "data_path": f"data/challenges/{e.category}/{e.name}",
            }
            for e in entries_sorted
        ],
    }

    safe_write_text(output_data_dir / "index.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def write_progress(output_data_dir: Path, stats: Dict[str, Any]) -> None:
    safe_write_text(output_data_dir / "progress.json", json.dumps(stats, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate viewer-only artifact data")
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--challenges", default="challenges")
    parser.add_argument("--output", default="viewer/data")
    parser.add_argument("--clean", action="store_true", help="Remove output directory before generating")

    args = parser.parse_args()

    config_path = Path(args.config)
    challenges_dir = Path(args.challenges)
    output_data_dir = Path(args.output)

    config = load_config(config_path)

    if args.clean and output_data_dir.exists():
        shutil.rmtree(output_data_dir)

    ensure_dir(output_data_dir)

    entries, stats = build_entries(config, challenges_dir, output_data_dir)
    write_index(output_data_dir, entries)
    write_progress(output_data_dir, stats)

    print(f"✅ Generated viewer data: {output_data_dir}")
    print(f"   Challenges: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
