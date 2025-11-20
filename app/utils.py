"""
الدوال المساعدة والأدوات (Utilities)
"""
import os
import uuid
import logging
import html
import re
from functools import wraps
from logging.handlers import RotatingFileHandler
from flask import current_app, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)


def sanitize_input(value, input_type='text'):
    """تنظيف وتطهير المدخلات من XSS والأحرف الضارة.
    
    Args:
        value: القيمة المدخلة
        input_type: نوع المدخل (text, email, username, notes)
    
    Returns:
        القيمة المنظفة
    """
    if not isinstance(value, str):
        return ''
    
    value = value.strip()
    
    if input_type == 'text':
        # إزالة HTML tags و JavaScript
        # أولاً: افصل واهرب الكيانات الخاصة بالـ HTML
        value = html.escape(value)
        # إزالة سلاسل JavaScript الشائعة وسمات الأحداث (onerror, onload, onclick...)
        # إزالة "javascript:" و "alert(...)" وكلمات الوظائف الخبيثة
        value = re.sub(r'(?i)javascript:\s*', '', value)
        value = re.sub(r'(?i)alert\s*\([^)]*\)', '', value)
        value = re.sub(r'(?i)on\w+\s*=\s*"[^"]*"', '', value)
        value = re.sub(r"(?i)on\w+\s*=\s*'[^']*'", '', value)
        value = re.sub(r'(?i)on\w+\s*=\s*[^\s>]+', '', value)
        # السماح بـ alphanumeric وبعض الأحرف الخاصة الآمنة والعربية بعد التنظيف
        value = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF_\-. ]', '', value)
    
    elif input_type == 'email':
        # تطبيع البريد
        value = value.lower()
        # فحص صيغة البريد
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            return ''
    
    elif input_type == 'username':
        # أسماء المستخدمين: alphanumeric و - و _
        value = re.sub(r'[^a-zA-Z0-9_-]', '', value)
    
    elif input_type == 'notes':
        # نصوص طويلة: السماح بـ newlines مع escape HTML
        value = html.escape(value)
        value = value[:1000]  # حد أقصى 1000 حرف
    
    return value


