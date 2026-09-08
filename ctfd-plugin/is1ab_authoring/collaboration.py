"""Staff roster and proposal/assignment workflow for the staging authoring site.

This does not approve artifacts or deploy challenges. Proposal acceptance and
human task acceptance are deliberately separate from release verification.
"""
import json
import math
from datetime import date, datetime

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)
from sqlalchemy import Index
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from CTFd.models import Challenges, Users, db
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user, is_admin

from . import access
from .config import categories, difficulties
from .models import (Assignment, AssignmentAcceptance, AssignmentPlan,
                     AuthoringEvent, AuthoringMember, ChallengeMetadata)

bp = Blueprint("is1ab_collaboration", __name__, template_folder="templates", url_prefix="/is1ab")
DECISIONS = {"draft": "草稿", "submitted": "待確認提案", "changes_requested": "提案需補充",
             "approved": "可開始製作", "standby": "備用", "withdrawn": "本場不採用"}
ACCEPTANCE_LABELS = {"pending": "待接案", "accepted": "已接案", "declined": "退回協調", "removed": "已交接"}
link_index = Index("uq_is1ab_assignment_challenge", Assignment.challenge_id, unique=True)


def _integer(value, label):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
        return number
    except (ValueError, TypeError):
        raise ValueError(label + "無效，請重新選擇。")


def _text(name, limit, required=False):
    value = request.form.get(name, "").strip()
    if required and not value:
        raise ValueError("請填寫" + {"title": "提案名稱", "goal": "考點與目標", "reason": "原因"}.get(name, name) + "。")
    if len(value) > limit:
        raise ValueError("內容超過長度限制，請縮短後再送出。")
    return value


def _schedule():
    raw = request.form.get("due_date", "").strip()
    try:
        due = date.fromisoformat(raw) if raw else None
    except ValueError:
        raise ValueError("截止日期格式應為 YYYY-MM-DD。")
    raw = request.form.get("estimated_hours", "").strip()
    try:
        hours = float(raw) if raw else None
        if hours is not None and (not math.isfinite(hours) or not 0 <= hours <= 10000):
            raise ValueError
    except ValueError:
        raise ValueError("預估工時須為 0 至 10000 的有限數字。")
    return due, hours


def _event(action, assignment=None, **detail):
    db.session.add(AuthoringEvent(actor_id=get_current_user().id,
                                 assignment_id=assignment.id if assignment else None,
                                 action=action, detail=json.dumps(detail, ensure_ascii=False)))


def plan_for(assignment):
    plan = AssignmentPlan.query.filter_by(assignment_id=assignment.id).first()
    if plan is None:
        plan = AssignmentPlan(assignment_id=assignment.id)
        db.session.add(plan)
        db.session.flush()
    return plan


def author_ids(assignment):
    result = {p.user_id for p in AssignmentAcceptance.query.filter_by(
        assignment_id=assignment.id, role="author").all()}
    if assignment.author_id:
        result.add(assignment.author_id)
    if assignment.challenge_id:
        result |= access.contributors(ChallengeMetadata.query.filter_by(
            challenge_id=assignment.challenge_id).first())
    return result


def _participants(assignment):
    return AssignmentAcceptance.query.filter_by(assignment_id=assignment.id).all()


def _sync_participants(assignment):
    desired = {(u, "reviewer") for u in access.ids(assignment.reviewer_ids)}
    if assignment.author_id:
        desired.add((assignment.author_id, "author"))
    existing = {(p.user_id, p.role): p for p in _participants(assignment)}
    for key, participant in existing.items():
        if key not in desired:
            participant.status = "removed"
        elif participant.status == "removed":
            participant.status, participant.reason, participant.accepted_at = "pending", "", None
    for uid, role in desired - set(existing):
        db.session.add(AssignmentAcceptance(assignment_id=assignment.id, user_id=uid, role=role))


def _eligible(uid, role):
    user = Users.query.filter_by(id=uid).first()
    if not user or role not in access.roles_for(user):
        raise ValueError("選定成員未啟用或沒有相應角色，請由管理員確認名單。")
    return user


def _assignees(assignment=None):
    uid = _integer(request.form.get("author_id"), "出題人")
    _eligible(uid, "author")
    reviewers = {_integer(x, "驗題人") for x in request.form.getlist("reviewers")}
    excluded = author_ids(assignment) if assignment else set()
    excluded.add(uid)
    if reviewers & excluded:
        raise ValueError("驗題人不能是本題目前或曾經的作者／共同作者。")
    for rid in reviewers:
        _eligible(rid, "reviewer")
    if assignment and assignment.challenge_id:
        meta = ChallengeMetadata.query.filter_by(challenge_id=assignment.challenge_id).first()
        if not meta or uid != meta.owner_id:
            raise ValueError("已建立題目的作者須與題目擁有者一致；請先完成題目交接。")
    return uid, ",".join(str(x) for x in sorted(reviewers))


