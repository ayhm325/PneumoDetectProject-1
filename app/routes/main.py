from flask import Blueprint, render_template, redirect, url_for, request, current_app, jsonify, abort
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash
from app.models import User
from app import csrf
from app.utils import APIResponse, handle_errors, sanitize_input, AuditLogger

# إنشاء Blueprint باسم 'main'
main = Blueprint('main', __name__)


# ================================
#   الصفحة الرئيسية
# ================================
@main.route('/')
def index():
    return render_template('index.html')


# ================================
#   صفحات المصادقة (Auth Pages)
# ================================
@main.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login_page():
    """عرض صفحة تسجيل الدخول أو معالجة POST requests من form submissions."""
    try:
        if request.method == 'GET':
            return render_template('login.html')
        
        # Handle form/query parameter submissions (POST)
        # Try to get credentials from JSON first, then from form data
        if request.is_json:
            data = request.get_json() or {}
            username = data.get('username', '').strip()
            password = data.get('password', '')
            remember_me = data.get('remember_me', False)
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me', False)
        
        if isinstance(remember_me, str):
            remember_me = remember_me.lower() in ['on', 'true', '1', 'yes']
        
        # Query user from database
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember_me)
            
            # Redirect to role-specific page
            redirect_url = None
            if user.role == 'doctor':
                redirect_url = '/doctor'
            elif user.role == 'patient':
                redirect_url = '/patient'
            elif user.role == 'admin':
                redirect_url = '/admin'
            else:
                redirect_url = '/'
            
            return redirect(redirect_url)
        else:
            # Re-show login page with error message
            return render_template('login.html', error='فشل تسجيل الدخول - تحقق من بيانات المستخدم')
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return render_template('login.html', error=f'خطأ: {str(e)}')


@main.route('/register')
def register_page():
    """عرض صفحة التسجيل."""
    return render_template('register.html')


# ================================
#   صفحات المستخدمين بحسب الدور
# ================================
@main.route('/doctor')
@login_required
def doctor_page():
    """عرض لوحة الطبيب."""
    if current_user.role != 'doctor':
        return redirect(url_for('main.index'))
    return render_template('doctor.html')


@main.route('/patient')
@login_required
def patient_page():
    """عرض لوحة المريض."""
    if current_user.role not in ['patient', 'admin']:
        abort(403)
    return render_template('patient.html', username=current_user.username)


@main.route('/patient/analysis/<int:analysis_id>')
@login_required
def patient_analysis_details(analysis_id):
    """عرض تفاصيل التحليل."""
    from app.models import AnalysisResult
    
    if current_user.role not in ['patient', 'admin']:
        abort(403)
    
    analysis = AnalysisResult.query.get(analysis_id)
    if not analysis:
        abort(404)
    
    # التحقق من ملكية التحليل
    # المرضى يمكنهم رؤية تحليلاتهم فقط، والمديرون يمكنهم رؤية كل شيء
    if analysis.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    # Return JSON with analysis details
    return jsonify({
        'id': analysis.id,
        'filename': analysis.filename,
        'result': analysis.result,
        'confidence': float(analysis.confidence) if analysis.confidence else 0,
        'uploaded_at': analysis.uploaded_at.isoformat() if analysis.uploaded_at else None,
        'doctor_notes': analysis.doctor_notes,
        'review_status': analysis.review_status,
        'reviewed_by': analysis.reviewed_by,
        'original_image_url': f'/api/uploads/{analysis.id}/original',
        'saliency_map_url': f'/api/uploads/{analysis.id}/saliency'
    })


@main.route('/admin')
@login_required
def admin_page():
    """عرض لوحة المدير."""
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    return render_template('admin.html')


# ================================
#   صفحات إضافية
# ================================
@main.route('/forgot-password')
def forgot_password():
    """صفحة استرجاع كلمة المرور."""
    return render_template('forgot_password.html', error=None)


@main.route('/terms')
def terms():
    """صفحة شروط الخدمة."""
    return render_template('terms.html')


@main.route('/privacy')
def privacy():
    """صفحة سياسة الخصوصية."""
    return render_template('privacy.html')


# Client-side error logging endpoint (collects JS errors from browser)
@main.route('/api/log_client_error', methods=['POST'])
@handle_errors
def log_client_error():
    """Receive client-side JavaScript errors for diagnostics."""
    try:
        data = request.get_json(silent=True) or {}
        
        # التحقق من البيانات المطلوبة
        if not data.get('message'):
            response, code = APIResponse.error('رسالة الخطأ مطلوبة', 400, 'MISSING_MESSAGE')
            return jsonify(response), code
        
        # تنظيف البيانات
        message = sanitize_input(data.get('message', '')[:200], 'text')
        stack = sanitize_input(data.get('stack', '')[:2000], 'text')
        page_url = sanitize_input(data.get('url', '')[:500], 'text')
        user_agent = sanitize_input(data.get('userAgent', '')[:500], 'text')
        extra = sanitize_input(data.get('extra', '')[:1000], 'text')
        
        # Associate with user if logged in
        user_id = None
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                user_id = current_user.id
        except Exception:
            user_id = None
        
        details = {
            'message': message,
            'stack': stack,
            'page_url': page_url,
            'user_agent': user_agent,
            'extra': extra
        }
        
        # Log at server side and create audit record if possible
        try:
            AuditLogger.log_event('CLIENT_ERROR', user_id, details, severity='WARNING')
            current_app.logger.warning(f"Client error reported by user={user_id} url={page_url} msg={message}")
        except Exception as e:
            current_app.logger.error(f"Failed to record client error: {e}")
        
        response, code = APIResponse.success(data={'received': True}, message='Client error logged')
        return jsonify(response), code
    except Exception as e:
        current_app.logger.error(f"Failed to log client error: {str(e)}")
        response, code = APIResponse.error('فشل تسجيل الخطأ', 500, 'LOG_ERROR')
        return jsonify(response), code