class APIResponse:
    """مساعد موحد لاستجابات API."""
    
    @staticmethod
    def success(data=None, message='Success', code=200, **kwargs):
        """استجابة ناجحة."""
        response = {
            'success': True,
            'message': message,
            'code': code,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        response.update(kwargs)
        return response, code
    
    @staticmethod
    def error(message='Error', code=400, error_code=None, **kwargs):
        """استجابة خطأ."""
        response = {
            'success': False,
            'message': message,
            'code': code,
            'error_code': error_code,
            'timestamp': datetime.utcnow().isoformat()
        }
        response.update(kwargs)
        return response, code


def handle_errors(f):
    """Decorator لمعالجة الأخطاء العامة."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error in {f.__name__}: {str(e)}")
            response, code = APIResponse.error(str(e), 400, 'VALIDATION_ERROR')
            return jsonify(response), code
        except PermissionError as e:
            logger.warning(f"Permission error in {f.__name__}: {str(e)}")
            response, code = APIResponse.error(str(e), 403, 'PERMISSION_ERROR')
            return jsonify(response), code
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            response, code = APIResponse.error('حدث خطأ غير متوقع', 500, 'INTERNAL_ERROR')
            return jsonify(response), code
    return decorated_function


def ensure_data_ownership(owner_id, current_user_id, current_user_obj=None, admin_allowed=True):
    """التحقق من ملكية البيانات ومنع وصول المستخدم لبيانات الآخرين.
    
    Args:
        owner_id: معرف مالك البيانات
        current_user_id: معرف المستخدم الحالي
        current_user_obj: كائن المستخدم الحالي (اختياري)
        admin_allowed: هل يُسمح للمسؤولين بالوصول
    
    Raises:
        PermissionError: إذا لم يكن لدى المستخدم الصلاحية
    """
    if owner_id != current_user_id:
        # السماح للمسؤولين إذا كانوا لديهم صلاحيات
        if admin_allowed and current_user_obj and hasattr(current_user_obj, 'is_admin'):
            if current_user_obj.is_admin():
                return
        
        logger.warning(
            f'Data access violation attempt: user {current_user_id} '
            f'attempted to access user {owner_id} data'
        )
        
        # تسجيل محاولة الوصول غير المصرح
        try:
            AuditLogger.log_event(
                'UNAUTHORIZED_DATA_ACCESS',
                current_user_id,
                {'target_user_id': owner_id},
                'WARNING'
            )
        except Exception as e:
            logger.error(f'Failed to log audit event: {e}')
        
        raise PermissionError('لا يمكنك الوصول إلى هذه البيانات')



def validate_required_fields(required_fields):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            data = request.get_json(silent=True)
            
            logger.info(f"[VALIDATE] Function: {f.__name__}, data={data}, required={required_fields}")
            logger.info(f"[REQUEST] Content-Type: {request.content_type}, Method: {request.method}")
            logger.info(f"[REQUEST] Headers: {dict(request.headers)}")
            logger.info(f"[REQUEST] Data type: {type(data)}")
            
            # JSON فاضي أو خطأ
            if not isinstance(data, dict):
                logger.error(f"INVALID: {f.__name__} got {type(data)} instead of dict, data={data}")
                response, code = APIResponse.error(
                    message=f'تنسيق الطلب غير صالح (نوع البيانات: {type(data).__name__})',
                    code=400,
                    error_code='INVALID_JSON'
                )
                return jsonify(response), code
            
            # التحقق من الحقول المطلوبة
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                logger.warning(f"Missing fields in {f.__name__}: {missing_fields}")
                response, code = APIResponse.error(
                    message=f'حقول ناقصة: {", ".join(missing_fields)}',
                    code=400,
                    error_code='MISSING_FIELDS'
                )
                return jsonify(response), code

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_per_user(max_requests=100, window_seconds=60):
    """Decorator لتحديد معدل الطلبات لكل مستخدم."""
    from flask import request, g
    from collections import defaultdict
    import time
    
    # تخزين مؤقت بسيط (في الإنتاج استخدم Redis)
    request_history = defaultdict(list)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            
            user_id = current_user.id if current_user.is_authenticated else request.remote_addr
            current_time = time.time()
            
            # تنظيف الطلبات القديمة
            request_history[user_id] = [
                timestamp for timestamp in request_history[user_id]
                if current_time - timestamp < window_seconds
            ]
            
            # التحقق من الحد الأقصى
            if len(request_history[user_id]) >= max_requests:
                response, code = APIResponse.error(
                    'تم تجاوز حد الطلبات المسموح به',
                    429,
                    'RATE_LIMIT_EXCEEDED'
                )
                return jsonify(response), code
            
            request_history[user_id].append(current_time)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def save_file_securely(file_data, folder, extension="jpg"):
    """حفظ الملف بأمان مع التحقق من الصحة."""
    if not file_data:
        raise ValueError('ملف فارغ')
    
    # التحقق من امتداد الملف
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png'})
    if extension.lower() not in allowed_extensions:
        raise ValueError(f'نوع الملف غير مدعوم: {extension}')
    
    # التحقق من حجم الملف
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)
    if len(file_data) > max_size:
        raise ValueError(f'حجم الملف كبير جداً (الحد الأقصى: {max_size / 1024 / 1024:.1f} MB)')
    
    # إنشاء اسم ملف عشوائي
    filename = f"{uuid.uuid4()}.{extension.lower()}"
    
    # بناء المسار الكامل
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    full_path = os.path.join(upload_folder, folder, filename)
    
    # التحقق من Path Traversal
    full_path_abs = os.path.abspath(full_path)
    upload_folder_abs = os.path.abspath(upload_folder)
    if not full_path_abs.startswith(upload_folder_abs):
        raise ValueError('مسار غير صالح')
    
    # إنشاء المجلد إن لم يكن موجود
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # حفظ الملف
    with open(full_path, 'wb') as f:
        f.write(file_data)
    
    logger.info(f"File saved: {full_path}")
    return folder, filename


def get_file_path(folder, filename):
    """الحصول على المسار الكامل للملف مع التحقق من الأمان."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    full_path = os.path.join(upload_folder, folder, filename)
    
    # التحقق من Path Traversal
    full_path_abs = os.path.abspath(full_path)
    upload_folder_abs = os.path.abspath(upload_folder)
    
    if not full_path_abs.startswith(upload_folder_abs):
        raise ValueError('وصول غير صالح للملف')
    
    if not os.path.exists(full_path_abs):
        raise FileNotFoundError('الملف غير موجود')
    
    return full_path_abs


def paginate_query(query, page=1, per_page=None):
    """مساعد للـ Pagination."""
    per_page = per_page or current_app.config.get('ITEMS_PER_PAGE', 20)
    
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        'items': pagination.items,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next
    }


