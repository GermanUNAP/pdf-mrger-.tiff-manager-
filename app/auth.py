from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not email or not password:
            flash('Todos los campos son obligatorios', 'error')
            return render_template('register.html')

        if password != confirm:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está registrado', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Bienvenido, {user.username}!', 'success')
            return redirect(next_page or url_for('index'))

        flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('index'))
