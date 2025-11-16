from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

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
@main.route('/login')
def login_page():
    """عرض صفحة تسجيل الدخول."""
    return render_template('login.html')


@main.route('/login.html')   # ⬅️ لإصلاح مشكلة طلب http://127.0.0.1:5000/login.html
def login_html():
    return render_template('login.html')


@main.route('/register')
def register_page():
    """عرض صفحة التسجيل."""
    return render_template('register.html')


@main.route('/register.html')  # ⬅️ لتفعيل /register.html أيضًا
def register_html():
    return render_template('register.html')


# ================================
#   صفحات المستخدمين بحسب الدور
# ================================
@main.route('/doctor')
@login_required
def doctor_page():
    """عرض لوحة الطبيب."""
    if not current_user.is_doctor():
        return redirect(url_for('main.index'))
    return render_template('doctor.html')


@main.route('/patient')
@login_required
def patient_page():
    """عرض لوحة المريض."""
    if current_user.role not in ['patient', 'admin']:
        from flask import abort
        abort(403)
    return render_template('patient.html')


@main.route('/admin')
@login_required
def admin_page():
    """عرض لوحة المدير."""
    if not current_user.is_admin():
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
