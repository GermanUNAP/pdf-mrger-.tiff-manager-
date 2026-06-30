import os
import tempfile
from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app():
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    app.config.from_object('app.config.Config')

    upload_folder = tempfile.mkdtemp(prefix='pdfmerger_')
    app.config['UPLOAD_FOLDER'] = upload_folder

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    from app.extensions import db, sess, login_manager, oauth
    db.init_app(app)
    app.config['SESSION_SQLALCHEMY'] = db
    sess.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    if app.config.get('GOOGLE_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    if app.config.get('GITHUB_CLIENT_ID'):
        oauth.register(
            name='github',
            client_id=app.config['GITHUB_CLIENT_ID'],
            client_secret=app.config['GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    with app.app_context():
        from app.models import User, UsageLog
        db.create_all()

    from app.routes import init_routes
    init_routes(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.services import init_cleanup
    init_cleanup(app)

    from app.metrics import init_middleware
    init_middleware(app)

    return app
