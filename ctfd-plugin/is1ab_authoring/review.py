"""Version-bound editorial review. No artifact, solve, or release approval is issued here."""
import hashlib
import hmac
import json
import os

from flask import Blueprint, abort, current_app, flash, redirect, request, url_for
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from CTFd.models import Challenges, Flags, Hints, Tags, Users, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

from . import access
from .models import AssignmentPlan, ChallengeMetadata, ReviewRound, ReviewIssue, ReviewFeedback

bp = Blueprint('is1ab_review', __name__, template_folder='templates', url_prefix='/is1ab')


def _document(challenge, meta):
    # Deliberately allowlist player-facing draft fields. Never copy blob/source/flags into the view.
    return dict(name=challenge.name, category=challenge.category, description=challenge.description,
                value=challenge.value, tags=[r.value for r in Tags.query.filter_by(challenge_id=challenge.id).order_by(Tags.id)],
                hints=[dict(cost=h.cost, content=h.content) for h in Hints.query.filter_by(
                    challenge_id=challenge.id).order_by(Hints.id)])


def _fingerprint(challenge, meta):
    # Private changes must invalidate the review too; a keyed digest avoids exposing a flag oracle.
    data = dict(public=_document(challenge, meta), metadata=meta.blob, owner=meta.owner_id,
                collaborators=meta.collaborators, flags=[(f.type, f.content, f.data) for f in
                    Flags.query.filter_by(challenge_id=challenge.id).order_by(Flags.id)])
    key = current_app.config.get('IS1AB_REVIEW_FINGERPRINT_KEY') or os.environ.get('IS1AB_REVIEW_FINGERPRINT_KEY')
    if not key or len(key) < 32:
        raise ValueError('送審服務尚未完成設定，請維運配置獨立的審閱指紋金鑰（至少 32 字元）。')
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, json.dumps(data, sort_keys=True, ensure_ascii=False).encode(), hashlib.sha256).hexdigest()


def _assignment(meta):
    a = access.assignment_for(meta.challenge_id)
    p = AssignmentPlan.query.get(a.id) if a else None
    return a, p


def _current(round_, meta):
    a, p = _assignment(meta)
    chal = Challenges.query.get(meta.challenge_id)
    try:
        fingerprint = _fingerprint(chal, meta)
    except ValueError:
        return False
    return bool(a and p and p.decision == 'approved' and a.id == round_.assignment_id and
                p.version == round_.assignment_version and access.draft_version(meta.challenge_id).version == round_.draft_version and
                hmac.compare_digest(round_.private_fingerprint, fingerprint))


def _text(name, required=True):
    value = request.form.get(name, '').strip()
    if required and not value:
        raise ValueError('請填寫具體說明。')
    if len(value) > 4000:
        raise ValueError('說明最多 4000 字，請縮短後重送。')
    return value


def _record(action, round_, **details):
    from .collaboration import _event
    _event('review.' + action, access.assignment_for(round_.challenge_id), round_id=round_.id, **details)


def _lock_scope(challenge_id, draft_version, assignment_id, assignment_version):
    # A no-op conditional update takes the row lock without changing the version.
    # Editor/assignment writes use these same rows, so they cannot race a review decision.
    from .models import ChallengeDraftVersion
    if ChallengeDraftVersion.query.filter_by(challenge_id=challenge_id, version=draft_version).update(
            {ChallengeDraftVersion.version: ChallengeDraftVersion.version}, synchronize_session=False) != 1:
        raise StaleDataError()
    if AssignmentPlan.query.filter_by(assignment_id=assignment_id, version=assignment_version).update(
            {AssignmentPlan.version: AssignmentPlan.version}, synchronize_session=False) != 1:
        raise StaleDataError()


def _qualified(meta):
    from .collaboration import _participants, _eligible, author_ids
    a, p = _assignment(meta)
    if not a or not p or p.decision != 'approved':
        raise ValueError('請先完成工單連結、接案與裁判提案確認。')
    reviewers = access.ids(a.reviewer_ids)
    if not reviewers or reviewers & author_ids(a):
        raise ValueError('請 PM 安排未參與本題製作的驗題人。')
    people = _participants(a)
    wanted = {(a.author_id, 'author')} | {(uid, 'reviewer') for uid in reviewers}
    accepted = {(p.user_id, p.role) for p in people if p.status == 'accepted'}
    if not wanted <= accepted:
        raise ValueError('請先由作者與所有驗題人接案。')
    for uid, role in wanted:
        _eligible(uid, role)
    return a, p


