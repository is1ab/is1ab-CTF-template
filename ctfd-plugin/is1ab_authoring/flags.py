"""is1ab_authoring 的 flag / tag 同步（從 __init__.py 抽出，拆檔第四步）。

只負責把表單/匯入來的 flag、tags 寫回 CTFd 原生表（Flags / Tags）。純寫入，
不依賴 __init__（只吃 challenge_id 與字串），可被 routes/import 流程共用。
"""

from __future__ import annotations

import warnings

from sqlalchemy.exc import SAWarning

from CTFd.models import Flags, Tags, db


def _sync_flag(challenge_id, content, flag_match, commit=True):
    """建 CTFd flag。flag_match（exact/regex）或直接的 CTFd type 皆可：只有 regex→regex，其餘→static。"""
    ctfd_type = "regex" if str(flag_match).lower() == "regex" else "static"
    Flags.query.filter_by(challenge_id=challenge_id).delete()
    if content:
        db.session.add(Flags(challenge_id=challenge_id, type=ctfd_type, content=content))
    # CTFd 的 Flags model 只有 polymorphic_on、沒有 static/regex 子類（核心自己也是這樣用
    # Flags(type=...) 建，見 FlagSchema），flush 時會噴 benign 的 SAWarning。純靜音、不改行為。
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SAWarning,
                                message=r".*incompatible polymorphic identity.*")
        db.session.commit() if commit else db.session.flush()


def _sync_tags(challenge_id, tags_csv, commit=True):
    Tags.query.filter_by(challenge_id=challenge_id).delete()
    for value in [t.strip() for t in (tags_csv or "").split(",") if t.strip()]:
        db.session.add(Tags(challenge_id=challenge_id, value=value))
    db.session.commit() if commit else db.session.flush()