def setup_logging(app):
    """إعداد نظام Logging متقدم."""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            os.path.join('logs', app.config['LOG_FILE']),
            maxBytes=10485760,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('PneumoDetect startup')
    
    # أضف معالج الكونسول أيضاً
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    
    # أضف handler للتطبيق الرئيسي
    app.logger.addHandler(console_handler)


def get_client_info():
    """الحصول على معلومات العميل (IP، User-Agent)."""
    from flask import request
    return {
        'ip': request.remote_addr,
        'user_agent': request.user_agent.string,
        'endpoint': request.endpoint,
        'method': request.method
    }


class ImageValidator:
    """مدقق صور."""
    
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'GIF', 'BMP'}
    MIN_SIZE = (50, 50)
    MAX_SIZE = (4096, 4096)
    
    @staticmethod
    def validate(image_pil):
        """التحقق من صحة الصورة."""
        if image_pil.format not in ImageValidator.ALLOWED_FORMATS:
            raise ValueError(f'صيغة الصورة غير مدعومة: {image_pil.format}')
        
        width, height = image_pil.size
        if width < ImageValidator.MIN_SIZE[0] or height < ImageValidator.MIN_SIZE[1]:
            raise ValueError('الصورة صغيرة جداً')
        
        if width > ImageValidator.MAX_SIZE[0] or height > ImageValidator.MAX_SIZE[1]:
            raise ValueError('الصورة كبيرة جداً')
        
        if image_pil.mode not in ['RGB', 'L', 'RGBA']:
            image_pil = image_pil.convert('RGB')
        
        return image_pil


class AuditLogger:
    """نظام تسجيل المراجعة والأمان (Audit Log)."""
    
    AUDIT_EVENTS = {
        'LOGIN_SUCCESS': 'تسجيل دخول ناجح',
        'LOGIN_FAILED': 'فشل تسجيل الدخول',
        'LOGOUT': 'تسجيل خروج',
        'ANALYSIS_CREATED': 'إنشاء تحليل',
        'ANALYSIS_REVIEWED': 'مراجعة تحليل',
        'ANALYSIS_DELETED': 'حذف تحليل',
        'PASSWORD_CHANGED': 'تغيير كلمة المرور',
        'PROFILE_UPDATED': 'تحديث الملف الشخصي',
        'UNAUTHORIZED_ACCESS': 'محاولة وصول غير مصرح',
        'ADMIN_ACTION': 'إجراء إداري'
    }
    
    @staticmethod
    def log_event(event_type, user_id=None, details=None, severity='INFO'):
        """تسجيل حدث أمني."""
        from app import db
        from app.models import User
        
        try:
            event_description = AuditLogger.AUDIT_EVENTS.get(event_type, event_type)
            
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'event_description': event_description,
                'user_id': user_id,
                'details': details or {},
                'severity': severity,
                'client_info': get_client_info()
            }
            
            log_level = getattr(logging, severity, logging.INFO)
            logger.log(log_level, f"[AUDIT] {event_description} | User: {user_id} | Details: {details}")
            # حاول حفظ السجل في قاعدة البيانات إن أمكن
            try:
                from app.models import AuditLog
                import json

                client = get_client_info()

                audit_record = AuditLog(
                    event_type=event_type,
                    event_description=event_description,
                    user_id=user_id,
                    details=json.dumps(details or {}),
                    severity=severity,
                    client_ip=client.get('ip'),
                    user_agent=client.get('user_agent'),
                    endpoint=client.get('endpoint'),
                    method=client.get('method')
                )
                db.session.add(audit_record)
                db.session.commit()
                # قم بإضافة معرف السجل إلى مخرجات السجل
                log_entry['db_id'] = audit_record.id
            except Exception as e:
                logger.debug(f"Audit DB persist failed: {e}")

            return log_entry
        except Exception as e:
            logger.error(f"Error in audit logging: {e}")
            return None


