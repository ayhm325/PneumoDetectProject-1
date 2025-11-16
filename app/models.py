from datetime import datetime
from flask_login import UserMixin
from app import db
import re
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

# =========================================================================
# 1. نموذج المستخدم (User)
# يستخدم Flask-Login لتسهيل إدارة الجلسات والمصادقة.
# =========================================================================

class User(UserMixin, db.Model):
    """
    يمثل المستخدمين في النظام (مريض، طبيب، مدير).
    
    الحقول:
    - id: معرف فريد للمستخدم
    - username: اسم المستخدم (فريد)
    - email: البريد الإلكتروني (فريد)
    - password_hash: Hash كلمة المرور
    - role: الدور (patient, doctor, admin)
    - is_active: حالة النشاط
    - created_at: تاريخ الإنشاء
    - updated_at: تاريخ آخر تحديث
    """
    __tablename__ = 'user'
    
    # المفاتيح الأساسية والفريدة
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # الدور والحالة
    role = db.Column(db.String(20), default='patient', nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # التواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # العلاقات
    analyses = db.relationship('AnalysisResult', foreign_keys='AnalysisResult.user_id', 
                               backref='uploader', lazy='dynamic', cascade='all, delete-orphan')
    reviewed_analyses = db.relationship('AnalysisResult', foreign_keys='AnalysisResult.doctor_id', 
                                       backref='reviewer', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def __str__(self):
        return self.username
    
    @staticmethod
    def validate_username(username):
        """التحقق من صحة اسم المستخدم."""
        if not username or len(username) < 3 or len(username) > 64:
            return False
        return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None
    
    @staticmethod
    def validate_email(email):
        """التحقق من صحة البريد الإلكتروني."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def is_doctor(self):
        """التحقق من كون المستخدم طبيب."""
        return self.role in ['doctor', 'admin']
    
    def is_admin(self):
        """التحقق من كون المستخدم مدير."""
        return self.role == 'admin'
    
    def is_patient(self):
        """التحقق من كون المستخدم مريض."""
        return self.role == 'patient'
    
    def to_dict(self):
        """تحويل المستخدم إلى قاموس."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

    def set_password(self, password):
        """Set password hash for the user."""
        if not password:
            raise ValueError('Password cannot be empty')
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check hashed password."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

# =========================================================================
# 2. نموذج نتائج التحليل (AnalysisResult)
# يستخدم لحفظ سجلات التحليل التي يطلبها المستخدمون المسجلون.
# =========================================================================

class AnalysisResult(db.Model):
    """
    يخزن تفاصيل كل عملية تحليل صورة بالأشعة السينية.
    
    الحقول:
    - id: معرف التحليل
    - user_id: معرف المريض الذي حمّل الصورة
    - doctor_id: معرف الطبيب الذي راجع التحليل
    - model_result: نتيجة النموذج (NORMAL/PNEUMONIA)
    - confidence: درجة الثقة (0-100)
    - image_path: مسار الصورة الأصلية
    - saliency_path: مسار خريطة الإبراز
    - created_at: وقت الإنشاء
    - updated_at: وقت آخر تحديث
    - review_status: حالة المراجعة (pending/reviewed/rejected)
    """
    __tablename__ = 'analysis_result'
    
    # المفاتيح الأساسية
    id = db.Column(db.Integer, primary_key=True)
    
    # المفاتيح الأجنبية
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    
    # نتائج التحليل
    model_result = db.Column(db.String(50), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    
    # مسارات الملفات
    image_path = db.Column(db.String(256), nullable=False)
    saliency_path = db.Column(db.String(256), nullable=True)
    
    # التواريخ والملاحظات
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # المراجعة
    doctor_notes = db.Column(db.Text, nullable=True)
    review_status = db.Column(db.String(50), default='pending', nullable=False, index=True)

    def __repr__(self):
        return f'<Analysis {self.id} - Result: {self.model_result} (Confidence: {self.confidence}%)>'
    
    def __str__(self):
        return f'Analysis #{self.id}'
    
    @staticmethod
    def is_valid_result(result):
        """التحقق من صحة نتيجة التحليل."""
        return result in ['NORMAL', 'PNEUMONIA']
    
    @staticmethod
    def is_valid_status(status):
        """التحقق من صحة حالة المراجعة."""
        return status in ['pending', 'reviewed', 'rejected']
    
    def is_pending_review(self):
        """التحقق من انتظار المراجعة."""
        return self.review_status == 'pending'
    
    def is_reviewed(self):
        """التحقق من تمت المراجعة."""
        return self.review_status == 'reviewed'
    
    def is_rejected(self):
        """التحقق من رفض المراجعة."""
        return self.review_status == 'rejected'
    
    def to_dict(self, include_paths=True):
        """تحويل التحليل إلى قاموس."""
        data = {
            'id': self.id,
            'model_result': self.model_result,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'review_status': self.review_status,
            'doctor_notes': self.doctor_notes,
            'patient_username': self.uploader.username if self.uploader else None,
            'doctor_username': self.reviewer.username if self.reviewer else None
        }
        
        if include_paths:
            data['image_path'] = self.image_path
            data['saliency_path'] = self.saliency_path
        
        return data


# =========================================================================
# 3. نموذج الإشعارات (Notification)
# نظام متقدم للإشعارات والتنبيهات
# =========================================================================

class Notification(db.Model):
    """نموذج الإشعارات والتنبيهات."""
    __tablename__ = 'notification'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # نوع الإشعار
    notification_type = db.Column(db.String(50), nullable=False)  # ANALYSIS_READY, REVIEWED, etc.
    message = db.Column(db.Text, nullable=False)
    
    # الربط بالبيانات ذات الصلة
    related_analysis_id = db.Column(db.Integer, db.ForeignKey('analysis_result.id'), nullable=True)
    
    # الحالة
    is_read = db.Column(db.Boolean, default=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # التواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # العلاقات
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    related_analysis = db.relationship('AnalysisResult', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id} - Type: {self.notification_type}>'
    
    def mark_as_read(self):
        """وضع علامة على الإشعار كمقروء."""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def to_dict(self):
        """تحويل الإشعار إلى قاموس."""
        return {
            'id': self.id,
            'type': self.notification_type,
            'message': self.message,
            'is_read': self.is_read,
            'related_analysis_id': self.related_analysis_id,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }


# =========================================================================
# 4. نموذج نسخة احتياطية من التحليلات (AnalysisHistory)
# لتتبع التغييرات والمراجعات
# =========================================================================

class AnalysisHistory(db.Model):
    """تاريخ وتطور التحليلات والمراجعات."""
    __tablename__ = 'analysis_history'
    
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis_result.id'), nullable=False, index=True)
    
    # تتبع التغييرات
    previous_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # الملاحظات
    change_reason = db.Column(db.Text, nullable=True)
    
    # التاريخ
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # العلاقات
    analysis = db.relationship('AnalysisResult', backref=db.backref('history', lazy='dynamic', cascade='all, delete-orphan'))
    changed_by = db.relationship('User', backref='analysis_changes')
    
    def __repr__(self):
        return f'<AnalysisHistory {self.id} - {self.previous_status} -> {self.new_status}>'
    
    def to_dict(self):
        """تحويل السجل إلى قاموس."""
        return {
            'id': self.id,
            'analysis_id': self.analysis_id,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by.username if self.changed_by else None,
            'reason': self.change_reason,
            'changed_at': self.changed_at.isoformat()
        }


# =========================================================================
# 5. نموذج سجل المراجعات (AuditLog)
# لتخزين أحداث الأمان والمراجعة بشكل دائم
# =========================================================================

class AuditLog(db.Model):
    """سجل المراجعات والأحداث الأمنيّة."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    event_description = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    details = db.Column(db.Text, nullable=True)  # JSON-encoded details
    severity = db.Column(db.String(20), nullable=False, default='INFO', index=True)

    # معلومات العميل
    client_ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    endpoint = db.Column(db.String(256), nullable=True)
    method = db.Column(db.String(16), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # العلاقات
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.id} - {self.event_type}>'

    def to_dict(self):
        """تحويل سجل المراجعة إلى قاموس (يفك JSON للحقل details إن أمكن)."""
        try:
            import json
            details_obj = json.loads(self.details) if self.details else {}
        except Exception:
            details_obj = self.details

        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_description': self.event_description,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None,
            'details': details_obj,
            'severity': self.severity,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'endpoint': self.endpoint,
            'method': self.method,
            'created_at': self.created_at.isoformat()
        }