def _can_read(assignment):
    user = get_current_user()
    return access.has_role("pm", "judge") or (user and (
        assignment.author_id == user.id and access.has_role("author") or
        user.id in access.ids(assignment.reviewer_ids) and access.has_role("reviewer")))


def _render(template, **kwargs):
    return render_template("is1ab_collaboration/" + template, nonce=session.get("nonce", ""),
                           role_labels=access.ROLE_LABELS, decisions=DECISIONS,
                           acceptance_labels=ACCEPTANCE_LABELS,
                           event_labels={"proposal.created": "建立提案", "assignment.proposal": "更新並送出提案",
                               "assignment.assign": "更新指派與時程", "assignment.accept": "更新接案回覆",
                               "assignment.decision": "確認提案決定", "assignment.link": "連結題目"},
                           event_detail=lambda event: json.loads(event.detail or "{}"),
                           can_manage=access.has_role("pm", "judge"),
                           is_pm=access.has_role("pm"), is_judge=access.has_role("judge"),
                           is_author=access.has_role("author"), admin=is_admin(),
                           viewer=get_current_user(), **kwargs)


@bp.route("/members", methods=["GET", "POST"])
@admins_only
def members():
    error, status = None, 200
    if request.method == "POST":
        try:
            uid = _integer(request.form.get("user_id"), "成員")
            user = Users.query.filter_by(id=uid).first_or_404()
            if user.type == "admin":
                raise ValueError("管理員身分由 CTFd 帳號管理；此頁僅授予一般成員的工作角色。")
            roles = set(request.form.getlist("roles"))
            if not roles <= set(access.ROLE_LABELS):
                raise ValueError("角色清單包含未知值。")
            member = AuthoringMember.query.filter_by(user_id=uid).first()
            if request.form.get("version") != str(member.version if member else 0):
                raise StaleDataError()
            if member is None:
                member = AuthoringMember(user_id=uid)
                db.session.add(member)
            previous_roles = set((member.roles or "").split(",")) if member.active else set()
            member.roles = ",".join(sorted(roles))
            member.active = request.form.get("active") == "on"
            removed_roles = previous_roles - (roles if member.active else set())
            for person in AssignmentAcceptance.query.filter_by(user_id=uid).all():
                if person.role in removed_roles and person.status != "removed":
                    person.status, person.accepted_at = "pending", None
                    changed = plan_for(Assignment.query.get(person.assignment_id))
                    changed.updated_at = datetime.utcnow()
                    if changed.decision == "approved":
                        changed.decision, changed.decision_reason = "submitted", "成員角色已撤銷，請重新協調指派。"
            _event("member.updated", user_id=uid, roles=sorted(roles), active=member.active)
            db.session.commit()
            flash("已儲存成員角色；同一帳號可兼任多項工作。", "success")
            return redirect(url_for("is1ab_collaboration.members"))
        except ValueError as exc:
            db.session.rollback()
            error, status = str(exc), 400
        except (StaleDataError, IntegrityError):
            db.session.rollback()
            error, status = "成員已被其他人更新，請核對目前設定後再儲存。", 409
    return _render("members.html", users=Users.query.order_by(Users.name).all(),
                   members={m.user_id: m for m in AuthoringMember.query.all()}, error=error), status


@bp.route("/work")
@authed_only
@access.require_roles(*access.ROLE_LABELS)
def work():
    from .review import summary as review_summary
    rows = []
    for assignment in Assignment.query.order_by(Assignment.id.desc()).all():
        if _can_read(assignment):
            plan = plan_for(assignment)
            rows.append({"a": assignment, "p": plan, "review_summary": review_summary(assignment.challenge_id), "participants": _participants(assignment),
                         "overdue": bool(plan.due_date and plan.due_date < date.today() and
                                         plan.decision not in ("standby", "withdrawn"))})
    db.session.commit()
    return _render("work.html", rows=rows, names={u.id: u.name for u in Users.query.all()})


