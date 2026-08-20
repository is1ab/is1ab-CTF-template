"""is1ab_authoring 的 DB models（從 __init__.py 抽出，拆檔第二步）。

只依賴 CTFd 的共享 db；被 __init__.py import 後即註冊到 metadata（db.create_all 會建表）。
四張表：challenge metadata / 配額 / 出題工單 / 留言。
"""

from __future__ import annotations

from datetime import datetime

from CTFd.models import db


class ChallengeMetadata(db.Model):
    __tablename__ = "is1ab_challenge_metadata"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # F1
    collaborators = db.Column(db.Text, default="")       # Phase 6：可共同編輯的 user id（逗號分隔）
    dev_status = db.Column(db.String(32), default="developing")  # Ⓑ 開發進度單一真相 → public.yml.status
    dev_status_at = db.Column(db.DateTime, nullable=True)  # 最後異動時間（停滯偵測用）
    uid = db.Column(db.String(16), nullable=True)        # Ⓓ 隱形亂碼綁定鍵
    repo_path = db.Column(db.String(255), nullable=True)  # Ⓓ 可讀目錄 <cat>/<slug>
    blob = db.Column("metadata_yaml", db.Text, default="")

    def __init__(self, challenge_id, owner_id=None, uid=None, repo_path=None, blob="",
                 collaborators="", dev_status="developing"):
        self.challenge_id = challenge_id
        self.owner_id = owner_id
        self.collaborators = collaborators
        self.dev_status = dev_status
        self.dev_status_at = datetime.utcnow()
        self.uid = uid
        self.repo_path = repo_path
        self.blob = blob


class ChallengeQuota(db.Model):
    """各 category×difficulty 的目標題數。"""

    __tablename__ = "is1ab_quota"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(32), nullable=False)
    difficulty = db.Column(db.String(32), nullable=False)
    target = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint("category", "difficulty", name="uq_quota_cat_diff"),)


class Assignment(db.Model):
    """出題工單：PM 指派誰出什麼、誰驗；題目建立後回填 challenge_id。"""

    __tablename__ = "is1ab_assignment"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default="")
    category = db.Column(db.String(32), default="")
    difficulty = db.Column(db.String(32), default="")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_ids = db.Column(db.Text, default="")     # 逗號分隔的 user id
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=True)
    status = db.Column(db.String(32), default="unassigned")


class ChallengeComment(db.Model):
    """題目留言：任何登入者皆可留言（審題 / 討論 / 回饋）。"""

    __tablename__ = "is1ab_comment"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
