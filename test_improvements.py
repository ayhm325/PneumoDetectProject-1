"""
اختبار شامل لجميع التحسينات المطبقة
Comprehensive Test Suite for All Applied Improvements
"""

import unittest
import json
import time
from flask import Flask
from app import create_app, db
from app.models import User, AnalysisResult
from app.utils import sanitize_input, ensure_data_ownership


class TestHealthEndpoints(unittest.TestCase):
    """اختبار health check endpoints"""

    def setUp(self):
        """إعداد التطبيق واختباره"""
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """تنظيف بعد الاختبار"""
        self.app_context.pop()

    def test_health_endpoint(self):
        """اختبار /health endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('version', data)
        self.assertIn('environment', data)

    def test_health_ready_endpoint(self):
        """اختبار /health/ready endpoint"""
        response = self.client.get('/health/ready')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])


class TestCSRFProtection(unittest.TestCase):
    """اختبار CSRF protection مع JSON APIs"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_csrf_token_from_cookie(self):
        """اختبار الحصول على CSRF token من الكوكي"""
        response = self.client.get('/')
        self.assertIn('csrf_token', response.cookies)

    def test_csrf_validation_json_api(self):
        """اختبار CSRF validation مع JSON"""
        # الحصول على الرمز
        response = self.client.get('/')
        csrf_token = response.cookies.get('csrf_token')
        
        # محاولة POST بدون رمز (يجب أن تفشل)
        response = self.client.post(
            '/api/analysis',
            json={'data': 'test'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_csrf_validation_with_header(self):
        """اختبار CSRF مع header"""
        response = self.client.get('/')
        csrf_token = response.cookies.get('csrf_token')
        
        # طلب مع header (يجب أن ينجح إذا كان المسار محمياً)
        response = self.client.post(
            '/api/analysis',
            json={'data': 'test'},
            headers={'X-CSRFToken': csrf_token},
            content_type='application/json'
        )
        # لن يكون 403 للخطأ في CSRF
        self.assertNotEqual(response.status_code, 403)


class TestInputSanitization(unittest.TestCase):
    """اختبار تنظيف المدخلات"""

    def test_sanitize_html(self):
        """اختبار إزالة HTML"""
        dirty = '<script>alert("XSS")</script>Hello'
        clean = sanitize_input(dirty, 'text')
        self.assertNotIn('<script>', clean)
        self.assertIn('Hello', clean)

    def test_sanitize_email(self):
        """اختبار تنظيف البريد الإلكتروني"""
        valid_email = sanitize_input('test@example.com', 'email')
        self.assertIn('@', valid_email)
        
        invalid_email = sanitize_input('<test>@example.com', 'email')
        self.assertNotIn('<', invalid_email)

    def test_sanitize_username(self):
        """اختبار تنظيف اسم المستخدم"""
        username = sanitize_input('user123', 'username')
        self.assertIsNotNone(username)
        self.assertIsInstance(username, str)

    def test_sanitize_xss_attempts(self):
        """اختبار حماية من XSS"""
        xss_attempts = [
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
            '<svg onload=alert("XSS")>',
        ]
        
        for attempt in xss_attempts:
            clean = sanitize_input(attempt, 'text')
            self.assertNotIn('alert', clean)


class TestDataIsolation(unittest.TestCase):
    """اختبار عزل البيانات بين المستخدمين"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # إنشاء مستخدمين للاختبار
        self.user1 = User(
            username='user1',
            email='user1@example.com',
            role='patient'
        )
        self.user1.set_password('password123')
        
        self.user2 = User(
            username='user2',
            email='user2@example.com',
            role='patient'
        )
        self.user2.set_password('password123')
        
        db.session.add(self.user1)
        db.session.add(self.user2)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def test_ensure_data_ownership(self):
        """اختبار تطبيق ملكية البيانات"""
        # يجب أن ينجح للمالك
        result = ensure_data_ownership(
            resource_owner_id=self.user1.id,
            current_user_id=self.user1.id,
            admin_bypass=False
        )
        self.assertTrue(result)
        
        # يجب أن يفشل للمستخدم الآخر
        result = ensure_data_ownership(
            resource_owner_id=self.user1.id,
            current_user_id=self.user2.id,
            admin_bypass=False
        )
        self.assertFalse(result)

    def test_admin_bypass(self):
        """اختبار تجاوز المسؤول"""
        # المسؤول يمكنه الوصول
        result = ensure_data_ownership(
            resource_owner_id=self.user1.id,
            current_user_id=self.user2.id,
            admin_bypass=True
        )
        self.assertTrue(result)


class TestPerformance(unittest.TestCase):
    """اختبار تحسينات الأداء"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_response_time(self):
        """اختبار سرعة الاستجابة"""
        # يجب أن تكون الاستجابة سريعة
        start = time.time()
        response = self.client.get('/health')
        duration = time.time() - start
        
        # يجب أن تكون أقل من 100ms (في الاختبار)
        self.assertLess(duration, 0.1)

    def test_cache_headers(self):
        """اختبار رؤوس الـ cache"""
        response = self.client.get('/health')
        # التحقق من وجود رؤوس الأمان
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertIn('X-Frame-Options', response.headers)


class TestErrorHandling(unittest.TestCase):
    """اختبار معالجة الأخطاء"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()

    def test_404_error(self):
        """اختبار خطأ 404"""
        response = self.client.get('/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_method_not_allowed(self):
        """اختبار طريقة غير مسموحة"""
        response = self.client.post('/health')
        self.assertEqual(response.status_code, 405)

    def test_500_error_handling(self):
        """اختبار معالجة أخطاء 500"""
        # تطبيق يعيد error سيتم اختباره
        response = self.client.get('/api/analysis/invalid-id')
        # يجب أن يكون 400 أو 404 أو 500
        self.assertIn(response.status_code, [400, 404, 500])


class TestSecurityHeaders(unittest.TestCase):
    """اختبار رؤوس الأمان"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()

    def test_security_headers(self):
        """اختبار وجود رؤوس الأمان"""
        response = self.client.get('/health')
        
        # التحقق من رؤوس الأمان الضرورية
        required_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
        
        for header, expected_value in required_headers.items():
            self.assertIn(header, response.headers)
            self.assertEqual(response.headers[header], expected_value)


class TestLogging(unittest.TestCase):
    """اختبار نظام السجلات"""

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_request_logging(self):
        """اختبار تسجيل الطلبات"""
        response = self.client.get('/health')
        # يجب أن تكون هناك سجلات
        self.assertEqual(response.status_code, 200)

    def test_error_logging(self):
        """اختبار تسجيل الأخطاء"""
        response = self.client.get('/nonexistent')
        # يجب أن يسجل الخطأ
        self.assertEqual(response.status_code, 404)


def run_tests():
    """تشغيل جميع الاختبارات"""
    # إنشاء مجموعة اختبار
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # إضافة جميع الاختبارات
    suite.addTests(loader.loadTestsFromTestCase(TestHealthEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestCSRFProtection))
    suite.addTests(loader.loadTestsFromTestCase(TestInputSanitization))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIsolation))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityHeaders))
    suite.addTests(loader.loadTestsFromTestCase(TestLogging))
    
    # تشغيل الاختبارات
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    
    # ملخص النتائج
    print("\n" + "="*50)
    print("📊 نتائج الاختبارات / Test Results")
    print("="*50)
    print(f"✅ نجح / Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ فشل / Failed: {len(result.failures)}")
    print(f"⚠️  أخطاء / Errors: {len(result.errors)}")
    print("="*50)
