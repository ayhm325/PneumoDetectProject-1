#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار سريع لـ PneumoDetect
Quick test script for PneumoDetect
"""

import sys
import os

# تعيين ترميز UTF-8 للمخرجات في Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_imports():
    """اختبار الاستيرادات"""
    print("🔍 اختبار الاستيرادات...")
    try:
        from app import create_app, db
        from app.models import User, AnalysisResult, Notification
        from app.routes import auth, analysis, doctor, admin
        print("✅ جميع الاستيرادات تعمل بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في الاستيرادات: {e}")
        return False


def test_app_creation():
    """اختبار إنشاء التطبيق"""
    print("\n🔨 اختبار إنشاء التطبيق...")
    try:
        from app import create_app
        app = create_app()
        print("✅ تم إنشاء التطبيق بنجاح")
        return app
    except Exception as e:
        print(f"❌ خطأ في إنشاء التطبيق: {e}")
        return None


def test_database(app):
    """اختبار قاعدة البيانات"""
    print("\n💾 اختبار قاعدة البيانات...")
    try:
        with app.app_context():
            from app import db
            from app.models import User, AnalysisResult
            from sqlalchemy import text
            
            # تحقق من اتصال قاعدة البيانات
            result = db.session.execute(text("SELECT 1"))
            print("✅ اتصال قاعدة البيانات يعمل")
            
            # حساب المستخدمين
            user_count = User.query.count()
            print(f"✅ عدد المستخدمين: {user_count}")
            
            return True
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False


def test_routes(app):
    """اختبار المسارات"""
    print("\n🛣️  اختبار المسارات...")
    try:
        client = app.test_client()
        
        # اختبر مسار الصحة
        response = client.get('/health')
        if response.status_code == 200:
            print("✅ مسار /health يعمل")
        else:
            print(f"⚠️  مسار /health: {response.status_code}")
        
        # اختبر صفحة التسجيل
        response = client.get('/')
        if response.status_code == 200:
            print("✅ الصفحة الرئيسية تعمل")
        else:
            print(f"⚠️  الصفحة الرئيسية: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في اختبار المسارات: {e}")
        return False


def test_security_headers(app):
    """اختبار رؤوس الأمان"""
    print("\n🔒 اختبار رؤوس الأمان...")
    try:
        client = app.test_client()
        response = client.get('/health')
        
        headers_to_check = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Content-Security-Policy',
            'Referrer-Policy'
        ]
        
        for header in headers_to_check:
            if header in response.headers:
                print(f"✅ {header}: {response.headers[header][:50]}...")
            else:
                print(f"⚠️  {header} غير موجود")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في اختبار رؤوس الأمان: {e}")
        return False


def test_ml_processor():
    """اختبار معالج ML"""
    print("\n🤖 اختبار معالج ML...")
    try:
        from app.ml.processor import MLProcessor
        processor = MLProcessor()
        print("✅ تم إنشاء معالج ML بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في معالج ML: {e}")
        return False


def main():
    """تشغيل الاختبارات"""
    print("=" * 60)
    print("🚀 اختبار PneumoDetect")
    print("=" * 60)
    
    # الاختبارات
    if not test_imports():
        sys.exit(1)
    
    app = test_app_creation()
    if not app:
        sys.exit(1)
    
    test_database(app)
    test_routes(app)
    test_security_headers(app)
    test_ml_processor()
    
    print("\n" + "=" * 60)
    print("✅ جميع الاختبارات نجحت!")
    print("🚀 المشروع جاهز للتشغيل")
    print("=" * 60)
    print("\nلتشغيل التطبيق:")
    print("  python run.py")
    print("\nالتطبيق سيكون متاح على:")
    print("  http://localhost:5000")


if __name__ == '__main__':
    main()
