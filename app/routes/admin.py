"""
لوحة المسؤول والإحصائيات المتقدمة
Admin Dashboard & Advanced Statistics
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, AnalysisResult, Notification, AnalysisHistory, AuditLog
from app.utils import (
    APIResponse, handle_errors, StatisticsHelper,
    AuditLogger, paginate_query
)

logger = logging.getLogger(__name__)

# تعريف Blueprint للإدارة
admin = Blueprint('admin', __name__)


# =========================================================================
# 1. التحقق من صلاحيات المدير
# =========================================================================
def check_admin(f):
    """Decorator للتحقق من أن المستخدم مدير."""
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            AuditLogger.log_event(
                'UNAUTHORIZED_ACCESS',
                current_user.id,
                {'endpoint': request.endpoint, 'method': request.method},
                'WARNING'
            )
            response, code = APIResponse.error(
                'غير مصرح - صلاحيات إدارية مطلوبة',
                403,
                'ADMIN_ONLY'
            )
            return jsonify(response), code
        return f(*args, **kwargs)
    return decorated_function


# =========================================================================
# 2. الإحصائيات العامة للنظام
# =========================================================================
@admin.route('/stats/system', methods=['GET'])
@handle_errors
@check_admin
def get_system_stats():
    """الحصول على إحصائيات النظام العامة."""
    try:
        stats = StatisticsHelper.get_system_stats()
        logger.info(f"System stats retrieved by admin {current_user.username}")
        
        response, code = APIResponse.success(
            data=stats,
            message='إحصائيات النظام'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في جلب الإحصائيات',
            500,
            'STATS_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 3. إحصائيات المستخدمين المتقدمة
# =========================================================================
@admin.route('/stats/users', methods=['GET'])
@handle_errors
@check_admin
def get_users_stats():
    """الحصول على إحصائيات تفصيلية عن المستخدمين."""
    try:
        page = request.args.get('page', 1, type=int)
        role_filter = request.args.get('role', None)
        
        query = User.query
        if role_filter and role_filter in ['patient', 'doctor', 'admin']:
            query = query.filter_by(role=role_filter)
        
        pagination = paginate_query(query.order_by(User.created_at.desc()), page)
        
        users_data = []
        for user in pagination['items']:
            try:
                user_stats = StatisticsHelper.get_user_stats(user.id)
                user_data = user.to_dict()
                user_data.update(user_stats)
                users_data.append(user_data)
            except Exception as e:
                logger.warning(f"Error getting stats for user {user.id}: {e}")
                users_data.append(user.to_dict())
        
        pagination['items'] = users_data
        
        logger.info(f"Users stats retrieved by admin {current_user.username}")
        
        response, code = APIResponse.success(
            data=pagination,
            message='إحصائيات المستخدمين'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching users stats: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في جلب إحصائيات المستخدمين',
            500,
            'USERS_STATS_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 4. إحصائيات التحليلات المتقدمة
# =========================================================================
@admin.route('/stats/analyses', methods=['GET'])
@handle_errors
@check_admin
def get_analyses_stats():
    """الحصول على إحصائيات تفصيلية عن التحليلات."""
    try:
        from datetime import datetime, timedelta
        
        # الفلاتر
        days = request.args.get('days', 30, type=int)
        status_filter = request.args.get('status', None)
        result_filter = request.args.get('result', None)
        
        # حساب التاريخ من البداية
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # الاستعلام الأساسي
        query = AnalysisResult.query.filter(AnalysisResult.created_at >= start_date)
        
        if status_filter and status_filter in ['pending', 'reviewed', 'rejected']:
            query = query.filter_by(review_status=status_filter)
        
        if result_filter and result_filter in ['NORMAL', 'PNEUMONIA']:
            query = query.filter_by(model_result=result_filter)
        
        analyses = query.all()
        
        # حساب الإحصائيات
        total = len(analyses)
        pneumonia = len([a for a in analyses if a.model_result == 'PNEUMONIA'])
        normal = len([a for a in analyses if a.model_result == 'NORMAL'])
        pending = len([a for a in analyses if a.review_status == 'pending'])
        reviewed = len([a for a in analyses if a.review_status == 'reviewed'])
        rejected = len([a for a in analyses if a.review_status == 'rejected'])
        
        # متوسط الثقة
        avg_confidence = round(sum(a.confidence for a in analyses) / total if total > 0 else 0, 2)
        
        # توزيع الثقة
        high_confidence = len([a for a in analyses if a.confidence >= 0.85])
        medium_confidence = len([a for a in analyses if 0.6 <= a.confidence < 0.85])
        low_confidence = len([a for a in analyses if a.confidence < 0.6])
        
        stats = {
            'period': f'{days} أيام',
            'total_analyses': total,
            'by_result': {
                'pneumonia': pneumonia,
                'normal': normal,
                'pneumonia_percentage': round((pneumonia / total * 100) if total > 0 else 0, 2)
            },
            'by_status': {
                'pending': pending,
                'reviewed': reviewed,
                'rejected': rejected
            },
            'confidence': {
                'average': avg_confidence,
                'high': high_confidence,
                'medium': medium_confidence,
                'low': low_confidence
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Analyses stats retrieved by admin {current_user.username}")
        
        response, code = APIResponse.success(
            data=stats,
            message='إحصائيات التحليلات'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching analyses stats: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في جلب إحصائيات التحليلات',
            500,
            'ANALYSES_STATS_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 5. سجل المراجعات (Audit Log)
# =========================================================================
@admin.route('/audit-log', methods=['GET'])
@handle_errors
@check_admin
def get_audit_log():
    """الحصول على سجل المراجعات الأمنية."""
    try:
        page = request.args.get('page', 1, type=int)
        user_id_filter = request.args.get('user_id', None, type=int)
        event_type_filter = request.args.get('event_type', None)
        days = request.args.get('days', 30, type=int)
        
        from datetime import datetime, timedelta

        start_date = datetime.utcnow() - timedelta(days=days)
        
        # استعلام سجل المراجعات من قاعدة البيانات
        query = AuditLog.query.filter(AuditLog.created_at >= start_date)

        if user_id_filter:
            query = query.filter(AuditLog.user_id == user_id_filter)

        if event_type_filter:
            query = query.filter(AuditLog.event_type == event_type_filter)

        pagination = paginate_query(query.order_by(AuditLog.created_at.desc()), page)

        entries = [e.to_dict() for e in pagination['items']]
        pagination['items'] = entries

        logger.info(f"Audit log retrieved by admin {current_user.username}")

        response, code = APIResponse.success(
            data=pagination,
            message='سجل المراجعات'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching audit log: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في جلب سجل المراجعات',
            500,
            'AUDIT_LOG_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 6. إدارة المستخدمين (المسح والتفعيل/التعطيل)
# =========================================================================
@admin.route('/users/<int:user_id>/status', methods=['PUT'])
@handle_errors
@check_admin
def update_user_status(user_id):
    """تحديث حالة نشاط المستخدم."""
    try:
        if user_id == current_user.id:
            response, code = APIResponse.error(
                'لا يمكنك تعديل حالتك الخاصة',
                400,
                'SELF_EDIT_NOT_ALLOWED'
            )
            return jsonify(response), code
        
        user = User.query.get(user_id)
        if not user:
            response, code = APIResponse.error(
                'المستخدم غير موجود',
                404,
                'USER_NOT_FOUND'
            )
            return jsonify(response), code
        
        data = request.get_json() or {}
        is_active = data.get('is_active')
        
        if is_active is not None:
            user.is_active = bool(is_active)
            db.session.commit()
            
            AuditLogger.log_event(
                'ADMIN_ACTION',
                current_user.id,
                {
                    'action': 'user_status_changed',
                    'target_user': user.username,
                    'new_status': 'active' if is_active else 'inactive'
                },
                'INFO'
            )
            
            logger.info(f"User {user.username} status changed by admin {current_user.username}")
            
            response, code = APIResponse.success(
                data=user.to_dict(),
                message=f"تم تحديث حالة المستخدم: {'مفعّل' if is_active else 'معطّل'}"
            )
            return jsonify(response), code
        
        response, code = APIResponse.error(
            'حقل is_active مطلوب',
            400,
            'MISSING_FIELD'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error updating user status: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في تحديث حالة المستخدم',
            500,
            'UPDATE_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 7. الإخطارات والتنبيهات الإدارية
# =========================================================================
@admin.route('/notifications', methods=['GET'])
@handle_errors
@check_admin
def get_system_notifications():
    """الحصول على الإخطارات النظامية والتنبيهات."""
    try:
        page = request.args.get('page', 1, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query
        if unread_only:
            query = query.filter_by(is_read=False)
        
        pagination = paginate_query(query.order_by(Notification.created_at.desc()), page)
        
        notifications_data = [n.to_dict() for n in pagination['items']]
        pagination['items'] = notifications_data
        
        response, code = APIResponse.success(
            data=pagination,
            message='الإخطارات النظامية'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في جلب الإخطارات',
            500,
            'NOTIFICATIONS_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 8. تقرير تفصيلي عن النظام
# =========================================================================
@admin.route('/report/system', methods=['GET'])
@handle_errors
@check_admin
def get_system_report():
    """الحصول على تقرير شامل عن النظام."""
    try:
        from datetime import datetime
        
        # الإحصائيات العامة
        general_stats = StatisticsHelper.get_system_stats()
        
        # إحصائيات النشاط
        today_analyses = AnalysisResult.query.filter(
            AnalysisResult.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count()
        
        # أعلى الأطباء نشاطاً
        top_doctors = db.session.query(
            User.username,
            db.func.count(AnalysisResult.id).label('review_count')
        ).join(
            AnalysisResult, User.id == AnalysisResult.doctor_id
        ).filter(
            User.role == 'doctor'
        ).group_by(User.id).order_by(
            db.func.count(AnalysisResult.id).desc()
        ).limit(5).all()
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'general_stats': general_stats,
            'activity': {
                'analyses_today': today_analyses
            },
            'top_doctors': [
                {'username': doc[0], 'review_count': doc[1]}
                for doc in top_doctors
            ]
        }
        
        logger.info(f"System report generated by admin {current_user.username}")
        
        response, code = APIResponse.success(
            data=report,
            message='التقرير الشامل للنظام'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error generating system report: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في إنشاء التقرير',
            500,
            'REPORT_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 9. إضافة مستخدم جديد
# =========================================================================
@admin.route('/users', methods=['POST'])
@handle_errors
@check_admin
def add_new_user():
    """إضافة مستخدم جديد من قبل مدير."""
    try:
        from werkzeug.security import generate_password_hash
        
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        role = data.get('role', 'patient')
        
        # التحقق من البيانات
        if not username or len(username) < 3:
            response, code = APIResponse.error(
                'اسم المستخدم غير صالح',
                400,
                'INVALID_USERNAME'
            )
            return jsonify(response), code
        
        if not email or '@' not in email:
            response, code = APIResponse.error(
                'البريد الإلكتروني غير صالح',
                400,
                'INVALID_EMAIL'
            )
            return jsonify(response), code
        
        if role not in ['patient', 'doctor', 'admin']:
            response, code = APIResponse.error(
                'دور غير صالح',
                400,
                'INVALID_ROLE'
            )
            return jsonify(response), code
        
        # التحقق من التكرار
        if User.query.filter_by(username=username).first():
            response, code = APIResponse.error(
                'اسم المستخدم موجود بالفعل',
                409,
                'USER_EXISTS'
            )
            return jsonify(response), code
        
        if User.query.filter_by(email=email).first():
            response, code = APIResponse.error(
                'البريد الإلكتروني موجود بالفعل',
                409,
                'EMAIL_EXISTS'
            )
            return jsonify(response), code
        
        # إنشاء مستخدم بكلمة مرور عشوائية
        temp_password = 'TempPass123!'
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(temp_password, method='pbkdf2:sha256'),
            role=role,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        AuditLogger.log_event(
            'ADMIN_ACTION',
            current_user.id,
            {'action': 'user_created', 'username': username, 'role': role},
            'INFO'
        )
        
        logger.info(f"User {username} created by admin {current_user.username}")
        
        response, code = APIResponse.success(
            data=user.to_dict(),
            message=f"تم إنشاء المستخدم {username} بنجاح",
            code=201
        )
        return jsonify(response), code
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في إنشاء المستخدم',
            500,
            'CREATE_ERROR'
        )
        return jsonify(response), code


# =========================================================================
# 10. حفظ إعدادات النظام
# =========================================================================


# =========================================================================
# 11. مسح البيانات (Danger Zone)
# =========================================================================
@admin.route('/clear-data', methods=['POST'])
@handle_errors
@check_admin
def clear_system_data():
    """مسح جميع بيانات النظام (عملية حساسة)."""
    try:
        # طلب تأكيد صريح
        data = request.get_json() or {}
        confirmation = data.get('confirm_clearance')
        
        if not confirmation or confirmation != 'CLEAR_ALL_DATA':
            response, code = APIResponse.error(
                'تأكيد واضح مطلوب (تعيين confirm_clearance إلى CLEAR_ALL_DATA)',
                400,
                'CLEARANCE_NOT_CONFIRMED'
            )
            return jsonify(response), code
        
        # تسجيل العملية
        AuditLogger.log_event(
            'DANGER_ZONE_ACTION',
            current_user.id,
            {'action': 'system_data_cleared'},
            'CRITICAL'
        )
        
        # مسح التحليلات
        AnalysisResult.query.delete()
        
        # مسح سجل التحليلات
        AnalysisHistory.query.delete()
        
        # مسح الإخطارات
        Notification.query.delete()
        
        # الالتزام بالتغييرات
        db.session.commit()
        
        logger.warning(f"System data cleared by admin {current_user.username}")
        
        response, code = APIResponse.success(
            message='تم مسح جميع بيانات النظام بنجاح'
        )
        return jsonify(response), code
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing system data: {e}", exc_info=True)
        response, code = APIResponse.error(
            'خطأ في مسح البيانات',
            500,
            'CLEAR_ERROR'
        )
        return jsonify(response), code
