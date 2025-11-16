import os
import io
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, url_for, send_from_directory, send_file
from flask_login import login_required, current_user
from PIL import Image
from werkzeug.utils import secure_filename

from app import db
from app.models import AnalysisResult, User, Notification, AnalysisHistory
from app.ml.processor import MLProcessor
from app.utils import APIResponse, handle_errors, save_file_securely, get_file_path, ImageValidator, AuditLogger, NotificationSystem

logger = logging.getLogger(__name__)

analysis = Blueprint('analysis', __name__)

# Lazy ML processor to avoid heavy imports at app startup
ml_processor = None

def get_ml_processor(app=None):
    """Initialize and return a singleton MLProcessor, loading the model on first use."""
    global ml_processor
    if ml_processor is None:
        ml_processor = MLProcessor()
    # ensure model is loaded
    if not ml_processor.is_loaded:
        # try to load using app config if provided
        cfg_app = app or current_app
        model_repo = cfg_app.config.get('MODEL_REPO')
        if not model_repo:
            raise RuntimeError('MODEL_REPO not configured; cannot load ML model')
        hf_token = cfg_app.config.get('HF_TOKEN')
        ml_processor.load_model(model_repo, hf_token)
    return ml_processor


def load_ml_model(app):
    """تحميل نموذج ML عند بدء التطبيق."""
    try:
        model_repo = app.config['MODEL_REPO']
        hf_token = app.config.get('HF_TOKEN')
        ml_processor.load_model(model_repo, hf_token)
        logger.info('✅ تم تحميل نموذج ML بنجاح')
    except Exception as e:
        logger.error(f'❌ فشل تحميل نموذج ML: {e}', exc_info=True)


def allowed_file(filename):
    """التحقق من امتداد الملف."""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'gif'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# =========================================================================
