import hashlib
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    oauth_provider = db.Column(db.String(30), nullable=True)
    oauth_id = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_bot = db.Column(db.Boolean, default=False)
    consent_given = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.Index('idx_user_oauth', 'oauth_provider', 'oauth_id', unique=True),
    )

    usage_logs = db.relationship('UsageLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class UsageLog(db.Model):
    __tablename__ = 'usage_logs'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(64), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    endpoint = db.Column(db.String(120), nullable=True)
    http_method = db.Column(db.String(10), nullable=True)
    status_code = db.Column(db.SmallInteger, nullable=True)
    action = db.Column(db.String(50), nullable=False, index=True)

    duration_ms = db.Column(db.Integer, nullable=True)
    processing_time = db.Column(db.Float, nullable=True)

    file_size_in = db.Column(db.BigInteger, nullable=True)
    file_size_out = db.Column(db.BigInteger, nullable=True)
    file_hash_in = db.Column(db.String(64), nullable=True)
    file_hash_out = db.Column(db.String(64), nullable=True)
    original_filename = db.Column(db.String(256), nullable=True)

    pages_in = db.Column(db.Integer, nullable=True)
    pages_out = db.Column(db.Integer, nullable=True)
    compression_ratio = db.Column(db.Float, nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    referrer = db.Column(db.String(512), nullable=True)
    country_hint = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    error_type = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.Index('idx_usage_logs_created_action', 'created_at', 'action'),
        db.Index('idx_usage_logs_user_date', 'user_id', 'created_at'),
        db.Index('idx_usage_logs_session_date', 'session_id', 'created_at'),
    )

    def to_dict(self, anonymize=False):
        d = {
            'id': self.id,
            'action': self.action,
            'endpoint': self.endpoint,
            'duration_ms': self.duration_ms,
            'pages_in': self.pages_in,
            'pages_out': self.pages_out,
            'file_size_in': self.file_size_in,
            'file_size_out': self.file_size_out,
            'compression_ratio': self.compression_ratio,
            'status_code': self.status_code,
            'success': self.success,
            'created_at': self.created_at.isoformat(),
        }
        if not anonymize:
            d.update({
                'user_id': self.user_id,
                'session_id': self.session_id,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'original_filename': self.original_filename,
            })
        else:
            d['country_hint'] = self.country_hint
            d['language'] = self.language
        return d

    def __repr__(self):
        return f'<UsageLog {self.action} #{self.id}>'
