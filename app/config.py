import os
from datetime import timedelta


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _resolve_database_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        url = url.replace('postgres://', 'postgresql://', 1)
        needs_ssl = 'sslmode=require' not in url
        needs_ssl = needs_ssl and 'localhost' not in url
        needs_ssl = needs_ssl and not url.startswith('postgresql://postgres:')
        if needs_ssl:
            url += ('&' if '?' in url else '?') + 'sslmode=require'
        return url
    return f'sqlite:///{os.path.join(basedir, "data.db")}'


def _session_lifetime():
    days = int(os.environ.get('SESSION_LIFETIME_DAYS', 30))
    return timedelta(days=days)


def _max_content_length():
    raw = os.environ.get('MAX_CONTENT_LENGTH')
    if raw:
        return int(raw)
    return 500 * 1024 * 1024


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = _max_content_length()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _resolve_database_url()

    SESSION_TYPE = 'sqlalchemy'
    SESSION_SQLALCHEMY_TABLE = 'sessions'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = _session_lifetime()
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'pdfm:'

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
    OAUTH_REDIRECT_URI = os.environ.get('OAUTH_REDIRECT_URI', 'http://127.0.0.1:5050')
