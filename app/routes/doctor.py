import logging
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from app import db
from app.models import AnalysisResult, User, AnalysisHistory, Notification
from app.utils import APIResponse, handle_errors, validate_required_fields, paginate_query, AuditLogger, ensure_data_ownership
from functools import wraps

logger = logging.getLogger(__name__)

# إنشاء Blueprint لمسارات الأطباء والمستخدمين
doctor = Blueprint('doctor', __name__)


# =========================================================================
# 1. Decorator للتحقق من الأدوار
# =========================================================================
def role_required(required_roles):
    """Decorator للتحقق من أن المستخدم لديه أحد الأدوار المطلوبة."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                raise PermissionError('يجب تسجيل الدخول أولاً')
            
            if current_user.role not in required_roles:
                logger.warning(f'محاولة وصول غير مصرح: {current_user.username} ({current_user.role})')
                raise PermissionError(f'دور غير مسموح: {current_user.role}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =========================================================================
# 2. مسار نتائج المريض (/my/results)
# =========================================================================
@doctor.route('/my/results', methods=['GET'])
@handle_errors
@login_required
def my_results():
    """يعرض سجل التحاليل الخاص بالمستخدم الحالي (المريض)."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        sort_by = request.args.get('sort_by', 'created_at', type=str)
        
        # التحقق من صحة معامل الترتيب
        allowed_sorts = ['created_at', 'confidence', 'model_result']
        if sort_by not in allowed_sorts:
            sort_by = 'created_at'
        
        # بناء الاستعلام
        query = AnalysisResult.query.filter_by(user_id=current_user.id)
        
        # الترتيب
        if sort_by == 'created_at':
            query = query.order_by(AnalysisResult.created_at.desc())
        elif sort_by == 'confidence':
            query = query.order_by(AnalysisResult.confidence.desc())
        elif sort_by == 'model_result':
            query = query.order_by(AnalysisResult.model_result.asc())
        
        # Pagination
        pagination_data = paginate_query(query, page, per_page)
        
        # تحضير البيانات مع التحقق من الملكية
        results_list = []
        for result in pagination_data['items']:
            # ✅ التحقق المزدوج من الملكية
            ensure_data_ownership(result.user_id, current_user.id, current_user, admin_allowed=True)
            
            reviewer_username = result.reviewer.username if result.reviewer else None
            
            results_list.append({
                'id': result.id,
                'model_result': result.model_result,
                'confidence': result.confidence,
                'created_at': result.created_at.isoformat(),
                'updated_at': result.updated_at.isoformat(),
                'review_status': result.review_status,
                'doctor_notes': result.doctor_notes,
                'doctor_username': reviewer_username,
                'image_url': url_for('analysis.serve_file', filename=result.image_path, _external=True),
                'saliency_url': url_for('analysis.serve_file', filename=result.saliency_path, _external=True)
            })
        
        response, code = APIResponse.success(
            data={
                'items': results_list,
                'page': pagination_data['page'],
                'per_page': pagination_data['per_page'],
                'total': pagination_data['total'],
                'pages': pagination_data['pages'],
                'has_prev': pagination_data['has_prev'],
                'has_next': pagination_data['has_next']
            },
            message='تم جلب النتائج بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f'خطأ في جلب النتائج: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 3. مسار قائمة التحاليل للمراجعة (/doctor/analyses)
# =========================================================================
@doctor.route('/analyses', methods=['GET'])
@handle_errors
@login_required
def doctor_analyses():
    """يعرض قائمة التحاليل للمراجعة مع خيارات البحث والفلترة."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # معايير البحث والفلترة
        patient_name = request.args.get('patient', '', type=str).strip()
        status_filter = request.args.get('status', 'pending', type=str)
        result_filter = request.args.get('result', '', type=str)
        
        # التحقق من صحة status_filter
        valid_statuses = ['pending', 'reviewed', 'rejected', 'all']
        if status_filter not in valid_statuses:
            status_filter = 'pending'
        
        # بناء الاستعلام
        query = AnalysisResult.query
        
        # فلترة حسب الحالة
        if status_filter != 'all':
            query = query.filter_by(review_status=status_filter)
        
        # البحث عن المريض
        if patient_name:
            users = User.query.filter(
                User.username.ilike(f'%{patient_name}%')
            ).all()
            user_ids = [u.id for u in users]
            
            if user_ids:
                query = query.filter(AnalysisResult.user_id.in_(user_ids))
            else:
                query = query.filter(AnalysisResult.user_id == -1)  # لا توجد نتائج
        
        # فلترة حسب النتيجة
        if result_filter in ['NORMAL', 'PNEUMONIA']:
            query = query.filter_by(model_result=result_filter)
        
        # الترتيب
        query = query.order_by(AnalysisResult.created_at.desc())
        
        # Pagination
        pagination_data = paginate_query(query, page, per_page)
        
        # تحضير البيانات
        analyses_list = []
        for result in pagination_data['items']:
            patient_username = result.uploader.username if result.uploader else 'N/A'
            reviewer_username = result.reviewer.username if result.reviewer else None
            
            analyses_list.append({
                'id': result.id,
                'patient_username': patient_username,
                'patient_id': result.user_id,
                'model_result': result.model_result,
                'confidence': result.confidence,
                'created_at': result.created_at.isoformat(),
                'review_status': result.review_status,
                'doctor_notes': result.doctor_notes,
                'doctor_username': reviewer_username,
                'image_url': url_for('analysis.serve_file', filename=result.image_path, _external=True),
                'saliency_url': url_for('analysis.serve_file', filename=result.saliency_path, _external=True)
            })
        
        response, code = APIResponse.success(
            data={
                'items': analyses_list,
                'page': pagination_data['page'],
                'per_page': pagination_data['per_page'],
                'total': pagination_data['total'],
                'pages': pagination_data['pages'],
                'filters': {
                    'patient': patient_name,
                    'status': status_filter,
                    'result': result_filter
                }
            },
            message='تم جلب التحاليل بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f'خطأ في جلب التحاليل: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 4. مسار مراجعة التحليل (/doctor/review/<id>)
# =========================================================================
@doctor.route('/review/<int:analysis_id>', methods=['POST'])
@handle_errors
@login_required
@validate_required_fields(['notes', 'status'])
def review_analysis(analysis_id):
    """يقوم الطبيب/المدير بإضافة ملاحظات على تحليل معين."""
    analysis = AnalysisResult.query.get_or_404(analysis_id)
    data = request.get_json()
    
    notes = data.get('notes', '').strip()
    status = data.get('status', 'reviewed').strip()
    
    # التحقق من صحة البيانات
    if not notes or len(notes) < 5:
        raise ValueError('الملاحظات يجب أن تكون 5 أحرف على الأقل')
    
    if len(notes) > 5000:
        raise ValueError('الملاحظات كبيرة جداً (الحد الأقصى: 5000 حرف)')
    
    if not AnalysisResult.is_valid_status(status):
        raise ValueError(f'حالة غير صالحة: {status}')
    
    try:
        # حفظ الحالة السابقة
        previous_status = analysis.review_status
        
        # تحديث البيانات
        analysis.doctor_id = current_user.id
        analysis.doctor_notes = notes
        analysis.review_status = status
        
        db.session.commit()
        
        # تسجيل التغيير في السجل
        history = AnalysisHistory(
            analysis_id=analysis.id,
            previous_status=previous_status,
            new_status=status,
            changed_by_id=current_user.id,
            change_reason=notes[:100]  # أول 100 حرف من الملاحظات
        )
        db.session.add(history)
        
        # إخطار المريض
        patient_notification = Notification(
            user_id=analysis.user_id,
            notification_type='ANALYSIS_REVIEWED',
            message=f'تم مراجعة تحليلك بواسطة الدكتور {current_user.username}',
            related_analysis_id=analysis.id
        )
        db.session.add(patient_notification)
        
        # تسجيل أمني
        AuditLogger.log_event(
            'ANALYSIS_REVIEWED',
            current_user.id,
            {
                'analysis_id': analysis.id,
                'previous_status': previous_status,
                'new_status': status,
                'patient': analysis.uploader.username
            },
            'INFO'
        )
        
        db.session.commit()
        
        logger.info(f'تم مراجعة التحليل: ID={analysis.id}, Doctor={current_user.username}, Status={status}')
        
        response, code = APIResponse.success(
            data={
                'analysis_id': analysis.id,
                'reviewer': current_user.username,
                'status': status,
                'updated_at': analysis.updated_at.isoformat()
            },
            message='تم تحديث مراجعة التحليل بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'خطأ في مراجعة التحليل: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 5. إحصائيات الطبيب (/doctor/stats)
# =========================================================================
@doctor.route('/stats', methods=['GET'])
@handle_errors
@login_required
def doctor_stats():
    """الحصول على إحصائيات الطبيب."""
    try:
        total_reviewed = AnalysisResult.query.filter_by(doctor_id=current_user.id).count()
        reviewed_status = AnalysisResult.query.filter_by(
            doctor_id=current_user.id,
            review_status='reviewed'
        ).count()
        rejected_status = AnalysisResult.query.filter_by(
            doctor_id=current_user.id,
            review_status='rejected'
        ).count()
        
        pending_analyses = AnalysisResult.query.filter_by(review_status='pending').count()
        
        # إحصائيات النتائج
        pneumonia_count = AnalysisResult.query.filter_by(
            doctor_id=current_user.id,
            model_result='PNEUMONIA'
        ).count()
        
        response, code = APIResponse.success(
            data={
                'total_reviewed': total_reviewed,
                'reviewed': reviewed_status,
                'rejected': rejected_status,
                'pending_in_system': pending_analyses,
                'pneumonia_cases': pneumonia_count
            },
            message='تم جلب الإحصائيات بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f'خطأ في جلب الإحصائيات: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 6. تقرير معين (/doctor/report/<id>)
# =========================================================================
@doctor.route('/report/<int:analysis_id>', methods=['GET'])
@handle_errors
@login_required
def generate_report(analysis_id):
    """الحصول على تقرير مفصل عن تحليل معين."""
    analysis = AnalysisResult.query.get_or_404(analysis_id)
    
    # التحقق من الصلاحيات
    is_owner = analysis.user_id == current_user.id
    is_reviewer = analysis.doctor_id == current_user.id
    is_admin = current_user.is_admin()
    
    if not (is_owner or is_reviewer or is_admin):
        raise PermissionError('لا توجد صلاحية للوصول إلى هذا التقرير')
    
    response, code = APIResponse.success(
        data=analysis.to_dict(include_paths=is_owner or is_reviewer or is_admin),
        message='تم جلب التقرير بنجاح'
    )
    return jsonify(response), code


# =========================================================================
# 7. مسار عرض سجل التغييرات (/doctor/analysis/<id>/history)
# =========================================================================
@doctor.route('/analysis/<int:analysis_id>/history', methods=['GET'])
@handle_errors
@login_required
def get_analysis_history(analysis_id):
    """الحصول على سجل التغييرات والمراجعات للتحليل."""
    analysis = AnalysisResult.query.get_or_404(analysis_id)
    
    # التحقق من الصلاحيات
    is_owner = analysis.user_id == current_user.id
    is_reviewer = analysis.doctor_id == current_user.id
    is_admin = current_user.is_admin()
    
    if not (is_owner or is_reviewer or is_admin):
        raise PermissionError('لا توجد صلاحية للوصول إلى السجل')
    
    try:
        history_records = AnalysisHistory.query.filter_by(
            analysis_id=analysis_id
        ).order_by(AnalysisHistory.changed_at.desc()).all()
        
        history_data = [record.to_dict() for record in history_records]
        
        response, code = APIResponse.success(
            data={
                'analysis_id': analysis_id,
                'history': history_data,
                'total_changes': len(history_data)
            },
            message='سجل التغييرات'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching analysis history: {e}", exc_info=True)
        response, code = APIResponse.error('خطأ في جلب السجل', 500, 'HISTORY_ERROR')
        return jsonify(response), code