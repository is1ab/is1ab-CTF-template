"""Disposable browser QA only. Requires an explicitly isolated SQLite database."""
import os
if os.environ.get('IS1AB_LOCAL_PREVIEW') != '1' or os.environ.get('DATABASE_URL') != 'sqlite:////tmp/authoring-test.db':
    raise SystemExit('Preview requires the disposable authoring test container.')
from CTFd import create_app
from CTFd.models import Users, db
from CTFd.utils import set_config
from CTFd.plugins.is1ab_authoring.models import AuthoringMember
app = create_app()
app.config["IS1AB_REVIEW_FINGERPRINT_KEY"] = "local-preview-fingerprint-only-000000000000"
with app.app_context():
    for key, value in dict(setup=True, is1ab_onboarded=True, ctf_name='出題協作 · 本機測試',
                           user_mode='users', registration_visibility='private').items():
        set_config(key, value)
    for name, role in [('admin',''), ('pm','pm'), ('author','author,reviewer'),
                        ('reviewer','author,reviewer'), ('judge','judge'), ('player','')]:
        if not Users.query.filter_by(name=name).first():
            user = Users(name=name, email=name+'@example.test', password='local-test-password',
                         type='admin' if name=='admin' else 'user', verified=True)
            db.session.add(user); db.session.flush()
            if role:
                db.session.add(AuthoringMember(user_id=user.id,roles=role))
    db.session.commit()
app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
