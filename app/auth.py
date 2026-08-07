from flask import Blueprint, redirect, url_for

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register')
@bp.route('/login')
@bp.route('/logout')
def not_available():
    return redirect(url_for('index'))
