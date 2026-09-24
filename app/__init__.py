import os
import sys
import traceback
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

    if sys.platform == 'win32':
        import tempfile
        upload_folder = tempfile.mkdtemp(prefix='pdfmerger_')
    else:
        upload_folder = '/tmp/pdfmerger'
    app.config['UPLOAD_FOLDER'] = upload_folder

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder, exist_ok=True)

    from app.routes import init_routes
    init_routes(app)

    from app.metrics import init_middleware
    init_middleware(app)

    return app


try:
    app = create_app()
except Exception as e:
    print(f"CREATE_APP FAILED: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise
