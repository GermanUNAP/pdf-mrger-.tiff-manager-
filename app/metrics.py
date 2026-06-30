import time
import hashlib

from flask import request, session as flask_session
from flask_login import current_user
from app.extensions import db
from app.models import UsageLog


def get_session_id():
    if not flask_session:
        return None
    sid = flask_session.sid if hasattr(flask_session, 'sid') else flask_session.get('_sid')
    if not sid:
        sid = flask_session.get('id')
    if not sid:
        return str(id(flask_session))
    return str(sid)


def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def hash_file(file_bytes):
    if not file_bytes:
        return None
    return hashlib.sha256(file_bytes).hexdigest()[:16]


def log_usage(action, file_size=None, pages_in=None, pages_out=None,
              success=True, error_message=None, error_type=None,
              duration_ms=None, endpoint=None, http_method=None,
              status_code=None, file_size_out=None,
              file_hash_in=None, file_hash_out=None,
              original_filename=None, compression_ratio=None):
    request._user_tracked = True
    try:
        log = UsageLog(
            session_id=flask_session.get('_permanent') and get_session_id(),
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            endpoint=endpoint or request.endpoint,
            http_method=http_method or request.method,
            status_code=status_code,
            duration_ms=duration_ms,
            file_size_in=file_size,
            file_size_out=file_size_out,
            file_hash_in=file_hash_in,
            file_hash_out=file_hash_out,
            original_filename=original_filename[:250] if original_filename else None,
            pages_in=pages_in,
            pages_out=pages_out,
            compression_ratio=compression_ratio,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:500],
            referrer=request.headers.get('Referer', '')[:500],
            language=request.headers.get('Accept-Language', '')[:20],
            success=success,
            error_message=str(error_message)[:500] if error_message else None,
            error_type=error_type,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


class RequestTimer:
    def __init__(self):
        self.start = None

    def begin(self):
        self.start = time.perf_counter()

    def end(self):
        if self.start is None:
            return 0
        return int((time.perf_counter() - self.start) * 1000)


def init_middleware(app):

    @app.before_request
    def before_request_log():
        request._timer = RequestTimer()
        request._timer.begin()
        request._user_tracked = False

    @app.after_request
    def after_request_log(response):
        timer = getattr(request, '_timer', None)
        duration = timer.end() if timer else 0
        user_tracked = getattr(request, '_user_tracked', False)

        endpoint = request.endpoint or 'unknown'
        is_static = endpoint == 'static'

        if is_static or endpoint is None:
            return response

        if not user_tracked and not endpoint.startswith('admin.') and not endpoint.startswith('auth.'):
            action = f'page_view:{endpoint}'
            if endpoint and 'page_count' in endpoint:
                action = 'api:page_count'
            elif endpoint and 'download' in endpoint:
                action = 'api:download'

            log_usage(
                action=action,
                endpoint=endpoint,
                http_method=request.method,
                status_code=response.status_code,
                duration_ms=duration,
                file_size_out=response.headers.get('Content-Length', type=int),
            )

        if current_user.is_authenticated:
            try:
                from app.models import User
                user = db.session.get(User, current_user.id)
                if user:
                    from datetime import datetime, timezone
                    user.last_seen = datetime.now(timezone.utc)
                    db.session.commit()
            except Exception:
                db.session.rollback()

        response.headers.add('X-Request-Duration-Ms', str(duration))
        return response
