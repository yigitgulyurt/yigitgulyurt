from flask import Flask, request, g, url_for, redirect, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from config import Config
import os
import secrets
import re

db                       = SQLAlchemy()
migrate                  = Migrate()
login_manager            = LoginManager()
login_manager.login_view = 'admin.login'
login_manager.session_protection = 'strong'
limiter                  = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

def _csrf_serializer(app):
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='csrf-token')

def generate_csrf_token():
    app = g.get('_csrf_app', None)
    if app is None:
        from flask import current_app
        app = current_app
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    s = _csrf_serializer(app)
    return s.dumps(session['_csrf_token'])

def validate_csrf_token(token):
    app = g.get('_csrf_app', None)
    if app is None:
        from flask import current_app
        app = current_app
    if not token or '_csrf_token' not in session:
        return False
    s = _csrf_serializer(app)
    try:
        data = s.loads(token, max_age=app.config.get('WTF_CSRF_TIME_LIMIT', 3600))
    except (BadSignature, SignatureExpired):
        return False
    return secrets.compare_digest(data, session['_csrf_token'])

@limiter.request_filter
def vip_request_filter():
    exempt_prefixes = ['/font/', '/image/', '/canli/', '/obsidian/']
    if any(request.path.startswith(prefix) for prefix in exempt_prefixes):
        return True
    
    ip = request.remote_addr
    if (
        ip in ['127.0.0.1', '::1'] or
        ip.startswith('10.') or 
        (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31) or 
        ip.startswith('192.168.')
    ):
        return True
    
    referer = request.headers.get('Referer', '')
    origin = request.headers.get('Origin', '')
    
    allowed_domains = [
        'https://yigitgulyurt.net.tr',
        'https://www.yigitgulyurt.net.tr',
        'http://yigitgulyurt.net.tr',
        'http://www.yigitgulyurt.net.tr',
        'http://localhost',
        'http://127.0.0.1'
        ]
    
    def is_allowed_domain(url):
        if not url:
            return False
        return any(url.startswith(domain) for domain in allowed_domains)
    
    if is_allowed_domain(referer) or is_allowed_domain(origin):
        return True
    
    return False

def csrf_protect():
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        path = request.path
        exempt_prefixes = ['/tools/ip-log', '/api/', '/canli/', '/obsidian/']
        if any(path.startswith(p) for p in exempt_prefixes):
            return
        if not current_user.is_authenticated:
            return
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(token):
            abort(400, description='Geçersiz CSRF belirteci.')

def security_headers(response):
    csp = (
        "default-src 'self' https://*.yigitgulyurt.net.tr; "
        "script-src 'self' 'unsafe-inline' https://*.yigitgulyurt.net.tr https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://*.yigitgulyurt.net.tr https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://*.yigitgulyurt.net.tr https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "connect-src 'self' https: wss: https://*.yigitgulyurt.net.tr wss://*.yigitgulyurt.net.tr; "
        "media-src 'self' blob: https: https://*.yigitgulyurt.net.tr; "
        "frame-ancestors 'self'; "
        "frame-src https: blob: data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    return response

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)

    from app.routes.views import main_bp, og_bp, projects_bp, blog_bp, contact_bp, admin_bp, tools_bp
    from app.routes.stream import stream_bp
    from app.routes.obsidian import obsidian_bp
    from app.routes.font import font_bp
    from app.routes.image import image_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projeler')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(contact_bp, url_prefix='/iletisim')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(tools_bp, url_prefix='/araclar')
    app.register_blueprint(og_bp)
    app.register_blueprint(stream_bp, url_prefix='/canli')
    app.register_blueprint(obsidian_bp, url_prefix='/obsidian')
    app.register_blueprint(font_bp, url_prefix='/font')
    app.register_blueprint(image_bp, url_prefix='/image')

    app.before_request(csrf_protect)
    app.after_request(security_headers)

    with app.app_context():
        personal_upload_dir = app.config.get('PERSONAL_UPLOAD_FOLDER')
        if personal_upload_dir:
            os.makedirs(personal_upload_dir, exist_ok=True)
        personal_partial_dir = app.config.get('PERSONAL_UPLOAD_PARTIAL_FOLDER')
        if personal_partial_dir:
            os.makedirs(personal_partial_dir, exist_ok=True)

    register_context_processors(app)

    @app.context_processor
    def inject_csrf():
        return {'csrf_token': generate_csrf_token}

    return app

from app import models  # noqa


from datetime import datetime, timezone

def register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.now(timezone.utc),
        }