class StatisticsHelper:
    """مساعد الإحصائيات المتقدمة."""
    
    @staticmethod
    def get_system_stats():
        """الحصول على إحصائيات النظام العامة."""
        from app.models import User, AnalysisResult
        
        total_users = User.query.count()
        total_analyses = AnalysisResult.query.count()
        
        pneumonia_count = AnalysisResult.query.filter_by(model_result='PNEUMONIA').count()
        normal_count = AnalysisResult.query.filter_by(model_result='NORMAL').count()
        
        pending_reviews = AnalysisResult.query.filter_by(review_status='pending').count()
        
        return {
            'total_users': total_users,
            'total_doctors': User.query.filter_by(role='doctor').count(),
            'total_patients': User.query.filter_by(role='patient').count(),
            'total_admins': User.query.filter_by(role='admin').count(),
            'total_analyses': total_analyses,
            'pneumonia_detected': pneumonia_count,
            'normal_cases': normal_count,
            'pending_reviews': pending_reviews,
            'pneumonia_percentage': round((pneumonia_count / total_analyses * 100) if total_analyses > 0 else 0, 2),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_user_stats(user_id):
        """الحصول على إحصائيات المستخدم."""
        from app.models import User, AnalysisResult
        
        user = User.query.get(user_id)
        if not user:
            raise ValueError('المستخدم غير موجود')
        
        if user.is_patient():
            user_analyses = AnalysisResult.query.filter_by(user_id=user_id).all()
            total = len(user_analyses)
            pneumonia = len([a for a in user_analyses if a.model_result == 'PNEUMONIA'])
            normal = len([a for a in user_analyses if a.model_result == 'NORMAL'])
            
            return {
                'username': user.username,
                'role': user.role,
                'total_analyses': total,
                'pneumonia_detected': pneumonia,
                'normal_cases': normal,
                'avg_confidence': round(sum(a.confidence for a in user_analyses) / total if total > 0 else 0, 2),
                'last_analysis': max([a.created_at for a in user_analyses], default=None).isoformat() if user_analyses else None
            }
        
        elif user.is_doctor():
            reviewed_analyses = AnalysisResult.query.filter_by(doctor_id=user_id).all()
            total_reviewed = len(reviewed_analyses)
            
            return {
                'username': user.username,
                'role': user.role,
                'total_reviewed': total_reviewed,
                'pending_reviews': AnalysisResult.query.filter_by(review_status='pending').count(),
                'last_review': max([a.updated_at for a in reviewed_analyses], default=None).isoformat() if reviewed_analyses else None
            }
        
        return {'username': user.username, 'role': user.role}


class NotificationSystem:
    """نظام التنبيهات والإشعارات."""
    
    NOTIFICATION_TYPES = {
        'ANALYSIS_READY': 'التحليل جاهز للمراجعة',
        'ANALYSIS_REVIEWED': 'تم مراجعة التحليل',
        'REPORT_READY': 'التقرير جاهز للتحميل',
        'SYSTEM_MESSAGE': 'رسالة نظام',
        'WARNING': 'تحذير أمني'
    }
    
    @staticmethod
    def create_notification(user_id, notification_type, message, related_id=None):
        """إنشاء إشعار جديد."""
        try:
            from app.models import User
            
            user = User.query.get(user_id)
            if not user:
                raise ValueError('المستخدم غير موجود')
            
            notification = {
                'id': uuid.uuid4().hex,
                'user_id': user_id,
                'type': notification_type,
                'message': message,
                'related_id': related_id,
                'created_at': datetime.utcnow().isoformat(),
                'read': False,
                'type_description': NotificationSystem.NOTIFICATION_TYPES.get(notification_type, 'إشعار')
            }
            
            logger.info(f"Notification created for user {user_id}: {notification_type}")
            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