# 1. تحليل مؤقت (للزوار)
# =========================================================================
@analysis.route('/analyze', methods=['POST'])
@handle_errors
def analyze():
    """تحليل صورة بدون حفظ (للزوار)."""
    # Accept common form keys 'file' or 'image' to be more tolerant of clients
    if 'file' not in request.files and 'image' not in request.files:
        logger.warning(
            "analyze(): missing file. request.files keys=%s, content_type=%s, content_length=%s",
            list(request.files.keys()), request.content_type, request.headers.get('Content-Length')
        )
        raise ValueError('لم يتم توفير ملف')

    file = request.files.get('file') or request.files.get('image')
    if file.filename == '':
        raise ValueError('لم يتم اختيار ملف')
    
    if not allowed_file(file.filename):
        raise ValueError('نوع ملف غير مدعوم. الملفات المدعومة: ' + 
                        ', '.join(current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png'})))
    
    try:
        # قراءة الصورة
        image_bytes = file.read()

        # التحقق من الملف
        if len(image_bytes) == 0:
            raise ValueError('الملف فارغ')

        # فتح الصورة والتحقق من صحتها
        # IMPORTANT: open the image first and validate using the original Image object
        # before converting to RGB. Converting creates a new Image with no `format`
        # which breaks ImageValidator (it checks image_pil.format).
        image_pil = Image.open(io.BytesIO(image_bytes))
        # Log PIL detected format/size for diagnostics
        logger.info('analyze(): opened image - format=%s, size=%s, mode=%s', image_pil.format, image_pil.size, image_pil.mode)
        image_pil = ImageValidator.validate(image_pil)
        image_pil = image_pil.convert('RGB')
        
        # تحليل الصورة مع معالجة الأخطاء الحرجة
        try:
            processor = get_ml_processor(current_app)
            analysis_data = processor.analyze_image(image_bytes)
            
        except RuntimeError as e:
            if 'CUDA' in str(e) or 'out of memory' in str(e).lower():
                logger.error(f'GPU memory exhausted: {str(e)}')
                AuditLogger.log_event(
                    'ML_GPU_ERROR',
                    current_user.id if current_user.is_authenticated else None,
                    {'image_size': len(image_bytes), 'error': str(e)},
                    'ERROR'
                )
                response, code = APIResponse.error(
                    'الموارد المتاحة غير كافية. يرجى المحاولة لاحقاً',
                    503,
                    'RESOURCE_EXHAUSTED'
                )
                return jsonify(response), code
            raise
        
        except Exception as e:
            logger.error(f'ML processing error: {str(e)}', exc_info=True)
            AuditLogger.log_event(
                'ML_PROCESSING_ERROR',
                current_user.id if current_user.is_authenticated else None,
                {'error': str(e)},
                'ERROR'
            )
            response, code = APIResponse.error(
                'فشل تحليل الصورة',
                500,
                'ANALYSIS_FAILED'
            )
            return jsonify(response), code
        
        # حساب خريطة الإبراز
        try:
            saliency_pil = processor.compute_saliency_map(image_pil)
            saliency_bytes = io.BytesIO()
            saliency_pil.save(saliency_bytes, format='JPEG')
            
            # حفظ خريطة الإبراز المؤقتة
            saliency_folder, saliency_filename = save_file_securely(
                saliency_bytes.getvalue(), 
                'temp_saliency',
                'jpg'
            )
            saliency_path = os.path.join(saliency_folder, saliency_filename).replace(os.sep, '/')
        except Exception as e:
            logger.warning(f'Saliency map generation failed: {str(e)}')
            saliency_path = None  # Continue without saliency map
        
        logger.info(f'تحليل ناجح: {analysis_data["result"]} (Confidence: {analysis_data["confidence"]}%)')
        
        # Ensure URL uses forward slashes (avoid Windows backslash in URLs)
        saliency_rel = os.path.join(saliency_folder, saliency_filename).replace(os.sep, '/') if saliency_path else None
        response, code = APIResponse.success(
            data={
                'result': analysis_data['result'],
                'confidence': analysis_data['confidence'],
                'explanation': analysis_data['explanation'],
                'saliency_url': url_for('analysis.serve_file', filename=saliency_rel, _external=True) if saliency_rel else None
            },
            message='تم التحليل بنجاح'
        )
        return jsonify(response), code
        
    except Exception as e:
        logger.error(f'خطأ غير متوقع في التحليل: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 2. تحليل وحفظ (للمسجلين)
# =========================================================================
@analysis.route('/analyze_and_save', methods=['POST'])
@login_required
@handle_errors
def analyze_and_save():
    """تحليل الصورة وحفظ النتيجة (للمستخدمين المسجلين فقط)."""
    # Accept both 'file' and 'image' form keys
    if 'file' not in request.files and 'image' not in request.files:
        logger.warning(
            "analyze_and_save(): missing file. request.files keys=%s, content_type=%s, content_length=%s",
            list(request.files.keys()), request.content_type, request.headers.get('Content-Length')
        )
        raise ValueError('لم يتم توفير ملف')

    file = request.files.get('file') or request.files.get('image')
    if file.filename == '':
        raise ValueError('لم يتم اختيار ملف')
    
    if not allowed_file(file.filename):
        raise ValueError('نوع ملف غير مدعوم')
    
    try:
        # قراءة الصورة
        image_bytes = file.read()

        if len(image_bytes) == 0:
            raise ValueError('الملف فارغ')

        # فتح الصورة والتحقق من صحتها
        image_pil = Image.open(io.BytesIO(image_bytes))
        logger.info('analyze_and_save(): opened image - format=%s, size=%s, mode=%s', image_pil.format, image_pil.size, image_pil.mode)
        image_pil = ImageValidator.validate(image_pil)
        image_pil = image_pil.convert('RGB')
        
        # تحليل الصورة (تأكد من تحميل النموذج عند الحاجة)
        processor = get_ml_processor(current_app)
        analysis_data = processor.analyze_image(image_bytes)
        
        # حفظ الصورة الأصلية
        img_folder, img_filename = save_file_securely(image_bytes, 'originals', 'jpg')
        image_path = os.path.join(img_folder, img_filename).replace(os.sep, '/')
        
        # حفظ خريطة الإبراز
        saliency_pil = processor.compute_saliency_map(image_pil)
        saliency_bytes = io.BytesIO()
        saliency_pil.save(saliency_bytes, format='JPEG')
        sal_folder, sal_filename = save_file_securely(
            saliency_bytes.getvalue(), 
            'saliency_maps',
            'jpg'
        )
        saliency_path = os.path.join(sal_folder, sal_filename).replace(os.sep, '/')
        
        # التحقق من صحة النتيجة
        if not AnalysisResult.is_valid_result(analysis_data['result']):
            raise ValueError(f'نتيجة غير صالحة: {analysis_data["result"]}')
        
        # حفظ في قاعدة البيانات
        result = AnalysisResult(
            user_id=current_user.id,
            model_result=analysis_data['result'],
            confidence=analysis_data['confidence'],
            image_path=image_path,
            saliency_path=saliency_path,
            review_status='pending'
        )
        
        db.session.add(result)
        db.session.commit()
        
        logger.info(f'تحليل محفوظ: ID={result.id}, User={current_user.username}, Result={analysis_data["result"]}')
        
        # Build URLs with forward slashes to avoid Windows backslash encoding in URLs
        image_rel = os.path.join(img_folder, img_filename).replace(os.sep, '/')
        saliency_rel = os.path.join(sal_folder, sal_filename).replace(os.sep, '/')

        response, code = APIResponse.success(
            data={
                'analysis_id': result.id,
                'result': analysis_data['result'],
                'confidence': analysis_data['confidence'],
                'explanation': analysis_data['explanation'],
                'image_url': url_for('analysis.serve_file', filename=image_rel, _external=True),
                'saliency_url': url_for('analysis.serve_file', filename=saliency_rel, _external=True),
                'created_at': result.created_at.isoformat()
            },
            message='تم التحليل والحفظ بنجاح',
            code=201
        )
        return jsonify(response), code
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'خطأ في التحليل والحفظ: {str(e)}', exc_info=True)
        raise


# =========================================================================
# 3. الحصول على تفاصيل تحليل
# =========================================================================
@analysis.route('/analysis/<int:analysis_id>', methods=['GET'])
@handle_errors
def get_analysis(analysis_id):
    """الحصول على تفاصيل تحليل معين."""
    result = AnalysisResult.query.get_or_404(analysis_id)
    
    # التحقق من الصلاحيات
    if not current_user.is_authenticated:
        if result.review_status == 'pending':
            raise PermissionError('لا توجد صلاحية للوصول إلى هذا التحليل')
    else:
        is_owner = result.user_id == current_user.id
        is_doctor = current_user.is_doctor() and result.doctor_id == current_user.id
        
        if not (is_owner or is_doctor or current_user.is_admin()):
            raise PermissionError('لا توجد صلاحية للوصول إلى هذا التحليل')
    
    response, code = APIResponse.success(
        data=result.to_dict(),
        message='تم جلب التحليل'
    )
    return jsonify(response), code


# =========================================================================
# 4. خدمة الملفات (آمنة)
# =========================================================================
@analysis.route('/uploads/<path:filename>')
def serve_file(filename):
    """خدمة الملفات بأمان (منع Path Traversal)."""
    try:
        full_path = get_file_path('', filename)
        folder = os.path.dirname(full_path).replace(
            os.path.abspath(current_app.config['UPLOAD_FOLDER']), ''
        ).lstrip(os.sep)

        # Diagnostic logging: absolute path and existence check
        try:
            abs_upload = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
            logger.info('serve_file(): requested filename=%s', filename)
            logger.info('serve_file(): full_path=%s, exists=%s', full_path, os.path.exists(full_path))
            logger.info('serve_file(): upload_folder=%s', abs_upload)
        except Exception as _ex:
            logger.debug('serve_file(): logging diagnostic failed: %s', _ex)

        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
        
    except FileNotFoundError:
        response, code = APIResponse.error('الملف غير موجود', 404, 'FILE_NOT_FOUND')
        return jsonify(response), code
    except ValueError as e:
        response, code = APIResponse.error(str(e), 403, 'ACCESS_DENIED')
        return jsonify(response), code


# =========================================================================
# 5. حذف تحليل
# =========================================================================
@analysis.route('/analysis/<int:analysis_id>', methods=['DELETE'])
@login_required
@handle_errors
def delete_analysis(analysis_id):
    """حذف تحليل (صاحبه فقط أو مدير)."""
    result = AnalysisResult.query.get_or_404(analysis_id)
    
    # التحقق من الصلاحيات
    is_owner = result.user_id == current_user.id
    is_admin = current_user.is_admin()
    
    if not (is_owner or is_admin):
        raise PermissionError('لا توجد صلاحية لحذف هذا التحليل')
    
    try:
        # حذف الملفات
        for path in [result.image_path, result.saliency_path]:
            if path:
                try:
                    full_path = get_file_path('', path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logger.info(f'تم حذف الملف: {full_path}')
                except Exception as e:
                    logger.warning(f'فشل حذف الملف: {path} - {str(e)}')
        
        # حذف السجل من قاعدة البيانات
        db.session.delete(result)
        db.session.commit()
        
        logger.info(f'تم حذف التحليل: ID={analysis_id}')
        
        response, code = APIResponse.success(message='تم حذف التحليل بنجاح')
        return jsonify(response), code
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'خطأ في حذف التحليل: {str(e)}', exc_info=True)
        raise


# =========================================================================
# Download analysis files (image + saliency)
# =========================================================================
@analysis.route('/analysis/<int:analysis_id>/download', methods=['GET'])
@handle_errors
@login_required
def download_analysis_files(analysis_id):
    """Download the original image and saliency map as a ZIP archive.

    Permissions: owner (uploader), reviewer (doctor), or admin.
    """
    result = AnalysisResult.query.get_or_404(analysis_id)

    # permission check similar to get_analysis
    if not current_user.is_authenticated:
        response, code = APIResponse.error('غير مصرح - يتطلب تسجيل الدخول', 401, 'UNAUTHORIZED')
        return jsonify(response), code

    is_owner = result.user_id == current_user.id
    is_reviewer = current_user.is_doctor() and result.doctor_id == current_user.id
    is_admin = current_user.is_admin()

    if not (is_owner or is_reviewer or is_admin):
        response, code = APIResponse.error('لا توجد صلاحية للوصول إلى هذا الملف', 403, 'FORBIDDEN')
        return jsonify(response), code

    files_to_add = []
    try:
        # resolve full paths safely
        if result.image_path:
            try:
                full_image = get_file_path('', result.image_path)
                if os.path.exists(full_image):
                    files_to_add.append(full_image)
            except Exception:
                pass

        if result.saliency_path:
            try:
                full_sal = get_file_path('', result.saliency_path)
                if os.path.exists(full_sal):
                    files_to_add.append(full_sal)
            except Exception:
                pass

        if not files_to_add:
            response, code = APIResponse.error('لا توجد ملفات للتحميل', 404, 'FILES_NOT_FOUND')
            return jsonify(response), code

        # If only one file, send it directly
        if len(files_to_add) == 1:
            return send_file(files_to_add[0], as_attachment=True)

        # Otherwise create an in-memory ZIP
        zip_buffer = io.BytesIO()
        import zipfile

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in files_to_add:
                zf.write(path, arcname=os.path.basename(path))

        zip_buffer.seek(0)
        filename = f'analysis_{analysis_id}_files.zip'
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f'Error creating download for analysis {analysis_id}: {e}', exc_info=True)
        response, code = APIResponse.error('فشل التحضير للتحميل', 500, 'DOWNLOAD_ERROR')
        return jsonify(response), code


# =========================================================================
# 5. إخطار الأطباء بتحليل جديد ينتظر المراجعة
# =========================================================================
def notify_doctors_for_analysis(analysis_id):
    """إرسال إخطارات للأطباء عن تحليل جديد."""
    try:
        analysis = AnalysisResult.query.get(analysis_id)
        if not analysis:
            return False
        
        # الحصول على جميع الأطباء النشطين
        doctors = User.query.filter_by(role='doctor', is_active=True).all()
        
        message_ar = f"تحليل جديد في انتظار المراجعة - المريض: {analysis.uploader.username}"
        message_en = f"New analysis pending review - Patient: {analysis.uploader.username}"
        
        for doctor in doctors:
            notification = Notification(
                user_id=doctor.id,
                notification_type='ANALYSIS_READY',
                message=message_ar,
                related_analysis_id=analysis_id
            )
            db.session.add(notification)
        
        db.session.commit()
        logger.info(f"Doctors notified for analysis {analysis_id}")
        return True
    except Exception as e:
        logger.error(f"Error notifying doctors: {e}", exc_info=True)
        return False


# =========================================================================
# 6. إخطار المريض عند مراجعة التحليل
# =========================================================================
def notify_patient_review_complete(analysis_id, doctor_id):
    """إخطار المريض عند انتهاء الطبيب من المراجعة."""
    try:
        analysis = AnalysisResult.query.get(analysis_id)
        doctor = User.query.get(doctor_id)
        
        if not analysis or not doctor:
            return False
        
        message = f"تم مراجعة تحليلك بواسطة الدكتور {doctor.username}"
        
        notification = Notification(
            user_id=analysis.user_id,
            notification_type='ANALYSIS_REVIEWED',
            message=message,
            related_analysis_id=analysis_id
        )
        db.session.add(notification)
        db.session.commit()
        
        logger.info(f"Patient {analysis.uploader.username} notified for analysis review")
        return True
    except Exception as e:
        logger.error(f"Error notifying patient: {e}", exc_info=True)
        return False


# =========================================================================
# 7. نقطة نهاية جديدة: الحصول على الإخطارات الخاصة بالمستخدم
# =========================================================================
@analysis.route('/notifications', methods=['GET'])
@handle_errors
@login_required
def get_user_notifications():
    """الحصول على إخطارات المستخدم."""
    try:
        page = request.args.get('page', 1, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        from app.utils import paginate_query
        
        query = Notification.query.filter_by(user_id=current_user.id)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        pagination = paginate_query(query.order_by(Notification.created_at.desc()), page)
        
        notifications_data = [n.to_dict() for n in pagination['items']]
        pagination['items'] = notifications_data
        
        response, code = APIResponse.success(
            data=pagination,
            message='إخطاراتك'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}", exc_info=True)
        response, code = APIResponse.error('خطأ في جلب الإخطارات', 500, 'NOTIFICATION_ERROR')
        return jsonify(response), code


# =========================================================================
# 8. نقطة نهاية: وضع علامة على إخطار كمقروء
# =========================================================================
@analysis.route('/notifications/<notification_id>/read', methods=['PUT'])
@handle_errors
@login_required
def mark_notification_read(notification_id):
    """وضع علامة على إخطار كمقروء."""
    try:
        notification = Notification.query.get_or_404(notification_id)
        
        # التحقق من الملكية
        if notification.user_id != current_user.id:
            response, code = APIResponse.error('غير مصرح', 403, 'FORBIDDEN')
            return jsonify(response), code
        
        notification.mark_as_read()
        db.session.commit()
        
        response, code = APIResponse.success(
            data=notification.to_dict(),
            message='تم وضع علامة على الإخطار كمقروء'
        )
        return jsonify(response), code
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}", exc_info=True)
        response, code = APIResponse.error('خطأ في تحديث الإخطار', 500, 'UPDATE_ERROR')
        return jsonify(response), code