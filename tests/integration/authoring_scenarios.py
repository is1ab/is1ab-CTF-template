"""Run with the pinned CTFd container, not the host's lightweight pytest runtime.

python /repo/tests/integration/authoring_scenarios.py
"""
import re
import unittest
from CTFd import create_app
from CTFd.models import Challenges, Users, Flags, db
from CTFd.utils import set_config
from CTFd.utils.security.signing import hmac
from CTFd.plugins.is1ab_authoring import load, _assignment_for, _my_stuff
from CTFd.plugins.is1ab_authoring.models import (
    Assignment, AssignmentPlan, AssignmentAcceptance, AuthoringMember,
    ChallengeMetadata, ChallengeContributor, AuthoringEvent,
)
from CTFd.plugins.is1ab_authoring import collaboration


class AuthoringScenarios(unittest.TestCase):
    def setUp(self):
        self.app = create_app('CTFd.config.TestingConfig')
        self.app.config['IS1AB_REVIEW_FINGERPRINT_KEY'] = 'test-fingerprint-only-000000000000000000000'
        self.ctx = self.app.app_context()
        self.ctx.push()
        load(self.app)
        for k, v in dict(setup=True, is1ab_onboarded=True, ctf_name='出題測試',
                         user_mode='users', challenge_visibility='public',
                         account_visibility='public').items():
            set_config(k, v)
        self.users = {}
        self.clients = {}
        roles = dict(admin=None, pm='pm', author='author,reviewer,judge',
                     reviewer='author,reviewer', judge='judge', ops='ops',
                     support='support', player='', stranger='author,reviewer')
        for name, grants in roles.items():
            user = Users(name=name, email=name+'@example.test', password='local-test-password',
                         type='admin' if name == 'admin' else 'user', verified=True)
            db.session.add(user)
            db.session.flush()
            self.users[name] = user
            if grants:
                db.session.add(AuthoringMember(user_id=user.id, roles=grants))
        db.session.commit()
        for name, user in self.users.items():
            client = self.app.test_client()
            with client.session_transaction() as s:
                s['id'], s['nonce'], s['hash'] = user.id, 'test-nonce', hmac(user.password)
            self.clients[name] = client

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()

    def post(self, who, path, **data):
        data['nonce'] = 'test-nonce'
        return self.clients[who].post(path, data=data)

    def new(self):
        r = self.post('pm', '/is1ab/work/new', title='Web 第一題', category='web', difficulty='easy',
                      goal='測試輸入解析', author_id=self.users['author'].id,
                      reviewers=str(self.users['reviewer'].id), due_date='2026-10-01', estimated_hours='8')
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True))
        return Assignment.query.order_by(Assignment.id.desc()).first()

    def act(self, who, a, action, **data):
        db.session.expire_all()
        data.setdefault('version', str(AssignmentPlan.query.get(a.id).version))
        return self.post(who, '/is1ab/work/'+str(a.id), action=action, **data)

    def ready(self):
        a = self.new()
        for who, role in [('author', 'author'), ('reviewer', 'reviewer')]:
            self.assertEqual(self.act(who, a, 'accept', role=role, status='accepted').status_code, 302)
        self.assertEqual(self.act('author', a, 'proposal', title=a.title, goal='測試解析', resources='').status_code, 302)
        self.assertEqual(self.act('judge', a, 'decision', decision='approved', reason='考點與時程確認').status_code, 302)
        return a

    def challenge(self, a=None):
        c = Challenges(name='秘密草稿', category='web', value=100, state='visible', type='standard', description='公開題敘')
        db.session.add(c); db.session.flush()
        db.session.add(ChallengeMetadata(challenge_id=c.id, owner_id=self.users['author'].id,
                                        blob='internal_notes: private-solution-marker\ndifficulty: easy\n'))
        db.session.add(Flags(challenge_id=c.id, type='static', content='flag{private-marker}'))
        if a:
            a.challenge_id = c.id
        db.session.commit()
        return c

    def test_unregistered_player_cannot_enter_or_mutate_staging(self):
        a = self.new(); c = self.challenge(a)
        for path in ['/is1ab', '/is1ab/work', '/is1ab/new', '/is1ab/import',
                     '/is1ab/work/'+str(a.id), '/is1ab/challenges/'+str(c.id)+'/view',
                     '/challenges', '/api/v1/challenges', '/api/v1/challenges/'+str(c.id), '/files/known/file.txt']:
            self.assertEqual(self.clients['player'].get(path).status_code, 403, path)
        for action in ['comment', 'reviewers', 'review-me', 'review-outcome', 'deploy', 'deploy-down', 'deploy-files']:
            self.assertEqual(self.post('player', f'/is1ab/challenges/{c.id}/{action}', body='unauthorized').status_code, 403)
        self.assertEqual(AuthoringMember.query.filter_by(user_id=self.users['player'].id).count(), 0)

    def test_admin_grants_multiple_roles_and_revocation_is_immediate(self):
        self.assertEqual(self.clients["admin"].get("/is1ab/members").status_code,200)
        uid = self.users['player'].id
        self.assertEqual(self.post('pm', '/is1ab/members', user_id=uid, version='0', roles=['pm']).status_code, 302)
        self.assertEqual(self.post('admin', '/is1ab/members', user_id=uid, version='0', roles=['author','reviewer'], active='on').status_code, 302)
        self.assertEqual(self.clients['player'].get('/is1ab/work/new').status_code, 200)
        m = AuthoringMember.query.get(uid); person_id = m.person_id
        self.assertEqual(self.post('admin', '/is1ab/members', user_id=uid, version=str(m.version), roles=['author']).status_code, 302)
        self.assertEqual(self.clients['player'].get('/is1ab/work').status_code, 403)
        self.assertEqual(AuthoringMember.query.get(uid).person_id, person_id)

    def test_full_proposal_acceptance_and_explicit_creation(self):
        a = self.ready()
        form = self.clients['author'].get('/is1ab/new?assignment_id='+str(a.id))
        self.assertEqual(form.status_code, 200)
        self.assertIn(b'name="assignment_id"', form.data)
        r = self.post('author', '/is1ab/new', assignment_id=a.id,
                      assignment_version=AssignmentPlan.query.get(a.id).version,
                      name=a.title, category='web', difficulty='easy', value=100,
                      description='題敘', flag='flag{only-author}', internal_notes='秘密筆記')
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True))
        db.session.expire_all(); a = Assignment.query.get(a.id)
        self.assertIsNotNone(a.challenge_id)
        self.assertEqual(Challenges.query.get(a.challenge_id).state, 'hidden')
        self.assertEqual(Flags.query.filter_by(challenge_id=a.challenge_id).count(), 1)
        count = Challenges.query.count()
        self.assertEqual(self.post('author', '/is1ab/new', assignment_id=a.id).status_code, 302)
        self.assertEqual(Challenges.query.count(), count)
        self.assertGreater(AuthoringEvent.query.filter_by(assignment_id=a.id).count(), 4)

    def test_pm_can_schedule_but_not_read_secrets_or_edit_challenge(self):
        a = self.ready(); c = self.challenge(a)
        self.assertEqual(self.act('pm', a, 'assign', author_id=a.author_id,
                         reviewers=a.reviewer_ids, due_date='2026-11-03', estimated_hours='6').status_code, 302)
        self.assertEqual(str(AssignmentPlan.query.get(a.id).due_date), '2026-11-03')
        r = self.clients['pm'].get(f'/is1ab/challenges/{c.id}/view')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'private-marker', r.data); self.assertNotIn(b'private-solution-marker', r.data)
        for suffix in ['edit', 'export', 'export/private.yml']:
            self.assertEqual(self.clients['pm'].get(f'/is1ab/challenges/{c.id}/{suffix}').status_code, 403)
        self.assertEqual(self.clients['pm'].get('/admin/users').status_code, 302)

    def test_reviewer_requires_assignment_and_acceptance(self):
        a = self.new(); c = self.challenge(a)
        path = f'/is1ab/challenges/{c.id}/view'
        self.assertEqual(self.clients['reviewer'].get(path).status_code, 403)
        self.assertEqual(self.act('reviewer', a, 'accept', role='reviewer', status='accepted').status_code, 302)
        r = self.clients['reviewer'].get(path)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'private-marker', r.data); self.assertNotIn(b'private-solution-marker', r.data)
        self.assertEqual(self.clients['stranger'].get(path).status_code, 403)
        self.assertEqual(self.post('stranger', f'/is1ab/challenges/{c.id}/review-me').status_code, 403)
        self.assertEqual(self.post('reviewer', f'/is1ab/challenges/{c.id}/review-outcome', outcome='passed').status_code, 409)

    def test_author_cannot_self_judge_or_be_assigned_to_review_own_work(self):
        a = self.new()
        self.assertEqual(self.act('author', a, 'decision', decision='approved', reason='自行通過').status_code, 403)
        r = self.act('pm', a, 'assign', author_id=a.author_id, reviewers=str(a.author_id))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Assignment.query.get(a.id).reviewer_ids, str(self.users['reviewer'].id))

    def test_former_author_and_collaborator_cannot_review(self):
        a = self.new()
        # Reassign the author before a challenge exists; their history is retained.
        self.assertEqual(self.act('pm', a, 'assign', author_id=self.users['stranger'].id,
                                 reviewers=self.users['reviewer'].id).status_code, 302)
        self.assertEqual(self.act('pm', a, 'assign', author_id=self.users['stranger'].id,
                                 reviewers=self.users['author'].id).status_code, 400)
        b = self.new(); c = self.challenge()
        db.session.add(ChallengeContributor(challenge_id=c.id, user_id=self.users['reviewer'].id)); db.session.commit()
        self.assertEqual(self.act('pm', b, 'link', challenge_id=c.id).status_code, 400)
        self.assertIsNone(Assignment.query.get(b.id).challenge_id)

    def test_confirmation_waits_for_all_people(self):
        a = self.new()
        self.act('author', a, 'proposal', title='缺接案', goal='考點', resources='')
        self.assertEqual(self.act('judge', a, 'decision', decision='approved', reason='確認').status_code, 400)
        self.assertEqual(self.clients['author'].get('/is1ab/new?assignment_id='+str(a.id)).status_code, 409)

    def test_stale_update_preserves_input_and_does_not_overwrite(self):
        a = self.new(); old = AssignmentPlan.query.get(a.id).version
        self.act('author', a, 'proposal', title='已更新', goal='新考點', resources='')
        r = self.act('author', a, 'proposal', version=old, title='我尚未送出的內容', goal='本地考點', resources='')
        self.assertEqual(r.status_code, 409)
        self.assertIn('我尚未送出的內容', r.get_data(as_text=True))
        self.assertEqual(Assignment.query.get(a.id).title, '已更新')

    def test_invalid_schedule_is_atomic(self):
        a = self.new(); old = a.author_id
        r = self.act('pm', a, 'assign', author_id=self.users['stranger'].id,
                     reviewers=a.reviewer_ids, due_date='tomorrow', estimated_hours='NaN')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Assignment.query.get(a.id).author_id, old)
        self.assertEqual(str(AssignmentPlan.query.get(a.id).due_date), '2026-10-01')

    def test_same_category_does_not_guess_identity(self):
        a = self.new(); b = self.new(); c = self.challenge()
        self.assertIsNone(_assignment_for(c.id))
        mine, _ = _my_stuff(self.users['author'].id)
        self.assertEqual(sum(not x['built'] for x in mine), 2)
        self.assertEqual(self.act('pm', a, 'link', challenge_id=c.id).status_code, 302)
        self.assertEqual(self.act('pm', b, 'link', challenge_id=c.id).status_code, 400)
        self.assertEqual(_assignment_for(c.id).id, a.id)

    def test_staff_native_bypass_and_legacy_mutations_are_closed(self):
        a = self.ready(); c = self.challenge(a)
        for who in ['author','reviewer','pm','judge','ops','support']:
            for path in ['/api/v1/challenges', '/files/test/answer.txt']:
                self.assertEqual(self.clients[who].get(path).status_code, 403)
        self.assertEqual(self.post('pm','/is1ab/assignments', action='delete', id=a.id).status_code,409)
        self.assertIsNotNone(Assignment.query.get(a.id))
        for who in ['author','reviewer','pm','support']:
            self.assertEqual(self.post(who,f'/is1ab/challenges/{c.id}/deploy').status_code,403)
        self.assertEqual(self.post('ops',f'/is1ab/challenges/{c.id}/deploy').status_code,410)

    def test_empty_and_invalid_forms_render_and_escape(self):
        self.assertEqual(self.clients['support'].get('/is1ab/work').status_code,200)
        r = self.post('author','/is1ab/work/new', title='<script>alert(1)</script>', goal='', category='web', difficulty='easy')
        self.assertEqual(r.status_code,400)
        self.assertIn(b'&lt;script&gt;',r.data); self.assertNotIn(b'<script>alert(1)</script>',r.data)

    def test_collaborative_edit_conflict_keeps_latest_flag_and_text(self):
        c = self.challenge()
        first = self.clients['author'].get(f'/is1ab/challenges/{c.id}/edit')
        version = re.search(rb'name="draft_version" value="(\d+)"', first.data).group(1).decode()
        data = dict(draft_version=version, name='新的題名', description='已儲存內容', category='web',
                    difficulty='easy', value='100', flag='flag{newest}', internal_notes='最新筆記')
        r = self.post('author', f'/is1ab/challenges/{c.id}/edit', **data)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        data.update(name='尚未合併的題名', flag='flag{stale}')
        r = self.post('author', f'/is1ab/challenges/{c.id}/edit', **data)
        self.assertEqual(r.status_code,409)
        self.assertIn('尚未合併的題名',r.get_data(as_text=True))
        self.assertEqual(Challenges.query.get(c.id).name,'新的題名')
        self.assertEqual(Flags.query.filter_by(challenge_id=c.id).first().content,'flag{newest}')

    def test_changed_schedule_requires_new_acceptance(self):
        a = self.ready()
        self.assertEqual(self.act('pm', a, 'assign', author_id=a.author_id, reviewers=a.reviewer_ids,
                                 due_date='2026-12-01', estimated_hours='40').status_code,302)
        self.assertEqual(AssignmentPlan.query.get(a.id).decision,'submitted')
        self.assertEqual(AssignmentAcceptance.query.filter_by(assignment_id=a.id,status='accepted').count(),0)
        self.assertEqual(self.clients['author'].get('/is1ab/new?assignment_id='+str(a.id)).status_code,409)

    def test_revoked_reviewer_cannot_regain_old_acceptance_by_reactivation(self):
        a = self.ready(); c = self.challenge(a)
        uid = self.users['reviewer'].id
        m = AuthoringMember.query.get(uid)
        self.assertEqual(self.post('admin','/is1ab/members',user_id=uid,version=m.version,roles=['author']).status_code,302)
        m = AuthoringMember.query.get(uid)
        self.assertEqual(self.post('admin','/is1ab/members',user_id=uid,version=m.version,roles=['author','reviewer'],active='on').status_code,302)
        self.assertEqual(self.clients['reviewer'].get(f'/is1ab/challenges/{c.id}/view').status_code,403)
        self.assertEqual(AssignmentPlan.query.get(a.id).decision,'submitted')

    def test_unknown_collaborator_is_rejected_without_partial_edit(self):
        c = self.challenge()
        first = self.clients['author'].get(f'/is1ab/challenges/{c.id}/edit')
        version = re.search(rb'name="draft_version" value="(\d+)"', first.data).group(1).decode()
        r = self.post('author',f'/is1ab/challenges/{c.id}/edit',draft_version=version,name='不應儲存',
                      category='web',value=100,collaborators=self.users['player'].id)
        self.assertEqual(r.status_code,400)
        self.assertEqual(Challenges.query.get(c.id).name,'秘密草稿')

    def test_legacy_migration_retains_identity_without_granting_membership(self):
        c = self.challenge()
        a = Assignment(author_id=self.users['author'].id, reviewer_ids=str(self.users['reviewer'].id),
                       challenge_id=c.id, category='web', difficulty='easy')
        db.session.add(a); db.session.commit()
        before = AuthoringMember.query.count()
        collaboration.migrate_existing()
        collaboration.migrate_existing()
        self.assertEqual(Assignment.query.get(a.id).challenge_id,c.id)
        self.assertEqual(AssignmentAcceptance.query.filter_by(assignment_id=a.id).count(),2)
        self.assertEqual(AuthoringMember.query.count(),before)
        self.assertEqual(AssignmentPlan.query.get(a.id).decision,'draft')

    def test_duplicate_legacy_links_fail_migration_without_overwriting(self):
        c = self.challenge()
        collaboration.link_index.drop(bind=db.engine)
        for _ in range(2):
            db.session.add(Assignment(author_id=self.users['author'].id,challenge_id=c.id))
        db.session.commit()
        with self.assertRaisesRegex(RuntimeError,'重複 challenge_id'):
            collaboration.migrate_existing()
        self.assertEqual(Assignment.query.filter_by(challenge_id=c.id).count(),2)

    def test_csrf_is_required_for_role_and_assignment_changes(self):
        before = Assignment.query.count()
        r = self.clients['pm'].post('/is1ab/work/new',data=dict(title='invalid',goal='goal',category='web',difficulty='easy'))
        self.assertEqual(r.status_code,403)
        self.assertEqual(Assignment.query.count(),before)

    def review_round(self):
        from CTFd.plugins.is1ab_authoring.models import ChallengeDraftVersion, ReviewRound
        a = self.ready(); c = self.challenge(a)
        self.clients['author'].get(f'/is1ab/challenges/{c.id}/reviews')
        version = ChallengeDraftVersion.query.get(c.id).version
        r = self.post('author',f'/is1ab/challenges/{c.id}/reviews',draft_version=version,
                      assignment_version=AssignmentPlan.query.get(a.id).version)
        self.assertEqual(r.status_code,302,r.get_data(as_text=True))
        return a,c,ReviewRound.query.order_by(ReviewRound.id.desc()).first()

    def review_act(self,who,row,action,**data):
        db.session.expire_all()
        data.setdefault('version',row.version)
        return self.post(who,f'/is1ab/reviews/{row.id}',action=action,**data)

    def test_review_snapshot_is_private_safe_and_submission_is_idempotent(self):
        from CTFd.plugins.is1ab_authoring.models import ReviewRound
        a,c,row = self.review_round()
        r = self.clients['reviewer'].get(f'/is1ab/reviews/{row.id}')
        self.assertEqual(r.status_code,200)
        self.assertNotIn(b'private-marker',r.data)
        self.assertNotIn(b'private-solution-marker',r.data)
        self.assertNotIn(row.private_fingerprint.encode(),r.data)
        repeat = self.post('author',f'/is1ab/challenges/{c.id}/reviews',draft_version=row.source_version,
                           assignment_version=row.assignment_version)
        self.assertEqual(repeat.status_code,302)
        self.assertEqual(ReviewRound.query.count(),1)
        for who in ['player','stranger']:
            self.assertEqual(self.clients[who].get(f'/is1ab/reviews/{row.id}').status_code,403)
        self.assertEqual(self.post('reviewer',f'/is1ab/challenges/{c.id}/reviews').status_code,403)

    def test_review_requires_independent_reviewer_and_open_issues_block_confirmation(self):
        from CTFd.plugins.is1ab_authoring.models import ReviewIssue
        a,c,row=self.review_round()
        self.assertEqual(self.review_act('author',row,'feedback',body='自審',confirm='on').status_code,403)
        self.assertEqual(self.review_act('pm',row,'feedback',body='PM 趕時間',confirm='on').status_code,403)
        self.assertEqual(self.review_act('reviewer',row,'issue',body='題敘缺少編碼說明').status_code,302)
        issue=ReviewIssue.query.filter_by(round_id=row.id).first()
        self.assertEqual(self.review_act('reviewer',row,'feedback',body='仍有待修正',confirm='on').status_code,400)
        self.assertEqual(self.review_act('author',row,'resolve',issue_id=issue.id,body='作者自稱修好').status_code,403)
        self.assertEqual(self.review_act('author',row,'respond',issue_id=issue.id,body='請看題敘第二句').status_code,302)
        self.assertEqual(self.review_act('reviewer',row,'resolve',issue_id=issue.id,body='已確認說明足夠').status_code,302)
        self.assertEqual(self.review_act('reviewer',row,'feedback',body='題敘與考點明確，難度 easy',confirm='on').status_code,302)
        r=self.clients['reviewer'].get(f'/is1ab/reviews/{row.id}')
        self.assertIn('此版題面已確認',r.get_data(as_text=True))
        self.assertIn('題面已確認，待技術驗證',self.clients['pm'].get('/is1ab/work').get_data(as_text=True))
        self.assertEqual(Challenges.query.get(c.id).state,'visible')  # No release mutation, even on legacy data.
        self.assertEqual(self.review_act('reviewer',row,'reopen',issue_id=issue.id,body='再次發現歧義').status_code,302)
        self.assertNotIn('此版題面已確認',self.clients['reviewer'].get(f'/is1ab/reviews/{row.id}').get_data(as_text=True))

    def test_editing_draft_preserves_snapshot_and_carries_unresolved_issues(self):
        from CTFd.plugins.is1ab_authoring.models import ReviewRound,ReviewIssue,ChallengeDraftVersion
        a,c,row=self.review_round()
        self.review_act('reviewer',row,'issue',body='缺少輸入格式')
        old_doc=row.public_json; old_id=row.id
        edit=self.clients['author'].get(f'/is1ab/challenges/{c.id}/edit')
        version=re.search(rb'name="draft_version" value="(\d+)"',edit.data).group(1).decode()
        self.assertEqual(self.post('author',f'/is1ab/challenges/{c.id}/edit',draft_version=version,
                         name='新版本',description='補充 UTF-8 格式',category='web',value=100,flag='flag{changed}').status_code,200)
        stale=self.review_act('reviewer',row,'feedback',body='未送出的重要回饋',confirm='on')
        self.assertEqual(stale.status_code,409)
        self.assertIn('未送出的重要回饋',stale.get_data(as_text=True))
        self.assertEqual(ReviewRound.query.get(old_id).public_json,old_doc)
        self.assertIn('草稿或指派已更新，待作者重新送審',self.clients['pm'].get('/is1ab/work').get_data(as_text=True))
        self.assertEqual(self.post('author',f'/is1ab/challenges/{c.id}/reviews',
                         draft_version=ChallengeDraftVersion.query.get(c.id).version,
                         assignment_version=AssignmentPlan.query.get(a.id).version).status_code,302)
        new=ReviewRound.query.order_by(ReviewRound.id.desc()).first()
        self.assertNotEqual(new.id,old_id)
        copied=ReviewIssue.query.filter_by(round_id=new.id).first()
        self.assertEqual(copied.body,'缺少輸入格式')
        self.assertEqual(copied.state,'open')
        self.assertIsNotNone(copied.origin_issue_id)
        self.assertNotIn('此版題面已確認',self.clients['reviewer'].get(f'/is1ab/reviews/{new.id}').get_data(as_text=True))

    def test_review_scope_changes_and_out_of_band_private_edits_invalidate(self):
        a,c,row=self.review_round()
        self.review_act('reviewer',row,'feedback',body='題面清楚',confirm='on')
        flag=Flags.query.filter_by(challenge_id=c.id).first();flag.content='flag{admin-change}';db.session.commit()
        self.assertEqual(self.review_act('reviewer',row,'feedback',body='舊版').status_code,409)
        self.assertNotIn('此版題面已確認',self.clients['pm'].get(f'/is1ab/reviews/{row.id}').get_data(as_text=True))
        self.act('pm',a,'assign',author_id=a.author_id,reviewers=a.reviewer_ids,due_date='2027-01-01',estimated_hours=20)
        self.assertEqual(self.clients['reviewer'].get(f'/is1ab/reviews/{row.id}').status_code,403)

    def test_review_stale_feedback_is_not_silently_overwritten(self):
        a,c,row=self.review_round(); version=row.version
        self.review_act('reviewer',row,'issue',body='新的問題')
        r=self.review_act('reviewer',row,'feedback',version=version,body='<script>old-input</script>',confirm='on')
        self.assertEqual(r.status_code,409)
        self.assertIn(b'&lt;script&gt;old-input&lt;/script&gt;',r.data)
        self.assertNotIn(b'<script>old-input</script>',r.data)

    def test_review_cannot_resolve_issue_from_another_round(self):
        from CTFd.plugins.is1ab_authoring.models import ReviewIssue
        a,c,first=self.review_round();self.review_act('reviewer',first,'issue',body='另一題問題')
        issue=ReviewIssue.query.filter_by(round_id=first.id).first()
        b,d,second=self.review_round()
        self.assertEqual(self.review_act('reviewer',second,'resolve',issue_id=issue.id,body='不應跨題').status_code,404)
        self.assertEqual(ReviewIssue.query.get(issue.id).state,'open')

    def test_review_requires_its_own_key_and_rolls_back_incomplete_submission(self):
        from CTFd.plugins.is1ab_authoring.models import ReviewRound,ChallengeDraftVersion
        a=self.ready();c=self.challenge(a)
        self.clients['author'].get(f'/is1ab/challenges/{c.id}/reviews')
        version=ChallengeDraftVersion.query.get(c.id).version
        self.app.config['IS1AB_REVIEW_FINGERPRINT_KEY']=''
        r=self.post('author',f'/is1ab/challenges/{c.id}/reviews',draft_version=version,
                    assignment_version=AssignmentPlan.query.get(a.id).version)
        self.assertEqual(r.status_code,400)
        self.assertEqual(ReviewRound.query.count(),0)
        self.assertEqual(ChallengeDraftVersion.query.get(c.id).version,version)

if __name__ == '__main__':
    unittest.main(verbosity=2)
