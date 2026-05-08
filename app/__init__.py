from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Nginx arkasında HTTPS ve IP bilgilerini doğru almak için
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config['SESSION_COOKIE_DOMAIN'] = '.yigitgulyurt.net.tr'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.routes.views import main_bp, og_bp, projects_bp, blog_bp, contact_bp, admin_bp
    from app.routes.stream import bp as stream_bp
    from app.routes.obsidian import bp as obsidian_bp
    from app.routes.fonts import bp as fonts_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projeler')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(contact_bp, url_prefix='/iletisim')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(og_bp)
    app.register_blueprint(stream_bp)  # subdomain='canli' blueprint'te tanımlı
    app.register_blueprint(obsidian_bp, subdomain='obsidian')
    app.register_blueprint(fonts_bp, subdomain='fonts')

    register_context_processors(app)

    return app

from app import models  # noqa


from datetime import datetime

def register_context_processors(app):
    @app.context_processor
    def inject_globals():
        from flask import current_app
        return {
            'now': datetime.utcnow(),
            'config': current_app.config,
        }
