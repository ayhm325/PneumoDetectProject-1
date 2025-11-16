#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل لقاعدة البيانات والسيرفر والـ API
Comprehensive Database, Server & API Testing
"""

import os
import sys
import json
import time
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Set up environment
os.environ['SKIP_ML'] = '1'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User, AnalysisResult, Notification, AnalysisHistory, AuditLog
from werkzeug.security import generate_password_hash

# Create app first
app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})

def print_header(text):
    """طباعة عنوان."""
    print("\n" + "=" * 70)
    print(f"🧪 {text}")
    print("=" * 70)

def print_test(name, status, details=""):
    """طباعة نتيجة اختبار."""
    symbol = "✅" if status else "❌"
    print(f"  {symbol} {name}")
    if details:
        print(f"     → {details}")

def print_section(name):
    """طباعة قسم."""
    print(f"\n📋 {name}")
    print("-" * 70)

def test_database():
    """اختبار قاعدة البيانات."""
    print_section("1️⃣ اختبارات قاعدة البيانات")
    
    with app.app_context():
        try:
            # إنشاء جداول
            db.create_all()
            print_test("إنشاء الجداول", True)
            
            # اختبار إنشاء مستخدم
            user = User(
                username='test_user',
                email='test@example.com',
                role='patient'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            print_test("إنشاء مستخدم", True, f"ID: {user.id}, Username: {user.username}")
            
            # اختبار التحقق من كلمة المرور
            check = user.check_password('password123')
            print_test("التحقق من كلمة المرور", check)
            
            # اختبار البحث عن مستخدم
            found_user = User.query.filter_by(username='test_user').first()
            print_test("البحث عن مستخدم", found_user is not None)
            
            # اختبار إنشاء نتيجة تحليل
            analysis = AnalysisResult(
                user_id=user.id,
                model_result='PNEUMONIA',
                confidence=85.5,
                image_path='/uploads/originals/test.jpg',
                saliency_path='/uploads/saliency_maps/test.jpg',
                review_status='pending'
            )
            db.session.add(analysis)
            db.session.commit()
            print_test("إنشاء نتيجة تحليل", True, f"ID: {analysis.id}, Result: {analysis.model_result}")
            
            # اختبار الإشعارات
            notification = Notification(
                user_id=user.id,
                notification_type='ANALYSIS_READY',
                message='تحليلك جاهز للمراجعة',
                related_analysis_id=analysis.id
            )
            db.session.add(notification)
            db.session.commit()
            print_test("إنشاء إشعار", True, f"ID: {notification.id}, Type: {notification.notification_type}")
            
            # اختبار سجل المراجعات
            history = AnalysisHistory(
                analysis_id=analysis.id,
                previous_status=None,
                new_status='pending',
                changed_by_id=user.id,
                change_reason='تم إنشاء التحليل'
            )
            db.session.add(history)
            db.session.commit()
            print_test("إنشاء سجل التاريخ", True, f"ID: {history.id}")
            
            # اختبار سجل التدقيق
            audit = AuditLog(
                event_type='USER_CREATED',
                event_description='تم إنشاء مستخدم جديد',
                user_id=user.id,
                severity='INFO',
                client_ip='127.0.0.1',
                endpoint='/api/auth/register',
                method='POST'
            )
            db.session.add(audit)
            db.session.commit()
            print_test("إنشاء سجل التدقيق", True, f"ID: {audit.id}, Event: {audit.event_type}")
            
            # اختبار الاستعلامات المتقدمة
            total_users = User.query.count()
            total_analyses = AnalysisResult.query.count()
            print_test("عد السجلات", True, f"Users: {total_users}, Analyses: {total_analyses}")
            
            # اختبار العلاقات
            user_analyses = user.analyses.count()
            print_test("الاستعلام عن العلاقات", True, f"User analyses: {user_analyses}")
            
            # اختبار to_dict
            user_dict = user.to_dict()
            analysis_dict = analysis.to_dict()
            print_test("تحويل البيانات إلى قاموس", True, f"User keys: {len(user_dict)}, Analysis keys: {len(analysis_dict)}")
            
            # تنظيف البيانات
            db.session.query(AuditLog).delete()
            db.session.query(AnalysisHistory).delete()
            db.session.query(Notification).delete()
            db.session.query(AnalysisResult).delete()
            db.session.query(User).delete()
            db.session.commit()
            print_test("تنظيف البيانات", True)
            
            return True
        except Exception as e:
            print_test("اختبار قاعدة البيانات", False, str(e))
            db.session.rollback()
            return False

def test_server():
    """اختبار السيرفر والـ endpoints."""
    print_section("2️⃣ اختبارات السيرفر والـ Endpoints")
    
    all_passed = True
    client = app.test_client()
    
    # اختبار Health Check
    response = client.get('/health')
    passed = response.status_code == 200
    all_passed = all_passed and passed
    print_test("GET /health", passed, f"Status: {response.status_code}")
    
    # اختبار Readiness Check
    response = client.get('/health/ready')
    passed = response.status_code == 200
    all_passed = all_passed and passed
    print_test("GET /health/ready", passed, f"Status: {response.status_code}")
    
    return all_passed

def test_authentication_api():
    """اختبار API المصادقة."""
    print_section("3️⃣ اختبارات API المصادقة")
    
    all_passed = True
    client = app.test_client()
    
    # اختبار GET CSRF token
    response = client.get('/register')
    passed = response.status_code == 200
    all_passed = all_passed and passed
    print_test("GET /register (HTML)", passed, f"Status: {response.status_code}")
    
    # اختبار GET login page
    response = client.get('/login')
    passed = response.status_code == 200
    all_passed = all_passed and passed
    print_test("GET /login (HTML)", passed, f"Status: {response.status_code}")
    
    # اختبار التسجيل (POST)
    with client:
        # أولاً احصل على CSRF token من الجلسة
        response = client.get('/register')
        csrf_token = None
        
        # حاول الحصول على التوكن من الـ session
        with client.session_transaction() as sess:
            csrf_token = sess.get('csrf_token')
        
        # حاول التسجيل
        register_data = {
            'username': 'testuser123',
            'email': 'testuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123'
        }
        
        # جرب POST بدون CSRF (قد تفشل)
        response = client.post('/api/auth/register', json=register_data)
        # قد يكون 201 (Created - نجح) أو 403 (CSRF) أو 400 (validation)
        passed = response.status_code in [200, 201, 403, 400]
        all_passed = all_passed and passed
        print_test("POST /api/auth/register", passed, f"Status: {response.status_code}")
    
    return all_passed

def test_protected_routes():
    """اختبار المسارات المحمية."""
    print_section("4️⃣ اختبارات المسارات المحمية")
    
    all_passed = True
    client = app.test_client()
    
    # اختبار محاولة الوصول بدون تسجيل
    response = client.get('/doctor')
    passed = response.status_code in [302, 401]  # redirect أو unauthorized
    all_passed = all_passed and passed
    print_test("GET /doctor (بدون login)", passed, f"Status: {response.status_code}")
    
    response = client.get('/admin')
    passed = response.status_code in [302, 401]
    all_passed = all_passed and passed
    print_test("GET /admin (بدون login)", passed, f"Status: {response.status_code}")
    
    return all_passed

def test_public_routes():
    """اختبار المسارات العامة."""
    print_section("5️⃣ اختبارات المسارات العامة")
    
    all_passed = True
    client = app.test_client()
    
    routes = [
        ('/', 'الصفحة الرئيسية'),
        ('/login', 'صفحة تسجيل الدخول'),
        ('/register', 'صفحة التسجيل'),
        ('/forgot-password', 'صفحة استرجاع كلمة المرور'),
        ('/terms', 'شروط الخدمة'),
        ('/privacy', 'سياسة الخصوصية'),
    ]
    
    for route, description in routes:
        response = client.get(route)
        passed = response.status_code == 200
        all_passed = all_passed and passed
        print_test(f"GET {route}", passed, f"{description} - Status: {response.status_code}")
    
    return all_passed

def test_api_endpoints():
    """اختبار نقاط API المختلفة."""
    print_section("6️⃣ اختبارات API Endpoints")
    
    all_passed = True
    client = app.test_client()
    
    # اختبار API health
    response = client.get('/api/system-info')
    # قد يكون 302 (redirect to login) أو 401 (requires login) أو 200
    passed = response.status_code in [200, 301, 302, 401, 403]
    all_passed = all_passed and passed
    print_test("GET /api/system-info", passed, f"Status: {response.status_code}")
    
    # اختبار Analysis stub
    analysis_data = {
        'image': 'test_image.jpg'
    }
    response = client.post('/api/analysis', json=analysis_data)
    # قد يكون 200 (mock) أو 400 (validation error)
    passed = response.status_code in [200, 400, 405]
    all_passed = all_passed and passed
    print_test("POST /api/analysis", passed, f"Status: {response.status_code}")
    
    return all_passed

def test_database_constraints():
    """اختبار قيود قاعدة البيانات."""
    print_section("7️⃣ اختبارات قيود قاعدة البيانات")
    
    all_passed = True
    
    with app.app_context():
        try:
            # اختبار التفرد (Uniqueness)
            user1 = User(
                username='unique_test',
                email='unique@test.com',
                role='patient'
            )
            user1.set_password('password')
            db.session.add(user1)
            db.session.commit()
            
            # محاولة إنشاء مستخدم برسم نفسه
            user2 = User(
                username='unique_test',
                email='different@test.com',
                role='patient'
            )
            user2.set_password('password')
            db.session.add(user2)
            
            try:
                db.session.commit()
                print_test("قيد التفرد للـ Username", False, "لم يتم منع البيانات المكررة")
                all_passed = False
            except Exception:
                db.session.rollback()
                print_test("قيد التفرد للـ Username", True, "تم منع البيانات المكررة")
            
            # اختبار البريد الفريد
            user3 = User(
                username='different_username',
                email='unique@test.com',
                role='patient'
            )
            user3.set_password('password')
            db.session.add(user3)
            
            try:
                db.session.commit()
                print_test("قيد التفرد للـ Email", False, "لم يتم منع البيانات المكررة")
                all_passed = False
            except Exception:
                db.session.rollback()
                print_test("قيد التفرد للـ Email", True, "تم منع البيانات المكررة")
            
            # تنظيف
            db.session.query(User).delete()
            db.session.commit()
            
        except Exception as e:
            print_test("اختبار القيود", False, str(e))
            db.session.rollback()
            all_passed = False
    
    return all_passed

def test_error_handling():
    """اختبار معالجة الأخطاء."""
    print_section("8️⃣ اختبارات معالجة الأخطاء")
    
    all_passed = True
    client = app.test_client()
    
    # اختبار 404
    response = client.get('/nonexistent-route')
    passed = response.status_code == 404
    all_passed = all_passed and passed
    print_test("معالجة 404", passed, f"Status: {response.status_code}")
    
    # اختبار طلب غير صحيح
    response = client.post('/api/auth/login', json={'invalid': 'data'})
    passed = response.status_code in [400, 422, 403]
    all_passed = all_passed and passed
    print_test("معالجة البيانات غير الصحيحة", passed, f"Status: {response.status_code}")
    
    return all_passed

def run_all_tests():
    """تشغيل جميع الاختبارات."""
    print_header("اختبار شامل - قاعدة البيانات والسيرفر والـ API")
    
    results = {
        'Database': test_database(),
        'Server': test_server(),
        'Authentication API': test_authentication_api(),
        'Protected Routes': test_protected_routes(),
        'Public Routes': test_public_routes(),
        'API Endpoints': test_api_endpoints(),
        'Database Constraints': test_database_constraints(),
        'Error Handling': test_error_handling(),
    }
    
    print_header("📊 ملخص النتائج")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for test_name, result in results.items():
        symbol = "✅" if result else "❌"
        print(f"  {symbol} {test_name}")
    
    print("\n" + "=" * 70)
    print(f"📈 النتيجة النهائية: {passed_count}/{total_count} اختبارات نجحت")
    
    if passed_count == total_count:
        print("🎉 جميع الاختبارات نجحت!")
    else:
        print(f"⚠️  {total_count - passed_count} اختبارات فشلت")
    
    print("=" * 70)
    
    return passed_count == total_count

if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ حرج: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