@bp.route("/work/new", methods=["GET", "POST"])
@authed_only
@access.require_roles("author", "pm")
def new():
    error = None
    if request.method == "POST":
        try:
            title, goal, resources = _text("title", 255, True), _text("goal", 4000, True), _text("resources", 4000)
            category, difficulty = request.form.get("category"), request.form.get("difficulty")
            if category not in categories() or difficulty not in difficulties():
                raise ValueError("請選擇有效分類與難度。")
            due, hours = _schedule()
            uid, reviewers = _assignees() if access.has_role("pm") else (get_current_user().id, "")
            assignment = Assignment(title=title, category=category, difficulty=difficulty,
                                    author_id=uid, reviewer_ids=reviewers, status="assigned")
            db.session.add(assignment)
            db.session.flush()
            db.session.add(AssignmentPlan(assignment_id=assignment.id, goal=goal, resources=resources,
                                           due_date=due, estimated_hours=hours))
            _sync_participants(assignment)
            _event("proposal.created", assignment, author_id=uid, reviewer_ids=reviewers)
            db.session.commit()
            return redirect(url_for("is1ab_collaboration.detail", assignment_id=assignment.id))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    return _render("new.html", authors=access.eligible_users("author"),
                   reviewers=access.eligible_users("reviewer"), categories=categories(),
                   difficulties=difficulties(), error=error), 400 if error else 200


def _act(assignment, plan):
    actor = get_current_user()
    action = request.form.get("action")
    if action == "proposal":
        if actor.id != assignment.author_id or not access.has_role("author"):
            abort(403)
        assignment.title = _text("title", 255, True)
        plan.goal, plan.resources = _text("goal", 4000, True), _text("resources", 4000)
        plan.decision, plan.decision_reason = "submitted", ""
    elif action == "assign":
        if not access.has_role("pm"):
            abort(403)
        previous = assignment.author_id, assignment.reviewer_ids, plan.due_date, plan.estimated_hours
        assignment.author_id, assignment.reviewer_ids = _assignees(assignment)
        plan.due_date, plan.estimated_hours = _schedule()
        _sync_participants(assignment)
        if previous != (assignment.author_id, assignment.reviewer_ids, plan.due_date, plan.estimated_hours):
            for person in _participants(assignment):
                if person.status != "removed":
                    person.status, person.accepted_at = "pending", None
            if plan.decision == "approved":
                plan.decision, plan.decision_reason = "submitted", "人員或時程已變更，請重新接案並確認提案。"
    elif action == "accept":
        role, status = request.form.get("role"), request.form.get("status")
        if role not in ("author", "reviewer") or status not in ("accepted", "declined"):
            raise ValueError("接案選項無效。")
        participant = AssignmentAcceptance.query.filter_by(
            assignment_id=assignment.id, user_id=actor.id, role=role).first()
        if not participant or participant.status == "removed" or not access.has_role(role):
            abort(403)
        if role == "reviewer" and actor.id in author_ids(assignment):
            abort(403)
        if plan.decision == "withdrawn":
            raise ValueError("本場不採用的提案需先由裁判恢復。")
        participant.reason = _text("reason", 2000, required=status == "declined")
        participant.status = status
        participant.accepted_at = datetime.utcnow() if status == "accepted" else None
    elif action == "decision":
        if not access.has_role("judge") or actor.id in author_ids(assignment):
            abort(403)
        decision = request.form.get("decision")
        if decision not in ("approved", "changes_requested", "standby", "withdrawn"):
            raise ValueError("提案決定無效。")
        reason = _text("reason", 2000, True)
        if decision == "approved":
            if plan.decision not in ("submitted", "standby", "withdrawn"):
                raise ValueError("請先由作者送出提案。")
            if not plan.goal or not assignment.reviewer_ids:
                raise ValueError("請補齊考點與獨立驗題指派。")
            for participant in _participants(assignment):
                if participant.status != "removed":
                    _eligible(participant.user_id, participant.role)
                    if participant.status != "accepted":
                        raise ValueError("請等待作者與驗題人接案。")
            if access.ids(assignment.reviewer_ids) & author_ids(assignment):
                raise ValueError("驗題人與作者歷史重疊，請 PM 重新指派。")
        plan.decision, plan.decision_reason = decision, reason
    elif action == "link":
        if not access.has_role("pm"):
            abort(403)
        if assignment.challenge_id:
            raise ValueError("工單已有題目，不能改綁另一題。")
        cid = _integer(request.form.get("challenge_id"), "題目")
        meta = ChallengeMetadata.query.filter_by(challenge_id=cid).first()
        if not meta or meta.owner_id != assignment.author_id:
            raise ValueError("題目不存在或作者與工單不同。")
        if Assignment.query.filter_by(challenge_id=cid).first():
            raise ValueError("此題已連到另一工單。")
        if access.ids(assignment.reviewer_ids) & access.contributors(meta):
            raise ValueError("本題共同作者不能被指派驗題。")
        access.remember_contributors(meta)
        assignment.challenge_id = cid
    else:
        raise ValueError("未知操作。")
    plan.updated_at = datetime.utcnow()  # Forces the version check for every mutation.
    _event("assignment." + action, assignment, version=plan.version,
           author_id=assignment.author_id, reviewer_ids=assignment.reviewer_ids,
           decision=plan.decision, status=request.form.get("status"),
           due_date=str(plan.due_date or ""), estimated_hours=plan.estimated_hours,
           reason=request.form.get("reason", "")[:2000])


