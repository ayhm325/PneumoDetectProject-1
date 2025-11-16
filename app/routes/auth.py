import logging
import traceback
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from app.utils import APIResponse, handle_errors, validate_required_fields, rate_limit_per_user, sanitize_input, AuditLogger

logger = logging.getLogger(__name__)

# تعريف Blueprint للمصادقة
auth = Blueprint('auth', __name__)


# =========================================================================
# 1. تسجيل مستخدم جديد (/register)
# =========================================================================
@auth.route('/register', methods=['POST'])
@rate_limit_per_user(max_requests=5, window_seconds=300)  # 5 محاولات كل 5 دقائق
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
        role = sanitize_input(data.get('userType', data.get('role', 'patient')), 'text')
        
        # تسجيل بيانات الطلب للتشخيص
        logger.info(f"محاولة تسجيل جديد: username='{username}', email='{email}', role='{role}'")
        
        # التحقق من عدم الفراغ بعد التنظيف
        if not username or len(username) < 3:
            logger.warning(f"فشل التحقق من اسم المستخدم: '{username}'")
            response, code = APIResponse.error('اسم المستخدم غير صالح بعد التطهير', 400, 'USERNAME_INVALID')
            return jsonify(response), code
        
        # التحقق من صحة البريد
        if not email:
            logger.warning(f"فشل التحقق من البريد: '{email}'")
            response, code = APIResponse.error('البريد الإلكتروني غير صالح', 400, 'EMAIL_INVALID')
            return jsonify(response), code
        
        # التحقق من قوة كلمة المرور
        if len(password) < 8:
            logger.warning(f"فشل التحقق من قوة كلمة المرور: طول={len(password)}")
            response, code = APIResponse.error('كلمة المرور يجب أن تكون 8 أحرف على الأقل', 400, 'PASSWORD_TOO_SHORT')
            return jsonify(response), code
        
        # التحقق من أن الدور مسموح
        if role not in ['patient', 'doctor']:
            logger.warning(f"فشل التحقق من الدور: '{role}'")
            response, code = APIResponse.error('دور غير مسموح', 400, 'ROLE_INVALID')
            return jsonify(response), code
        
        # التحقق من عدم تكرار اسم المستخدم
        if User.query.filter_by(username=username).first():
            logger.warning(f"محاولة تسجيل باسم مستخدم موجود: {username}")
            response, code = APIResponse.error('اسم المستخدم مستخدم من قبل', 409, 'USERNAME_EXISTS')
            return jsonify(response), code
        
        # التحقق من عدم تكرار البريد
        if User.query.filter_by(email=email).first():
            logger.warning(f"محاولة تسجيل ببريد موجود: {email}")
            response, code = APIResponse.error('البريد الإلكتروني مسجل مسبقاً', 409, 'EMAIL_EXISTS')
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
        print("\n===== TRACEBACK START =====")
        traceback.print_exc()
        print("===== TRACEBACK END =====\n")

        logger.error(f"خطأ غير متوقع في التسجيل: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify(APIResponse.error(f"فشل التسجيل: {str(e)}", 500, 'REGISTRATION_FAILED')), 500



# =========================================================================
# 2. تسجيل الدخول (/login)
# =========================================================================
@auth.route('/login', methods=['POST'])
@rate_limit_per_user(max_requests=10, window_seconds=300)  # 10 محاولات كل 5 دقائق
@validate_required_fields(['username', 'password'])
@handle_errors
def login():
    """تسجيل دخول المستخدم وإنشاء جلسة."""
    try:
        data = request.get_json()
        
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
        
        response, code = APIResponse.success(
            data={
                'username': user.username,
                'user_id': user.id,
                'role': user.role,
                'email': user.email
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
        
        # التحقق من قوة كلمة المرور الجديدة
        if len(new_password) < 8:
            logger.warning(f"محاولة تغيير كلمة المرور: كلمة المرور الجديدة قصيرة للمستخدم {current_user.username}")
            response, code = APIResponse.error('كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل', 400, 'PASSWORD_TOO_SHORT')
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