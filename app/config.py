"""
إعدادات التطبيق (Configuration)
يحتوي على إعدادات البيئات المختلفة (تطوير، اختبار، إنتاج)
"""
import os
from datetime import timedelta


def _env_bool(name, default=False):
    """Helper to parse boolean-like env vars."""
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).lower() in ('1', 'true', 'yes', 'on')

class Config:
    """الإعدادات الأساسية المشتركة."""
    
    # الأمان
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # قاعدة البيانات
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(PROJECT_ROOT, 'instance', 'site.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # الملفات
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'dcm'}  # DICOM للأشعات
    
    # Hugging Face
    HF_TOKEN = os.environ.get('HF_TOKEN')
    MODEL_REPO = os.environ.get('MODEL_REPO') or 'dima806/chest_xray_pneumonia_detection'
    
    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = _env_bool('REMEMBER_COOKIE_SECURE', True)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get('REMEMBER_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_DOMAIN = os.environ.get('REMEMBER_COOKIE_DOMAIN', None)
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    # Allow overriding these via environment for flexible deployments.
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_DOMAIN = os.environ.get('SESSION_COOKIE_DOMAIN', None)  # Allow any host/IP
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Logging
    LOG_FILE = 'app.log'
    LOG_LEVEL = 'INFO'
    
    # CORS
    CORS_ORIGINS = [
        'http://localhost:3000', 
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://127.0.0.1:3000',
        'http://192.168.1.111:5000',
        'http://192.168.1.111:3000'
    ]
    
    # JSON
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    # Flask-WTF CSRF (enabled by default; tests may disable it in TestingConfig)
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير."""
    DEBUG = True
    TESTING = False
    FLASK_ENV = 'development'
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """إعدادات بيئة الاختبار."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج."""
    DEBUG = False
    TESTING = False
    FLASK_ENV = 'production'
    # In production, recommend cookies usable across origins when necessary.
    # Browsers require Secure=True when SAMESITE=None.
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'None')
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', True)
    REMEMBER_COOKIE_SAMESITE = os.environ.get('REMEMBER_COOKIE_SAMESITE', 'None')
    REMEMBER_COOKIE_SECURE = _env_bool('REMEMBER_COOKIE_SECURE', True)


    # يجب تعيين هذا في متغيرات البيئة
   # if not os.environ.get('SECRET_KEY'):
    #    raise ValueError('SECRET_KEY must be set in production')
    
    #if not os.environ.get('DATABASE_URI'):
     #   raise ValueError('DATABASE_URI must be set in production')


# تحديد الإعداد الحالي بناءً على متغير البيئة
config_name = os.environ.get('FLASK_ENV', 'development')
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

Config = config_by_name.get(config_name, DevelopmentConfig)
