from flask import Blueprint, redirect, url_for

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/', defaults={'path': ''})
@bp.route('/<path:path>')
def not_available(path):
    return redirect(url_for('index'))
