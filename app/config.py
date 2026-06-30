import os
from datetime import timedelta


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def resolve_database_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        if 'sslmode=require' not in url and 'localhost' not in url and 'postgres:' not in url:
            suffix = '&' if '?' in url else '?'
            url += suffix + 'sslmode=require'
        return url
    return f'sqlite:///{os.path.join(basedir, "data.db")}'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = resolve_database_url()

    SESSION_TYPE = 'sqlalchemy'
    SESSION_SQLALCHEMY_TABLE = 'sessions'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'pdfm:'
