import time

from flask import request


def log_usage(action, **kwargs):
    pass


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

    @app.after_request
    def after_request_log(response):
        timer = getattr(request, '_timer', None)
        duration = timer.end() if timer else 0
        response.headers.add('X-Request-Duration-Ms', str(duration))
        return response
