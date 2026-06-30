from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app()

GET_ROUTES = [
    '/', '/find', '/merge-multiple', '/compress', '/convert',
    '/crop', '/remove-pages', '/reorder',
    '/auth/login', '/auth/register',
    '/admin/', '/admin/export', '/admin/consent',
    '/static/style.css',
]

with app.test_client() as c:
    print('GET routes:')
    for route in GET_ROUTES:
        r = c.get(route)
        ok = 'OK' if r.status_code == 200 else 'UNEXPECTED'
        print(f'  {ok:10} {r.status_code} {route}')

    # POST routes (can't test fully without form data, just check they exist)
    POST_ROUTES = ['/merge', '/merge-multi', '/page-count', '/convert-tiff',
                   '/crop-pdf', '/remove-pages-pdf', '/reorder-pdf', '/compress-pdfs']
    print('POST routes (expected 400/415 without data, not 404):')
    for route in POST_ROUTES:
        r = c.post(route)
        ok = 'EXISTS' if r.status_code != 404 else 'NOT FOUND'
        print(f'  {ok:10} {r.status_code} {route}')

    # Admin redirect when not logged in
    from flask import url_for
    with app.test_request_context():
        admin_url = url_for('admin.dashboard')
    r = c.get(admin_url, follow_redirects=False)
    print(f'  {"REDIRECTS":10} {r.status_code} {admin_url} (expected 302 to login)')

    print()
    print('ALL ROUTES CHECKED')
