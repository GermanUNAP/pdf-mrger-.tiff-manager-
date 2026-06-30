from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session

db = SQLAlchemy()
sess = Session()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
