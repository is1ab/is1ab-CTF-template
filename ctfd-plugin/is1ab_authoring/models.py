"""is1ab_authoring 的 DB models（從 __init__.py 抽出，拆檔第二步）。

只依賴 CTFd 的共享 db；被 __init__.py import 後即註冊到 metadata（db.create_all 會建表）。
四張表：challenge metadata / 配額 / 出題工單 / 留言。
"""

from __future__ import annotations

from datetime import datetime
import uuid

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
    """Authorized challenge participants share review/discussion feedback."""

    __tablename__ = "is1ab_comment"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class AuthoringMember(db.Model):
    """Platform identity and explicitly granted roles; GitHub is not required."""
    __tablename__ = "is1ab_authoring_member"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    person_id = db.Column(db.String(36), unique=True, nullable=False,
                          default=lambda: str(uuid.uuid4()))
    roles = db.Column(db.Text, nullable=False, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class AssignmentPlan(db.Model):
    """Additive extension of Assignment; existing challenge tables need no ALTER."""
    __tablename__ = "is1ab_assignment_plan"
    assignment_id = db.Column(db.Integer, db.ForeignKey("is1ab_assignment.id"), primary_key=True)
    goal = db.Column(db.Text, nullable=False, default="")
    resources = db.Column(db.Text, nullable=False, default="")
    decision = db.Column(db.String(32), nullable=False, default="draft")
    decision_reason = db.Column(db.Text, nullable=False, default="")
    due_date = db.Column(db.Date, nullable=True)
    estimated_hours = db.Column(db.Float, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class AssignmentAcceptance(db.Model):
    __tablename__ = "is1ab_assignment_acceptance"
    assignment_id = db.Column(db.Integer, db.ForeignKey("is1ab_assignment.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role = db.Column(db.String(16), primary_key=True)
    status = db.Column(db.String(16), nullable=False, default="pending")
    reason = db.Column(db.Text, nullable=False, default="")
    accepted_at = db.Column(db.DateTime, nullable=True)


class AuthoringEvent(db.Model):
    __tablename__ = "is1ab_authoring_event"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("is1ab_assignment.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ChallengeContributor(db.Model):
    """Keep authorship even after an owner/collaborator is removed."""
    __tablename__ = "is1ab_challenge_contributor"
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)


class ChallengeDraftVersion(db.Model):
    """Optimistic editing version without altering the existing metadata table."""
    __tablename__ = "is1ab_challenge_draft_version"
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class ReviewRound(db.Model):
    """Frozen public draft for editorial review; never a release attestation."""
    __tablename__ = 'is1ab_review_round'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('is1ab_assignment.id'), nullable=False)
    assignment_version = db.Column(db.Integer, nullable=False)
    source_version = db.Column(db.Integer, nullable=False)
    draft_version = db.Column(db.Integer, nullable=False)
    public_json = db.Column(db.Text, nullable=False)
    private_fingerprint = db.Column(db.String(64), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version}
    __table_args__ = (db.UniqueConstraint('challenge_id', 'source_version', name='uq_review_source_version'),)


class ReviewIssue(db.Model):
    __tablename__ = 'is1ab_review_issue'
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('is1ab_review_round.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    origin_issue_id = db.Column(db.Integer, db.ForeignKey('is1ab_review_issue.id'), nullable=True)
    response = db.Column(db.Text, nullable=False, default='')
    state = db.Column(db.String(16), nullable=False, default='open')
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ReviewFeedback(db.Model):
    __tablename__ = 'is1ab_review_feedback'
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('is1ab_review_round.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    detail = db.Column(db.Text, nullable=False)
    editorial_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
