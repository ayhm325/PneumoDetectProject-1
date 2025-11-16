import os
import logging
import time
from flask import Flask, jsonify, session, abort, request, url_for, g
import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from flask_wtf import CSRFProtect

# تحميل متغيرات البيئة
load_dotenv()

# كائنات التوسيع (Extensions)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Redis Caching
try:
    from flask_caching import Cache
    cache = Cache()
    CACHE_AVAILABLE = True
except ImportError:
    cache = None
    CACHE_AVAILABLE = False

# Sentry للمراقبة
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# إعدادات Flask-Login
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'يجب عليك تسجيل الدخول أولاً.'


def create_app(test_config=None):
    # Do not forcibly overwrite FLASK_ENV; allow tests to provide it.
    os.environ.setdefault('FLASK_ENV', 'development')
    """مصنع التطبيق (App Factory)."""
    app = Flask(__name__)


    # =========================================================
    # 1. الإعدادات
    # =========================================================
    if test_config:
        # First, load the base config so default keys (e.g., LOG_LEVEL)
        # are present even when tests supply a minimal dict.
        from app.config import Config
        app.config.from_object(Config)

        # Support passing either a dict-like config or a config name (e.g. 'testing')
        if isinstance(test_config, dict):
            app.config.update(test_config)
        elif isinstance(test_config, str):
            # Allow tests to pass a config name that maps to a Config class
            from app.config import config_by_name
            cfg = config_by_name.get(test_config)
            if cfg:
                app.config.from_object(cfg)
            else:
                raise ValueError(f"Unknown config name: {test_config}")
        else:
            # Fallback for other mapping-like objects
            app.config.update(test_config)
    else:
        from app.config import Config
        app.config.from_object(Config)

    print(">>> DB PATH:", app.config["SQLALCHEMY_DATABASE_URI"])

    # Ensure UPLOAD_FOLDER is an absolute path (use project cwd)
    try:
        configured = app.config.get('UPLOAD_FOLDER', 'uploads')
        abs_upload = os.path.abspath(os.path.join(os.getcwd(), configured))
        app.config['UPLOAD_FOLDER'] = abs_upload
    except Exception:
        # If anything goes wrong, fall back to the configured value
        app.logger.warning('Could not normalize UPLOAD_FOLDER to absolute path')
    
    # التحقق من الإعدادات الحرجة
    if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        if app.config.get('ENV') == 'production':
            raise ValueError('❌ SECRET_KEY يجب أن يكون قوياً في الإنتاج')
        app.logger.warning('⚠️  استخدام SECRET_KEY ضعيف (بيئة تطوير فقط)')

    # =========================================================
    # 2. تهيئة الإضافات
    # =========================================================
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # Initialize Flask-WTF CSRF protection (optional - will validate forms and headers)
    try:
        csrf.init_app(app)
        app.logger.info('✅ CSRFProtect enabled')
    except Exception:
        app.logger.debug('CSRFProtect could not be initialized')
    
    # تفعيل CORS
    CORS(app, resources={
        r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}
    })
    
    # تهيئة Redis Caching
    if CACHE_AVAILABLE:
        cache_config = {
            'CACHE_TYPE': os.getenv('CACHE_TYPE', 'simple'),
            'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'CACHE_DEFAULT_TIMEOUT': 300
        }
        if cache_config['CACHE_TYPE'] == 'redis':
            try:
                app.config.from_mapping(cache_config)
                cache.init_app(app)
                app.logger.info('✅ Redis Caching enabled')
            except Exception as e:
                app.logger.warning(f'⚠️  Redis cache failed, falling back to simple: {e}')
                app.config['CACHE_TYPE'] = 'simple'
                cache.init_app(app)
        else:
            cache.init_app(app)
            app.logger.info('✅ Simple caching enabled (non-Redis)')
    
    # تهيئة Sentry للمراقبة
    if SENTRY_AVAILABLE and not app.debug:
        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn:
            try:
                sentry_sdk.init(
                    dsn=sentry_dsn,
                    integrations=[FlaskIntegration()],
                    traces_sample_rate=0.1,
                    environment=app.config.get('ENV', 'development'),
                    debug=False
                )
                app.logger.info('✅ Sentry monitoring enabled')
            except Exception as e:
                app.logger.warning(f'⚠️  Sentry initialization failed: {e}')
    elif SENTRY_AVAILABLE and app.debug:
        app.logger.info('⚠️  Sentry disabled in debug mode')

    # =========================================================
    # 3. تحميل المستخدم
    # =========================================================
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # =========================================================
    # 4. معالجات الأخطاء
    # =========================================================
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'message': 'طلب غير صحيح',
            'error_code': 'BAD_REQUEST'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'message': 'غير مصرح لك',
            'error_code': 'UNAUTHORIZED'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'message': 'وصول مرفوع',
            'error_code': 'FORBIDDEN'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'المورد غير موجود',
            'error_code': 'NOT_FOUND'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'خطأ في الخادم: {error}')
        return jsonify({
            'success': False,
            'message': 'خطأ في الخادم',
            'error_code': 'INTERNAL_SERVER_ERROR'
        }), 500

    # =========================================================
    # 5. تسجيل Blueprints
    # =========================================================
    from app.routes.auth import auth as auth_blueprint
    
    # Import analysis blueprint (real analysis with ML)
    try:
        from app.routes.analysis import analysis as analysis_blueprint
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        app.logger.error(f'❌ فشل استيراد مسار التحليل: {e}', exc_info=True)
        raise RuntimeError(f'تعذر تحميل واجهات برمجية التحليل: {e}')

    from app.routes.doctor import doctor as doctor_blueprint
    from app.routes.main import main as main_blueprint
    from app.routes.admin import admin as admin_blueprint

    # API blueprints registered under `/api` to match frontend templates
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    app.register_blueprint(analysis_blueprint, url_prefix='/api')
    app.register_blueprint(doctor_blueprint, url_prefix='/api/doctor')
    app.register_blueprint(admin_blueprint, url_prefix='/api/admin')
    # main blueprint serves the frontend pages
    app.register_blueprint(main_blueprint)

    # =========================================================
    # 6. إنشاء مجلد التحميل
    # =========================================================
    upload_folder = app.config['UPLOAD_FOLDER']
    required_dirs = [
        upload_folder,
        os.path.join(upload_folder, 'originals'),
        os.path.join(upload_folder, 'saliency_maps'),
        os.path.join(upload_folder, 'temp_saliency')
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            app.logger.info(f'تم إنشاء المجلد: {directory}')

    # =========================================================
    # 7. إعداد Logging
    # =========================================================
    from app.utils import setup_logging
    setup_logging(app)

    # =========================================================
    # 8. Middleware للأمان والـ Logging
    # =========================================================
    @app.before_request
    def log_request_start():
        """تسجيل بداية الطلب."""
        g.start_time = time.time()
        app.logger.debug(
            f'REQUEST: {request.method} {request.path} - '
            f'IP: {request.remote_addr} - '
            f'Content-Type: {request.content_type}'
        )

    @app.before_request
    def set_security_headers():
        """إضافة رؤوس أمان HTTP مهمة."""
        # توليد توكن CSRF للجلسة إذا لم يكن موجودًا
        if 'csrf_token' not in session:
            try:
                session['csrf_token'] = secrets.token_urlsafe(32)
            except Exception:
                session['csrf_token'] = 'dev-csrf-token'

        # لحماية نقاط النهاية التي تسمح بتغيير الحالة، نتحقق من توكن CSRF
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # If Flask-WTF CSRFProtect is active, let it perform validation
            if 'csrf' in app.extensions:
                return
            # استثناء endpoints معينة من التحقق
            safe_endpoints = ['/health', '/health/ready', '/api/analyze', '/api/analyze_and_save']
            if request.path in safe_endpoints:
                return

            session_token = session.get('csrf_token')
            
            # محاولة الحصول على token من مصادر مختلفة
            csrf_token = None
            
            # 1. من X-CSRF-Token header (الطريقة الأفضل لـ JSON APIs)
            csrf_token = request.headers.get('X-CSRF-Token')
            
            # 2. من XSRF-TOKEN header (بديل)
            if not csrf_token:
                csrf_token = request.headers.get('XSRF-TOKEN')
            
            # 3. من XSRF-TOKEN cookie (آخر خيار)
            if not csrf_token:
                csrf_token = request.cookies.get('XSRF-TOKEN')
            
            # 4. من form data (للـ form submissions)
            if not csrf_token and request.form:
                csrf_token = request.form.get('csrf_token')
            
            # التحقق من التوكن
            if not session_token or not csrf_token or csrf_token != session_token:
                app.logger.warning(f'CSRF token validation failed for {request.method} {request.path}')
                abort(403)

    @app.after_request
    def set_security_headers_after(response):
        """إضافة رؤوس أمان HTTP وتسجيل الاستجابة."""
        # منع XSS
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Strict Transport Security (HSTS) - في الإنتاج فقط
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy (مبسطة)
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com"
        
        # تسجيل الاستجابة
        duration = time.time() - g.get('start_time', 0)
        log_level = 'INFO'
        if response.status_code >= 500:
            log_level = 'ERROR'
        elif response.status_code >= 400:
            log_level = 'WARNING'
        
        app.logger.log(
            getattr(logging, log_level),
            f'RESPONSE: {request.method} {request.path} - '
            f'Status: {response.status_code} - '
            f'Duration: {duration:.3f}s - '
            f'Size: {response.content_length or 0} bytes'
        )
        
        # معيار Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # ضع توكن CSRF في كوكي يمكن للـ JavaScript قراءته (غير HttpOnly)
        try:
            xsrf = session.get('csrf_token')
            if xsrf:
                # Secure cookie في الإنتاج
                secure_flag = app.config.get('SESSION_COOKIE_SECURE', False)
                samesite = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
                domain = app.config.get('SESSION_COOKIE_DOMAIN', None)
                response.set_cookie(
                    'XSRF-TOKEN',
                    xsrf,
                    httponly=False,
                    samesite=samesite,
                    secure=secure_flag,
                    domain=domain
                )
        except Exception:
            app.logger.debug('Could not set XSRF-TOKEN cookie')

        return response

    # =========================================================
    # 9. Context Processors
    # =========================================================
    @app.context_processor
    def inject_config():
        return {
            'app_name': 'PneumoDetect',
            'app_version': '1.0.0'
        }

    @app.context_processor
    def inject_csrf_token():
        """Make a `csrf_token()` helper available inside Jinja templates.

        The function returns the session CSRF token so templates that call
        `{{ csrf_token() }}` will work even when we manage CSRF manually.
        """
        def _csrf_token():
            return session.get('csrf_token', '')

        return {'csrf_token': _csrf_token}

    # =========================================================
    # 10. مسار اختبار الصحة (Health Check)
    # =========================================================
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'environment': app.config.get('ENV', 'unknown')
        }), 200

    @app.route('/health/ready', methods=['GET'])
    def readiness_check():
        """Readiness check - التحقق من جاهزية جميع المكونات."""
        from datetime import datetime
        from sqlalchemy import text
        checks = {}
        status_code = 200
        
        # فحص قاعدة البيانات
        try:
            db.session.execute(text('SELECT 1'))
            checks['database'] = '✓ OK'
        except Exception as e:
            app.logger.error(f'Database health check failed: {e}')
            checks['database'] = f'✗ FAILED: {str(e)[:50]}'
            status_code = 503
        
        # فحص Redis (إن وجد)
        if CACHE_AVAILABLE and cache:
            try:
                cache.get('test_key')
                checks['cache'] = '✓ OK'
            except Exception as e:
                logger.warning(f'Cache health check failed: {e}')
                checks['cache'] = f'⚠️ WARN: {str(e)[:50]}'
        else:
            checks['cache'] = 'ℹ️ Not configured'
        
        # فحص Sentry
        if SENTRY_AVAILABLE and not app.debug:
            checks['sentry'] = '✓ OK'
        else:
            checks['sentry'] = 'ℹ️ Disabled'
        
        return jsonify({
            'status': 'ready' if status_code == 200 else 'not_ready',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': checks
        }), status_code

    # =========================================================
    # 11. مسارات معلومات النظام (للمسؤولين فقط)
    # =========================================================
    @app.route('/api/system-info', methods=['GET'])
    @login_required
    def system_info():
        """معلومات النظام (للمدير فقط)."""
        if not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        
        import sys
        import os
        return jsonify({
            'python_version': sys.version,
            'environment': app.config.get('ENV', 'unknown'),
            'debug_mode': app.debug,
            'database': app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0],
            'upload_folder': app.config['UPLOAD_FOLDER']
        }), 200

    return app