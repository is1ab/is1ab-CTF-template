"""Role and per-challenge access used by both new and legacy authoring routes."""
from functools import wraps

from flask import abort
from CTFd.models import Users, db
from CTFd.utils.user import get_current_user, is_admin

from .models import (Assignment, AssignmentAcceptance, AuthoringMember,
                     ChallengeContributor, ChallengeDraftVersion)

ROLE_LABELS = {
    "pm": "PM", "judge": "裁判", "author": "出題", "reviewer": "驗題",
    "ops": "維運", "support": "選手支援",
}


def ids(value):
    return {int(x) for x in (value or "").split(",") if x.strip().isdigit()}


def roles_for(user):
    if not user:
        return set()
    if user.type == "admin":
        return set(ROLE_LABELS)
    member = AuthoringMember.query.filter_by(user_id=user.id).first()
    return set((member.roles or "").split(",")) & set(ROLE_LABELS) if member and member.active else set()


def has_role(*roles):
    return bool(roles_for(get_current_user()) & set(roles))


def require_roles(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not has_role(*roles):
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def contributors(meta):
    if not meta:
        return set()
    current = ids(meta.collaborators)
    if meta.owner_id:
        current.add(meta.owner_id)
    return current | {r.user_id for r in ChallengeContributor.query.filter_by(
        challenge_id=meta.challenge_id).all()}


def remember_contributors(meta):
    for uid in contributors(meta):
        if Users.query.filter_by(id=uid).first() and not ChallengeContributor.query.filter_by(
                challenge_id=meta.challenge_id, user_id=uid).first():
            db.session.add(ChallengeContributor(challenge_id=meta.challenge_id, user_id=uid))


def assignment_for(challenge_id):
    # Never infer identity from author/category/difficulty.
    rows = Assignment.query.filter_by(challenge_id=challenge_id).all()
    return rows[0] if len(rows) == 1 else None


def can_edit(meta):
    if is_admin():
        return True
    user = get_current_user()
    return bool(user and meta and has_role("author") and (
        user.id == meta.owner_id or user.id in ids(meta.collaborators)))


def can_review(meta):
    user = get_current_user()
    if not user or not meta or not has_role("reviewer") or user.id in contributors(meta):
        return False
    assignment = assignment_for(meta.challenge_id)
    if not assignment or user.id not in ids(assignment.reviewer_ids):
        return False
    if AssignmentAcceptance.query.filter_by(assignment_id=assignment.id, user_id=user.id, role="author").first():
        return False
    return AssignmentAcceptance.query.filter_by(
        assignment_id=assignment.id, user_id=user.id, role="reviewer", status="accepted").first() is not None


def can_view(meta):
    if can_edit(meta) or has_role("pm", "judge"):
        return True
    return can_review(meta)


def eligible_users(role):
    return [u for u in Users.query.order_by(Users.name).all() if role in roles_for(u)]


def draft_version(challenge_id):
    row = ChallengeDraftVersion.query.filter_by(challenge_id=challenge_id).first()
    if row is None:
        row = ChallengeDraftVersion(challenge_id=challenge_id)
        db.session.add(row)
        db.session.flush()
    return row
