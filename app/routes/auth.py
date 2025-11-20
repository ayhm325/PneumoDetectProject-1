import logging
import re  # تمت الإضافة للتحقق من قوة كلمة المرور
from flask import Blueprint, request, jsonify, current_app, redirect
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, csrf
from app.models import User
from app.utils import APIResponse, handle_errors, validate_required_fields, rate_limit_per_user, sanitize_input, AuditLogger

logger = logging.getLogger(__name__)

# تعريف Blueprint للمصادقة
auth = Blueprint('auth', __name__)


def is_strong_password(password):
    """التحقق من قوة كلمة المرور."""
    if len(password) < 8:
        return False
    # التحقق من وجود حرف كبير، حرف صغير، رقم، ورمز
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


# =========================================================================
# 1. تسجيل مستخدم جديد (/register)
# =========================================================================
@auth.route('/register', methods=['POST'])
@csrf.exempt
@rate_limit_per_user(max_requests=5, window_seconds=60)  # 5 محاولات كل 1 دقيقة
@validate_required_fields(['username', 'email', 'password'])
@handle_errors
def register():
    """تسجيل مستخدم جديد (الدور الافتراضي: مريض)."""
    try:
        data = request.get_json()
        
        # تنظيف المدخلات
        username = sanitize_input(data.get('username', ''), 'username')
        email = sanitize_input(data.get('email', ''), 'email')
        password = data.get('password', '')
        
        # --- إصلاح: تثبيت دور المستخدم على 'patient' ---
        role = 'patient' # لا تسمح للمستخدم باختيار الدور
        
        # تسجيل بيانات الطلب للتشخيص
        logger.info(f"محاولة تسجيل جديد: username='{username}', email='{email}', role='{role}'")
        
        # التحقق من عدم الفراغ بعد التنظيف
        if not username or len(username) < 3:
            logger.warning(f"فشل التحقق من اسم المستخدم: '{username}'")
            response, code = APIResponse.error('اسم المستخدم غير صالح', 400, 'USERNAME_INVALID')
            return jsonify(response), code
        
        # --- تحسين: التحقق من صحة البريد الإلكتروني ---
        if not email or not User.validate_email(email):
            logger.warning(f"فشل التحقق من البريد: '{email}'")
            response, code = APIResponse.error('البريد الإلكتروني غير صالح', 400, 'EMAIL_INVALID')
            return jsonify(response), code
        
        # --- تحسين: التحقق من قوة كلمة المرور ---
        if not is_strong_password(password):
            logger.warning(f"فشل التحقق من قوة كلمة المرور للمستخدم '{username}'")
            response, code = APIResponse.error('كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل وتشمل أحرف كبيرة وصغيرة وأرقام ورموز', 400, 'PASSWORD_WEAK')
            return jsonify(response), code
        
        # --- تحسين: منع تعداد المستخدمين ---
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            logger.warning(f"محاولة تسجيل ببيانات موجودة: username='{username}', email='{email}'")
            response, code = APIResponse.error('اسم المستخدم أو البريد الإلكتروني مستخدم بالفعل', 409, 'USER_EXISTS')
            return jsonify(response), code
        
        # تشفير كلمة المرور
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # إنشاء المستخدم
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=role
        )
        
        # حفظ في قاعدة البيانات
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"تسجيل مستخدم جديد بنجاح: {username} ({role})")
        
        response, code = APIResponse.success(
            data={'user_id': new_user.id, 'username': new_user.username},
            message='تم إنشاء الحساب بنجاح',
            code=201
        )
        return jsonify(response), code
        
    except ValueError as e:
        # معالجة أخطاء التحقق (Validation Errors)
        logger.warning(f"خطأ في التحقق من صحة بيانات التسجيل: {str(e)}")
        response, code = APIResponse.error(str(e), 400, 'VALIDATION_ERROR')
        return jsonify(response), code
        
    except Exception as e:
        # --- تحسين: إزالة طباعة الأخطاء ---
        logger.error(f"خطأ غير متوقع في التسجيل: {str(e)}", exc_info=True)
        db.session.rollback()
        response, code = APIResponse.error(f"فشل التسجيل: {str(e)}", 500, 'REGISTRATION_FAILED')
        return jsonify(response), code