def _render(template, **kw):
    from .collaboration import _render as render_work
    return render_work(template, **kw)


@bp.route('/challenges/<int:challenge_id>/reviews', methods=['GET', 'POST'])
@authed_only
def rounds(challenge_id):
    chal = Challenges.query.filter_by(id=challenge_id).first_or_404()
    meta = ChallengeMetadata.query.filter_by(challenge_id=challenge_id).first_or_404()
    if not access.can_view(meta):
        abort(403)
    revision = access.draft_version(challenge_id)
    db.session.commit()
    error, code = None, 200
    # Primary author submits; collaborators can edit and respond, but cannot silently submit for them.
    can_submit = get_current_user().id == meta.owner_id and access.has_role('author')
    if request.method == 'POST':
        if not can_submit:
            abort(403)
        try:
            a, p = _qualified(meta)
            raw = request.form.get('draft_version', '')
            if not raw.isdigit():
                raise ValueError('草稿版本無效，請重新開啟送審頁。')
            existing = ReviewRound.query.filter_by(challenge_id=challenge_id, source_version=int(raw)).first()
            if existing and _current(existing, meta):
                return redirect(url_for('is1ab_review.detail', round_id=existing.id))
            latest = ReviewRound.query.filter_by(challenge_id=challenge_id).order_by(ReviewRound.id.desc()).first()
            if latest and _current(latest, meta) and int(raw) == revision.version:
                return redirect(url_for('is1ab_review.detail', round_id=latest.id))
            if int(raw) != revision.version or request.form.get('assignment_version') != str(p.version):
                raise StaleDataError()
            if not chal.name or not (chal.description or '').strip():
                raise ValueError('請先填妥題名與題目描述。')
            _lock_scope(challenge_id, revision.version, a.id, p.version)
            source = revision.version
            revision.version += 1  # CAS and transaction serialize submission against editor saves.
            db.session.flush()
            row = ReviewRound(challenge_id=challenge_id, assignment_id=a.id, assignment_version=p.version,
                              source_version=source, draft_version=revision.version, created_by=get_current_user().id,
                              public_json=json.dumps(_document(chal, meta), ensure_ascii=False),
                              private_fingerprint=_fingerprint(chal, meta))
            db.session.add(row)
            db.session.flush()
            if latest:
                for issue in ReviewIssue.query.filter_by(round_id=latest.id, state='open').all():
                    db.session.add(ReviewIssue(round_id=row.id, created_by=issue.created_by,
                        origin_issue_id=issue.origin_issue_id or issue.id, body=issue.body, response=issue.response))
            _record('submitted', row, draft_version=row.draft_version)
            db.session.commit()
            return redirect(url_for('is1ab_review.detail', round_id=row.id))
        except ValueError as exc:
            db.session.rollback()
            error, code = str(exc), 400
        except (StaleDataError, IntegrityError):
            db.session.rollback()
            error, code = '題目或工單已更新。請核對最新資料後重新送審。', 409
    a, p = _assignment(meta)
    history = ReviewRound.query.filter_by(challenge_id=challenge_id).order_by(ReviewRound.id.desc()).all()
    return _render('review_rounds.html', challenge=chal, revision=revision, plan=p, error=error,
                   can_submit=can_submit, rounds=[dict(row=r, current=_current(r, meta)) for r in history]), code


