import csv
import io
import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, Response, jsonify, request as flask_request
from flask_login import login_required, current_user
from sqlalchemy import func, text

from app.extensions import db
from app.models import User, UsageLog

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@login_required
def dashboard():
    if not current_user.is_admin:
        return render_template('admin/dashboard.html', admin=False)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = User.query.count()
    total_ops = UsageLog.query.count()
    today_ops = UsageLog.query.filter(UsageLog.created_at >= today_start).count()
    week_ops = UsageLog.query.filter(UsageLog.created_at >= week_ago).count()
    month_ops = UsageLog.query.filter(UsageLog.created_at >= month_ago).count()
    anon_ops = UsageLog.query.filter(UsageLog.user_id.is_(None)).count()

    avg_duration = (
        db.session.query(func.avg(UsageLog.duration_ms))
        .filter(UsageLog.duration_ms.isnot(None))
        .scalar()
    ) or 0

    total_with_errors = UsageLog.query.filter(UsageLog.success.is_(False)).count()
    error_rate = (total_with_errors * 100.0 / total_ops) if total_ops > 0 else 0

    by_action = (
        db.session.query(UsageLog.action, func.count(UsageLog.id))
        .group_by(UsageLog.action)
        .order_by(func.count(UsageLog.id).desc())
        .all()
    )

    top_users = (
        db.session.query(
            User.username, func.count(UsageLog.id).label('count')
        )
        .join(UsageLog, UsageLog.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(func.count(UsageLog.id).desc())
        .limit(10)
        .all()
    )

    recent_logs = (
        UsageLog.query
        .order_by(UsageLog.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        admin=True,
        total_users=total_users,
        total_ops=total_ops,
        today_ops=today_ops,
        week_ops=week_ops,
        month_ops=month_ops,
        anon_ops=anon_ops,
        avg_duration=int(avg_duration),
        error_rate=round(error_rate, 2),
        by_action=by_action,
        top_users=top_users,
        recent_logs=recent_logs,
    )


@bp.route('/export')
@login_required
def export_page():
    return render_template('admin/export.html', admin=current_user.is_admin)


@bp.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    if not current_user.is_admin:
        return jsonify({'error': 'Acceso restringido'}), 403

    if flask_request.method == 'POST':
        user_id = flask_request.form.get('user_id', type=int)
        consent_val = flask_request.form.get('consent_given') == '1'
        if user_id:
            user = db.session.get(User, user_id)
            if user:
                user.consent_given = consent_val
                db.session.commit()
                return jsonify({'success': True, 'user_id': user_id, 'consent_given': consent_val})
        return jsonify({'error': 'Usuario no encontrado'}), 404

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/consent.html', admin=True, users=users)


@bp.route('/research/stats')
@login_required
def research_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Acceso restringido'}), 403

    total = UsageLog.query.count()
    unique_sessions = (
        db.session.query(UsageLog.session_id)
        .filter(UsageLog.session_id.isnot(None))
        .distinct().count()
    )
    unique_ips = (
        db.session.query(UsageLog.ip_address)
        .filter(UsageLog.ip_address.isnot(None))
        .distinct().count()
    )

    action_counts = {
        row.action: row[1]
        for row in db.session.query(UsageLog.action, func.count(UsageLog.id))
        .group_by(UsageLog.action)
        .order_by(func.count(UsageLog.id).desc())
        .all()
    }

    daily = [
        {'date': row[0].strftime('%Y-%m-%d'), 'count': row[1]}
        for row in db.session.query(
            func.date(UsageLog.created_at), func.count(UsageLog.id)
        )
        .group_by(func.date(UsageLog.created_at))
        .order_by(func.date(UsageLog.created_at).desc())
        .limit(90)
        .all()
    ]

    duration_avg = (
        db.session.query(func.avg(UsageLog.duration_ms))
        .filter(UsageLog.duration_ms.isnot(None)).scalar()
    ) or 0
    duration_min = (
        db.session.query(func.min(UsageLog.duration_ms))
        .filter(UsageLog.duration_ms.isnot(None)).scalar()
    ) or 0
    duration_max = (
        db.session.query(func.max(UsageLog.duration_ms))
        .filter(UsageLog.duration_ms.isnot(None)).scalar()
    ) or 0
    all_durations = [
        r[0] for r in db.session.query(UsageLog.duration_ms)
        .filter(UsageLog.duration_ms.isnot(None))
        .order_by(UsageLog.duration_ms)
        .all()
    ]
    duration_median = all_durations[len(all_durations) // 2] if all_durations else 0

    compression_data = [
        {'pages_in': r.pages_in, 'pages_out': r.pages_out,
         'ratio': r.compression_ratio, 'duration': r.duration_ms}
        for r in UsageLog.query
        .filter(UsageLog.action == 'compress_pdfs')
        .filter(UsageLog.pages_in.isnot(None))
        .order_by(UsageLog.created_at.desc())
        .limit(500)
        .all()
    ]

    file_sizes = [
        {'in': r.file_size_in, 'out': r.file_size_out, 'action': r.action}
        for r in UsageLog.query
        .filter(UsageLog.file_size_in.isnot(None))
        .order_by(UsageLog.created_at.desc())
        .limit(1000)
        .all()
    ]

    return jsonify({
        'total_operations': total,
        'unique_sessions': unique_sessions,
        'unique_ips': unique_ips,
        'action_distribution': action_counts,
        'daily_activity': daily,
        'duration_ms': {
            'avg': round(duration_avg, 2),
            'median': round(duration_median, 2),
            'min': duration_min,
            'max': duration_max,
        },
        'compression_data': compression_data,
        'file_sizes': file_sizes,
    })


@bp.route('/research/export')
@login_required
def research_export():
    if not current_user.is_admin:
        return jsonify({'error': 'Acceso restringido'}), 403

    fmt = flask_request.args.get('format', 'json')
    anonymize = flask_request.args.get('anonymize', '1') == '1'
    limit = min(int(flask_request.args.get('limit', 5000)), 50000)
    offset = int(flask_request.args.get('offset', 0))

    query = UsageLog.query.order_by(UsageLog.created_at.desc()).limit(limit).offset(offset)
    logs = query.all()

    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            'id', 'action', 'endpoint', 'http_method', 'status_code',
            'duration_ms', 'file_size_in', 'file_size_out',
            'pages_in', 'pages_out', 'compression_ratio',
            'success', 'error_type', 'created_at'
        ]
        if not anonymize:
            headers += ['user_id', 'session_id', 'ip_address', 'original_filename']
        writer.writerow(headers)

        for log in logs:
            row = [
                log.id, log.action, log.endpoint, log.http_method, log.status_code,
                log.duration_ms, log.file_size_in, log.file_size_out,
                log.pages_in, log.pages_out, log.compression_ratio,
                log.success, log.error_type,
                log.created_at.isoformat() if log.created_at else ''
            ]
            if not anonymize:
                row += [log.user_id, log.session_id, log.ip_address, log.original_filename]
            writer.writerow(row)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=research_data.csv'}
        )

    data = [log.to_dict(anonymize=anonymize) for log in logs]
    return jsonify({
        'total': len(data),
        'offset': offset,
        'limit': limit,
        'anonymized': anonymize,
        'data': data,
    })
