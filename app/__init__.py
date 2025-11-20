import os
import logging
import time
import secrets
from datetime import datetime
from flask import Flask, jsonify, session, abort, request, g, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# =============================
# Extensions
# =============================
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'يجب عليك تسجيل الدخول أولاً.'

# CSRF Protect
try:
    from flask_wtf import CSRFProtect
    csrf = CSRFProtect()
except ImportError:
    csrf = None

# Caching
try:
    from flask_caching import Cache
    cache = Cache()
    CACHE_AVAILABLE = True
except ImportError:
    cache = None
    CACHE_AVAILABLE = False

# Sentry
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# Optional libs
try:
    import flask_limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    flask_limiter = None
    get_remote_address = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import celery
except ImportError:
    celery = None

# Werkzeug secure_filename
try:
    from werkzeug.utils import secure_filename
except ImportError:
    secure_filename = None

# =============================
# Factory
# =============================
def create_app(test_config=None):
    os.environ.setdefault('FLASK_ENV', 'development')
    app = Flask(__name__)

    # Load config
    from app.config import Config
    app.config.from_object(Config)
    if test_config:
        if isinstance(test_config, dict):
            app.config.update(test_config)
        elif isinstance(test_config, str):
            from app.config import config_by_name
            cfg = config_by_name.get(test_config)
            if cfg:
                app.config.from_object(cfg)
            else:
                raise ValueError(f"Unknown config name: {test_config}")

    print(">>> DB PATH:", app.config["SQLALCHEMY_DATABASE_URI"])

    # UPLOAD_FOLDER absolute path
    upload_folder = os.path.abspath(os.path.join(os.getcwd(), app.config.get('UPLOAD_FOLDER', 'uploads')))
    app.config['UPLOAD_FOLDER'] = upload_folder

    # Check SECRET_KEY
    if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        if app.config.get('ENV') == 'production':
            raise ValueError('❌ SECRET_KEY يجب أن يكون قوياً في الإنتاج')
        app.logger.warning('⚠️  استخدام SECRET_KEY ضعيف (بيئة تطوير فقط)')

    # =============================
    # Initialize extensions
    # =============================
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    if csrf:
        try:
            # csrf.init_app(app)  # Enable if needed
            app.logger.info('⏸️  CSRFProtect disabled for stateless API')
        except Exception as e:
            app.logger.debug(f'CSRF initialization failed: {e}')

    # CORS
    CORS(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})

    # Caching
    if CACHE_AVAILABLE:
        cache_config = {
            'CACHE_TYPE': os.getenv('CACHE_TYPE', 'simple'),
            'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'CACHE_DEFAULT_TIMEOUT': 300
        }
        try:
            app.config.from_mapping(cache_config)
            cache.init_app(app)
            app.logger.info('✅ Caching enabled')
        except Exception as e:
            app.logger.warning(f'⚠️  Cache initialization failed: {e}')

    # Sentry
    if SENTRY_AVAILABLE and not app.debug:
        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn:
            try:
                sentry_sdk.init(dsn=sentry_dsn, integrations=[FlaskIntegration()],
                                traces_sample_rate=0.1,
                                environment=app.config.get('ENV', 'development'),
                                debug=False)
                app.logger.info('✅ Sentry monitoring enabled')
            except Exception as e:
                app.logger.warning(f'⚠️  Sentry init failed: {e}')

    # =============================
    # Load User
    # =============================
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # =============================
    # Blueprints
    # =============================
    from app.routes.auth import auth as auth_blueprint
    from app.routes.doctor import doctor as doctor_blueprint
    from app.routes.main import main as main_blueprint
    from app.routes.admin import admin as admin_blueprint

    try:
        from app.routes.analysis import analysis as analysis_blueprint
    except Exception as e:
        app.logger.warning(f'⚠️ Analysis blueprint failed: {e}')
        from flask import Blueprint
        analysis_blueprint = Blueprint('analysis', __name__)

    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    app.register_blueprint(analysis_blueprint, url_prefix='/api')
    app.register_blueprint(doctor_blueprint, url_prefix='/api/doctor')
    app.register_blueprint(admin_blueprint, url_prefix='/api/admin')
    app.register_blueprint(main_blueprint)

    # =============================
    # Ensure upload folders
    # =============================
    required_dirs = [
        upload_folder,
        os.path.join(upload_folder, 'originals'),
        os.path.join(upload_folder, 'saliency_maps'),
        os.path.join(upload_folder, 'temp_saliency')
    ]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        app.logger.info(f'✅ Folder ready: {directory}')

    # =============================
    # Logging
    # =============================
    from app.utils import setup_logging
    setup_logging(app)

    # =============================
    # Middleware
    # =============================
    @app.before_request
    def start_request():
        g.start_time = time.time()
        app.logger.debug(f'REQUEST START: {request.method} {request.path} - IP {request.remote_addr}')

        # CSRF token
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)

        # Skip CSRF for safe endpoints
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            safe_endpoints = ['/health', '/health/ready', '/api/analyze', '/api/analyze_and_save', '/login', '/register', '/api/log_client_error']
            if request.path in safe_endpoints:
                return
            session_token = session.get('csrf_token')
            csrf_token = request.headers.get('X-CSRF-Token') or request.headers.get('XSRF-TOKEN') or request.cookies.get('XSRF-TOKEN') or request.form.get('csrf_token')
            if not session_token or not csrf_token or csrf_token != session_token:
                app.logger.warning(f'CSRF failed: {request.method} {request.path}')
                abort(403)

    @app.after_request
    def after_request(response):
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https://images.unsplash.com; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "worker-src 'self' blob:; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Set XSRF cookie
        xsrf = session.get('csrf_token')
        if xsrf:
            response.set_cookie('XSRF-TOKEN', xsrf, httponly=False,
                                samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax'),
                                secure=app.config.get('SESSION_COOKIE_SECURE', False),
                                domain=app.config.get('SESSION_COOKIE_DOMAIN'))

        # Log response
        duration = time.time() - g.get('start_time', 0)
        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        app.logger.log(level, f'RESPONSE: {request.method} {request.path} - Status {response.status_code} - Duration {duration:.3f}s')

        return response

    # =============================
    # Context processors
    # =============================
    @app.context_processor
    def inject_config():
        return {'app_name': 'PneumoDetect', 'app_version': '1.0.0'}

    @app.context_processor
    def inject_csrf_token():
        return {'csrf_token': lambda: session.get('csrf_token', '')}

    # =============================
    # Health checks
    # =============================
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'version': '1.0.0', 'environment': app.config.get('ENV', 'unknown')}), 200

    @app.route('/health/ready', methods=['GET'])
    def readiness_check():
        checks = {}
        status_code = 200
        # Database
        try:
            db.session.execute('SELECT 1')
            checks['database'] = '✓ OK'
        except Exception as e:
            app.logger.error(f'DB check failed: {e}')
            checks['database'] = f'✗ FAILED: {str(e)[:50]}'
            status_code = 503
        # Cache
        if CACHE_AVAILABLE and cache:
            try:
                cache.get('test_key')
                checks['cache'] = '✓ OK'
            except Exception as e:
                app.logger.warning(f'Cache check failed: {e}')
                checks['cache'] = f'⚠️ WARN: {str(e)[:50]}'
        else:
            checks['cache'] = 'ℹ️ Not configured'
        # Sentry
        checks['sentry'] = '✓ OK' if SENTRY_AVAILABLE and not app.debug else 'ℹ️ Disabled'

        return jsonify({'status': 'ready' if status_code == 200 else 'not_ready',
                        'timestamp': datetime.utcnow().isoformat(),
                        'checks': checks}), status_code

    # =============================
    # System info
    # =============================
    @app.route('/api/system-info', methods=['GET'])
    @login_required
    def system_info():
        if not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        import sys
        return jsonify({
            'python_version': sys.version,
            'environment': app.config.get('ENV', 'unknown'),
            'debug_mode': app.debug,
            'database': app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0],
            'upload_folder': app.config['UPLOAD_FOLDER']
        }), 200

    return app