@bp.route("/work/<int:assignment_id>", methods=["GET", "POST"])
@authed_only
def detail(assignment_id):
    from .review import summary as review_summary
    assignment = Assignment.query.filter_by(id=assignment_id).first_or_404()
    if not _can_read(assignment):
        abort(403)
    plan = plan_for(assignment)
    db.session.commit()
    error, code = None, 200
    if request.method == "POST":
        try:
            if request.form.get("version") != str(plan.version):
                raise StaleDataError()
            _act(assignment, plan)
            db.session.commit()
            flash("已儲存。提案確認與接案不代表題目已通過正式驗證。", "success")
            return redirect(url_for("is1ab_collaboration.detail", assignment_id=assignment.id))
        except ValueError as exc:
            db.session.rollback()
            error, code = str(exc), 400
        except (StaleDataError, IntegrityError):
            db.session.rollback()
            error, code = "內容已更新或題目已被其他工單連結。你的輸入已保留，請核對最新資料後再送出。", 409
    return _render("detail.html", a=assignment, p=plan, error=error, review_summary=review_summary(assignment.challenge_id),
                   participants=_participants(assignment), authors=access.eligible_users("author"),
                   reviewers=access.eligible_users("reviewer"),
                   names={u.id: u.name for u in Users.query.all()}, author_ids=author_ids(assignment),
                   can_view_challenge=access.can_view(ChallengeMetadata.query.filter_by(challenge_id=assignment.challenge_id).first()) if assignment.challenge_id else False,
                   events=AuthoringEvent.query.filter_by(assignment_id=assignment.id).order_by(
                       AuthoringEvent.id.desc()).limit(30).all()), code


def initialize(app):
    app.register_blueprint(bp)
    with app.app_context():
        migrate_existing()


def migrate_existing():
    duplicates = db.session.query(Assignment.challenge_id).filter(
        Assignment.challenge_id.isnot(None)).group_by(Assignment.challenge_id).having(db.func.count() > 1).all()
    if duplicates:
        raise RuntimeError("is1ab 工單有重複 challenge_id，請先人工確認明確連結；不自動覆寫：" +
                           ", ".join(str(row[0]) for row in duplicates))
    db.create_all()
    link_index.create(bind=db.engine, checkfirst=True)
    for assignment in Assignment.query.all():
        plan_for(assignment)
        _sync_participants(assignment)
    for meta in ChallengeMetadata.query.all():
        access.remember_contributors(meta)
        access.draft_version(meta.challenge_id)
    db.session.commit()


def creation_assignment():
    raw = request.form.get("assignment_id") if request.method == "POST" else request.args.get("assignment_id")
    if not raw:
        return None
    try:
        aid = _integer(raw, "工單")
    except ValueError as exc:
        abort(400, description=str(exc))
    assignment = Assignment.query.filter_by(id=aid).first_or_404()
    if assignment.author_id != get_current_user().id or not access.has_role("author"):
        abort(403)
    if assignment.challenge_id:
        return assignment  # Retry returns the existing challenge, never a duplicate.
    plan = plan_for(assignment)
    if plan.decision != "approved":
        abort(409, description="請先完成提案確認與接案，再依工單建立題目。")
    for participant in _participants(assignment):
        if participant.status != "removed":
            try:
                _eligible(participant.user_id, participant.role)
            except ValueError as exc:
                abort(409, description=str(exc))
            if participant.status != "accepted":
                abort(409, description="請等待作者與驗題人接案。")
    if request.method == "POST" and request.form.get("assignment_version") != str(plan.version):
        abort(409, description="工單已更新，請重新開啟建立題目表單。")
    return assignment


def bind_created_challenge(assignment, challenge_id):
    if assignment:
        assignment.challenge_id = challenge_id
        plan_for(assignment).updated_at = datetime.utcnow()
        _event("assignment.link", assignment, challenge_id=challenge_id)
