from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app.extensions import db, oauth
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


@bp.route('/login/<provider>')
def oauth_login(provider):
    if provider not in ('google', 'github'):
        flash('Proveedor OAuth no soportado', 'error')
        return redirect(url_for('auth.login'))

    client = oauth.create_client(provider)
    if client is None:
        flash(f'Inicio de sesión con {provider} no configurado', 'error')
        return redirect(url_for('auth.login'))

    redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@bp.route('/callback/<provider>')
def oauth_callback(provider):
    if provider not in ('google', 'github'):
        flash('Proveedor OAuth no soportado', 'error')
        return redirect(url_for('auth.login'))

    client = oauth.create_client(provider)
    if client is None:
        flash(f'Proveedor {provider} no configurado', 'error')
        return redirect(url_for('auth.login'))

    try:
        token = client.authorize_access_token()
    except Exception as e:
        flash(f'Error al autenticar con {provider}: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

    if provider == 'google':
        userinfo = token.get('userinfo')
        if not userinfo:
            userinfo = client.parse_id_token(token)
        oauth_id = userinfo.get('sub')
        email = userinfo.get('email', '')
        name = userinfo.get('name') or userinfo.get('given_name', '') or email.split('@')[0]
    elif provider == 'github':
        resp = client.get('user')
        resp.raise_for_status()
        userinfo = resp.json()
        oauth_id = str(userinfo.get('id'))
        email = userinfo.get('email', '')
        if not email:
            emails_resp = client.get('user/emails')
            emails_resp.raise_for_status()
            for e in emails_resp.json():
                if e.get('primary'):
                    email = e.get('email', '')
                    break
            if not email and emails_resp.json():
                email = emails_resp.json()[0].get('email', '')
        name = userinfo.get('login', '') or email.split('@')[0]

    if not email:
        flash(f'No se pudo obtener el email de {provider}', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter(
        (User.oauth_provider == provider) & (User.oauth_id == oauth_id)
    ).first()

    if not user:
        existing = User.query.filter_by(email=email).first()
        if existing:
            existing.oauth_provider = provider
            existing.oauth_id = oauth_id
            user = existing
        else:
            username = name.replace(' ', '_')[:80]
            base = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f'{base}_{counter}'
                counter += 1
            user = User(
                username=username,
                email=email,
                oauth_provider=provider,
                oauth_id=oauth_id,
            )
            db.session.add(user)
        db.session.commit()

    login_user(user)
    flash(f'Bienvenido, {user.username}!', 'success')
    next_page = request.args.get('next')
    return redirect(next_page or url_for('index'))