# =========================================================================
# 2. تسجيل الدخول (/login)
# =========================================================================
@auth.route('/login', methods=['POST', 'GET'])
@csrf.exempt
@rate_limit_per_user(max_requests=10, window_seconds=60)  # 10 محاولات كل 1 دقيقة
@handle_errors
def login():
    """تسجيل دخول المستخدم وإنشاء جلسة."""
    logger.info("[LOGIN] Function entered")
    try:
        # Support both JSON POST and form data (GET with query params or POST form)
        if request.method == 'GET' or request.content_type != 'application/json':
            # Get from query parameters or form data
            username = request.args.get('username', request.form.get('username', '')).strip()
            password = request.args.get('password', request.form.get('password', ''))
            remember_me = request.args.get('remember_me', request.form.get('remember_me', False))
            # Convert string 'on' or 'true' to boolean
            if isinstance(remember_me, str):
                remember_me = remember_me.lower() in ['on', 'true', '1', 'yes']
            logger.info(f"[LOGIN] data from query/form: username={username}, remember_me={remember_me}")
        else:
            # Get from JSON
            data = request.get_json() or {}
            logger.info(f"[LOGIN] data from request.get_json(): {data}")
            username = data.get('username', '').strip()
            password = data.get('password', '')
            remember_me = data.get('remember_me', False)
        
        # تسجيل بيانات الطلب للتشخيص
        logger.info(f"محاولة تسجيل دخول: username='{username}', remember_me={remember_me}")
        
        if not username or not password:
            logger.warning("فشل تسجيل الدخول: بيانات غير مكتملة")
            response, code = APIResponse.error('اسم المستخدم وكلمة المرور مطلوبة', 400, 'MISSING_CREDENTIALS')
            return jsonify(response), code
        
        # البحث عن المستخدم
        user = User.query.filter_by(username=username).first()
        
        # التحقق من وجود المستخدم والمصادقة
        if not user or not check_password_hash(user.password_hash, password):
            logger.warning(f"محاولة دخول فاشلة: {username}")
            response, code = APIResponse.error('بيانات دخول غير صحيحة', 401, 'INVALID_CREDENTIALS')
            return jsonify(response), code
        
        # التحقق من تفعيل الحساب
        if not user.is_active:
            logger.warning(f"محاولة دخول من حساب معطل: {username}")
            response, code = APIResponse.error('الحساب معطل', 403, 'ACCOUNT_DISABLED')
            return jsonify(response), code
        
        # تسجيل الدخول بنجاح
        login_user(user, remember=remember_me)
        logger.info(f"دخول ناجح: {username}")
        # Determine redirect URL server-side for a clean professional flow
        if user.role == 'doctor':
            redirect_url = '/doctor'
        elif user.role == 'admin':
            redirect_url = '/admin'
        else:
            redirect_url = '/patient'

        # If request came from query parameters (GET/form), redirect directly
        if request.method == 'GET' or request.content_type != 'application/json':
            logger.info(f"Redirecting user {username} to {redirect_url}")
            return redirect(redirect_url)
        
        # Otherwise return JSON for AJAX requests
        response, code = APIResponse.success(
            data={
                'username': user.username,
                'user_id': user.id,
                'role': user.role,
                'email': user.email,
                'redirect_url': redirect_url
            },
            message='تم تسجيل الدخول بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}", exc_info=True)
        response, code = APIResponse.error('فشل تسجيل الدخول', 500, 'LOGIN_FAILED')
        return jsonify(response), code


# =========================================================================
# 3. تسجيل الخروج (/logout)
# =========================================================================
@auth.route('/logout', methods=['POST'])
@handle_errors
@login_required
def logout():
    """إنهاء جلسة المستخدم الحالي."""
    try:
        username = current_user.username
        logout_user()
        logger.info(f"خروج ناجح: {username}")
        
        response, code = APIResponse.success(message='تم تسجيل الخروج بنجاح')
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل الخروج: {str(e)}", exc_info=True)
        response, code = APIResponse.error('فشل تسجيل الخروج', 500, 'LOGOUT_FAILED')
        return jsonify(response), code


# =========================================================================
# 4. حالة المستخدم الحالي (/status)
# =========================================================================
@auth.route('/status', methods=['GET'])
@handle_errors
def status():
    """إرجاع حالة تسجيل الدخول والدور."""
    try:
        if current_user.is_authenticated:
            response, code = APIResponse.success(
                data={
                    'username': current_user.username,
                    'user_id': current_user.id,
                    'role': current_user.role,
                    'email': current_user.email,
                    'is_doctor': current_user.is_doctor(),
                    'is_admin': current_user.is_admin(),
                    'is_authenticated': True
                },
                message='المستخدم مسجل دخول'
            )
            return jsonify(response), 200
        else:
            response, code = APIResponse.success(
                data={'is_authenticated': False},
                message='غير مسجل دخول'
            )
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"خطأ في جلب حالة المستخدم: {str(e)}", exc_info=True)
        response, code = APIResponse.error('فشل جلب حالة المستخدم', 500, 'STATUS_CHECK_FAILED')
        return jsonify(response), code


