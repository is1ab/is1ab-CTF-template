"""is1ab_authoring 的出題進度儀表板彙總（從 __init__.py 抽出，拆檔第四步）。

純讀取聚合：把配額（quota）、指派（assignment）、題目（challenge）、metadata 交叉出
「每格幾個 slot、誰出、誰驗、進度」的矩陣，供 quota_page / dashboard 兩個 route render。

刻意不 import __init__（避免循環）：受控詞彙從 config、DB model 從 models/CTFd.models 取；
`_challenge_difficulty`、`_users_map` 這兩個小 helper 一併搬進來（__init__ 的 route 會 re-import
沿用同名），`STALE_DAYS` 亦只有本檔用到，直接定義於此。
"""

from __future__ import annotations

from datetime import datetime

import yaml

from CTFd.models import Challenges, Users

from .config import categories as _categories, difficulties as _difficulties
from .models import Assignment, ChallengeMetadata, ChallengeQuota

STALE_DAYS = 7   # developing/testing 超過幾天沒動 → 視為停滯（該催）


def _challenge_difficulty(challenge_id):
    """從題目的 metadata blob 讀 difficulty（配額對帳用）。"""
    meta = ChallengeMetadata.query.filter_by(challenge_id=challenge_id).first()
    if not meta or not meta.blob:
        return ""
    try:
        data = yaml.safe_load(meta.blob) or {}
    except yaml.YAMLError:
        return ""
    return str(data.get("difficulty", "")).strip() if isinstance(data, dict) else ""


def _quota_data():
    """回傳 {category: {difficulty: (target, actual)}}。"""
    targets = {(q.category, q.difficulty): q.target for q in ChallengeQuota.query.all()}
    actual = {}
    for c in Challenges.query.all():
        key = (c.category or "", _challenge_difficulty(c.id))
        actual[key] = actual.get(key, 0) + 1
    data = {}
    for cat in _categories():
        data[cat] = {d: (targets.get((cat, d), 0), actual.get((cat, d), 0)) for d in _difficulties()}
    return data


def _users_map():
    return {u.id: u.name for u in Users.query.all()}


def _dashboard_matrix():
    """回傳 {category: {difficulty: {'slots': [...], 'target': N}}}。

    每格拆成 target 個 slot（配額幾題就幾個位）。每個 slot：
      - 已有題目 → 題目連結（+ 出題者小字）
      - 只有指派、還沒建題 → 出題者名稱（未建）
      - 都沒有（配額還沒補滿）→ 缺
    """
    targets = {(q.category, q.difficulty): q.target for q in ChallengeQuota.query.all()}
    umap = _users_map()
    chal_by_id = {c.id: c for c in Challenges.query.all()}
    metas = ChallengeMetadata.query.all()
    owner_by_cid = {m.challenge_id: m.owner_id for m in metas}
    status_by_cid = {m.challenge_id: m.dev_status for m in metas}

    def _blob_test(m):
        try:
            b = yaml.safe_load(m.blob) if m.blob else {}
            t = (b or {}).get("testing") if isinstance(b, dict) else {}
            return (t or {}).get("test_status") if isinstance(t, dict) else None
        except Exception:
            return None
    test_by_cid = {m.challenge_id: _blob_test(m) for m in metas}

    chal_cell = {cat: {d: [] for d in _difficulties()} for cat in _categories()}
    uncategorized = []   # C1：落在固定格外的題（自由填分類/空難度）→ 收容，不讓它從追蹤消失
    for c in Challenges.query.order_by(Challenges.id).all():
        cat, diff = (c.category or ""), _challenge_difficulty(c.id)
        if cat in chal_cell and diff in chal_cell[cat]:
            chal_cell[cat][diff].append(c)
        else:
            uncategorized.append({"cid": c.id, "cname": c.name,
                                  "category": cat or "（空）", "difficulty": diff or "（空）",
                                  "author": umap.get(owner_by_cid.get(c.id)),
                                  "status": status_by_cid.get(c.id)})

    asg_cell = {cat: {d: [] for d in _difficulties()} for cat in _categories()}
    for a in Assignment.query.all():
        if a.category in asg_cell and a.difficulty in asg_cell[a.category]:
            asg_cell[a.category][a.difficulty].append(a)

    data = {}
    for cat in _categories():
        data[cat] = {}
        for d in _difficulties():
            target = targets.get((cat, d), 0)
            slots, linked = [], set()
            for a in asg_cell[cat][d]:                      # 先放指派（出題者 + 驗題者）
                chal = chal_by_id.get(a.challenge_id) if a.challenge_id else None
                if chal:
                    linked.add(chal.id)
                # 出題者：優先指派者，其次題目擁有者
                author = umap.get(a.author_id) or (umap.get(owner_by_cid.get(chal.id)) if chal else None)
                slots.append({"author": author, "author_id": a.author_id,
                              "reviewers": [umap.get(int(x)) for x in (a.reviewer_ids or "").split(",") if x],
                              "cid": chal.id if chal else None,
                              "cname": chal.name if chal else None,
                              "status": status_by_cid.get(chal.id) if chal else None,
                              "review": test_by_cid.get(chal.id) if chal else None})
            for c in chal_cell[cat][d]:                     # 再放沒對應指派的題（顯示擁有者 + 進度）
                if c.id not in linked:
                    slots.append({"author": umap.get(owner_by_cid.get(c.id)), "author_id": None,
                                  "reviewers": [], "cid": c.id, "cname": c.name,
                                  "status": status_by_cid.get(c.id),
                                  "review": test_by_cid.get(c.id)})
            while len(slots) < target:                      # 補滿到配額數 → 缺
                slots.append({"author": None, "author_id": None, "reviewers": [],
                              "cid": None, "cname": None, "status": None})
            data[cat][d] = {"slots": slots, "target": target}

    # KPI 彙總（E1）：跨格加總，讓 PM 一眼看「還差多少、完成幾成」
    built = completed = missing = 0
    for cat in _categories():
        for d in _difficulties():
            cell = data[cat][d]
            cell_built = sum(1 for s in cell["slots"] if s["cid"])
            built += cell_built
            completed += sum(1 for s in cell["slots"]
                             if s["status"] in ("completed", "deployed"))
            missing += max(0, cell["target"] - cell_built)
    # 停滯偵測（E2）：developing/testing 超過 STALE_DAYS 天沒動 → 該催了
    now = datetime.utcnow()
    stalled = []
    for m in metas:
        if m.dev_status in ("developing", "testing") and m.dev_status_at:
            age = (now - m.dev_status_at).days
            if age >= STALE_DAYS:
                ch = chal_by_id.get(m.challenge_id)
                if ch:
                    stalled.append({"cid": ch.id, "cname": ch.name, "days": age,
                                    "author": umap.get(m.owner_id), "status": m.dev_status})
    stalled.sort(key=lambda x: -x["days"])

    total_target = sum(targets.values())
    denom = max(total_target, built)   # 配額未設滿時，用已建題數當分母，避免完成率爆表
    summary = {"target": total_target, "built": built, "completed": completed,
               "missing": missing, "uncat": len(uncategorized), "stalled": len(stalled),
               "rate": (round(completed * 100 / denom) if denom else 0)}
    return {"grid": data, "summary": summary, "uncategorized": uncategorized, "stalled": stalled}