def _act(row, meta):
    reviewer, editor = access.can_review(meta), access.can_edit(meta)
    action = request.form.get('action')
    if action == 'resolve' and request.form.get('action_override') == 'reopen':
        action = 'reopen'
    if action == 'issue':
        if not reviewer:
            abort(403)
        db.session.add(ReviewIssue(round_id=row.id, created_by=get_current_user().id, body=_text('body')))
    elif action in ('respond', 'resolve', 'reopen'):
        issue = ReviewIssue.query.filter_by(id=request.form.get('issue_id'), round_id=row.id).first()
        if not issue:
            abort(404)
        if action == 'respond':
            if not editor:
                abort(403)
            issue.response = _text('body')
            issue.state, issue.resolved_by = 'open', None
        else:
            if not reviewer:
                abort(403)
            # Closing a report requires an explanation, not an author's self-reported fix.
            note = _text('body')
            issue.state = 'resolved' if action == 'resolve' else 'open'
            issue.resolved_by = get_current_user().id if action == 'resolve' else None
            db.session.add(ReviewFeedback(round_id=row.id, reviewer_id=get_current_user().id,
                                          detail=f'問題 #{issue.id}：{note}', editorial_confirmed=False))
    elif action == 'feedback':
        if not reviewer:
            abort(403)
        body = _text('body')
        confirmed = request.form.get('confirm') == 'on'
        if confirmed and ReviewIssue.query.filter_by(round_id=row.id, state='open').first():
            raise ValueError('還有未結問題，請先處理或留下回饋。')
        db.session.add(ReviewFeedback(round_id=row.id, reviewer_id=get_current_user().id,
                                      detail=body, editorial_confirmed=confirmed))
    else:
        raise ValueError('未知操作。')
    row.version += 1  # All feedback and issue transitions serialize on the same review round.
    _record(action, row, issue_id=request.form.get('issue_id'), body=request.form.get('body', '')[:4000])


@bp.route('/reviews/<int:round_id>', methods=['GET', 'POST'])
@authed_only
def detail(round_id):
    row = ReviewRound.query.filter_by(id=round_id).first_or_404()
    meta = ChallengeMetadata.query.filter_by(challenge_id=row.challenge_id).first_or_404()
    if not access.can_view(meta):
        abort(403)
    current = _current(row, meta)
    error, code = None, 200
    if request.method == 'POST':
        try:
            if not current or request.form.get('version') != str(row.version):
                raise StaleDataError()
            _lock_scope(row.challenge_id, row.draft_version, row.assignment_id, row.assignment_version)
            _qualified(meta)
            _act(row, meta)
            db.session.commit()
            flash('已記錄此版題面回饋；尚未取得正式試解或發布資格。', 'success')
            return redirect(url_for('is1ab_review.detail', round_id=row.id))
        except ValueError as exc:
            db.session.rollback()
            error, code = str(exc), 400
        except (StaleDataError, IntegrityError):
            db.session.rollback()
            error, code = '題目、指派或審閱紀錄已更新。輸入已保留，請核對後再送出；舊版不能核准新版。', 409
    current, issues, feedback, confirmed = _state(row, meta)
    return _render('review_detail.html', r=row, doc=json.loads(row.public_json), current=current,
                   issues=issues, feedback=feedback, confirmed=confirmed, error=error,
                   reviewer=access.can_review(meta), editor=access.can_edit(meta),
                   names={u.id:u.name for u in Users.query.all()}), code


def initialize(app):
    app.register_blueprint(bp)


def _state(row, meta):
    current = _current(row, meta)
    issues = ReviewIssue.query.filter_by(round_id=row.id).order_by(ReviewIssue.id).all()
    feedback = ReviewFeedback.query.filter_by(round_id=row.id).order_by(ReviewFeedback.id.desc()).all()
    # Confirmation is derived from the latest feedback, current scope, and open blockers.
    # A newly reported issue invalidates all earlier confirmations, even after it is closed.
    last_issue = max((i.created_at for i in issues), default=None)
    latest = feedback[0] if feedback else None
    confirmed = bool(current and latest and latest.editorial_confirmed and not any(i.state == 'open' for i in issues)
                     and (last_issue is None or latest.created_at > last_issue))
    return current, issues, feedback, confirmed


def summary(challenge_id):
    if not challenge_id:
        return "尚未建立題目"
    meta = ChallengeMetadata.query.filter_by(challenge_id=challenge_id).first()
    row = ReviewRound.query.filter_by(challenge_id=challenge_id).order_by(ReviewRound.id.desc()).first()
    if not meta or not row:
        return "草稿，待作者送出題面審閱"
    current, issues, feedback, confirmed = _state(row, meta)
    if not current:
        return "草稿或指派已更新，待作者重新送審"
    if any(i.state == "open" for i in issues):
        return "有未結問題，待作者回覆／驗題人確認"
    return "題面已確認，待技術驗證" if confirmed else "待指定驗題人審閱題面"