# =========================================================================
# 5. تغيير كلمة المرور (/change-password)
# =========================================================================
@auth.route('/change-password', methods=['POST'])
@handle_errors
@validate_required_fields(['old_password', 'new_password', 'confirm_password'])
@login_required
def change_password():
    """تغيير كلمة مرور المستخدم."""
    try:
        data = request.get_json()
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # التحقق من تطابق كلمتي المرور الجديدة
        if new_password != confirm_password:
            logger.warning(f"محاولة تغيير كلمة المرور: كلمات المرور غير متطابقة للمستخدم {current_user.username}")
            response, code = APIResponse.error('كلمات المرور الجديدة غير متطابقة', 400, 'PASSWORD_MISMATCH')
            return jsonify(response), code
        
        # --- تحسين: استخدام نفس التحقق من قوة كلمة المرور ---
        if not is_strong_password(new_password):
            logger.warning(f"محاولة تغيير كلمة المرور: كلمة المرور الجديدة ضعيفة للمستخدم {current_user.username}")
            response, code = APIResponse.error('كلمة المرور الجديدة يجب أن تحتوي على 8 أحرف على الأقل وتشمل أحرف كبيرة وصغيرة وأرقام ورموز', 400, 'PASSWORD_WEAK')
            return jsonify(response), code
        
        # التحقق من كلمة المرور القديمة
        if not check_password_hash(current_user.password_hash, old_password):
            logger.warning(f"محاولة تغيير كلمة المرور: كلمة المرور القديمة غير صحيحة للمستخدم {current_user.username}")
            response, code = APIResponse.error('كلمة المرور القديمة غير صحيحة', 400, 'OLD_PASSWORD_INVALID')
            return jsonify(response), code
        
        # تحديث كلمة المرور
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        logger.info(f"تغيير كلمة المرور بنجاح للمستخدم: {current_user.username}")
        
        response, code = APIResponse.success(message='تم تغيير كلمة المرور بنجاح')
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f"خطأ في تغيير كلمة المرور: {str(e)}", exc_info=True)
        db.session.rollback()
        response, code = APIResponse.error('فشل تغيير كلمة المرور', 500, 'PASSWORD_CHANGE_FAILED')
        return jsonify(response), code


# =========================================================================
# 6. ملف الشخصي (/profile)
# =========================================================================
@auth.route('/profile', methods=['GET'])
@handle_errors
@login_required
def get_profile():
    """الحصول على بيانات الملف الشخصي."""
    try:
        response, code = APIResponse.success(
            data=current_user.to_dict(),
            message='تم جلب الملف الشخصي'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f"خطأ في جلب الملف الشخصي: {str(e)}", exc_info=True)
        response, code = APIResponse.error('فشل جلب الملف الشخصي', 500, 'PROFILE_GET_FAILED')
        return jsonify(response), code


@auth.route('/profile', methods=['PUT'])
@handle_errors
@login_required
def update_profile():
    """تحديث بيانات الملف الشخصي."""
    try:
        data = request.get_json() or {}
        
        email = data.get('email', '').lower().strip()
        
        if email:
            # --- تحسين: استخدام نفس التحقق من البريد الإلكتروني ---
            if not User.validate_email(email):
                logger.warning(f"محاولة تحديث البريد الإلكتروني ببريد غير صالح: {email}")
                response, code = APIResponse.error('البريد الإلكتروني غير صالح', 400, 'EMAIL_INVALID')
                return jsonify(response), code
            
            # التحقق من عدم استخدام البريد من قبل
            existing_user = User.query.filter(
                User.email == email,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                logger.warning(f"محاولة تحديث البريد الإلكتروني ببريد مستخدم من قبل: {email}")
                response, code = APIResponse.error('البريد الإلكتروني مستخدم من قبل', 409, 'EMAIL_EXISTS')
                return jsonify(response), code
            
            current_user.email = email
        
        db.session.commit()
        logger.info(f"تحديث الملف الشخصي بنجاح للمستخدم: {current_user.username}")
        
        response, code = APIResponse.success(
            data=current_user.to_dict(),
            message='تم تحديث الملف الشخصي'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f"خطأ في تحديث الملف الشخصي: {str(e)}", exc_info=True)
        db.session.rollback()
        response, code = APIResponse.error('فشل تحديث الملف الشخصي', 500, 'PROFILE_UPDATE_FAILED')
        return jsonify(response), code