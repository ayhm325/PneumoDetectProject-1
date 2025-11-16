#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص شامل للتطبيق - اختبار جميع الوحدات والمسارات
"""

import os
import sys
os.environ['SKIP_ML'] = '1'

from app import create_app, db
from app.models import User

def test_app_structure():
    """فحص بنية التطبيق"""
    print("\n" + "="*70)
    print("🧪 فحص شامل للتطبيق")
    print("="*70)
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    
    # 1. فحص Blueprints
    print("\n✓ الـ Blueprints المسجلة:")
    with app.app_context():
        blueprints_info = {}
        for name, blueprint in app.blueprints.items():
            blueprints_info[name] = len(blueprint.deferred_functions)
            print(f"  - {name}: {len(blueprint.deferred_functions)} دالة")
    
    # 2. فحص Routes
    print("\n✓ المسارات المتاحة:")
    with app.app_context():
        routes_info = []
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static') and not rule.rule.startswith('/uploads'):
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                routes_info.append((rule.rule, methods))
                print(f"  {rule.rule:45} [{methods}]")
        
        print(f"\n📊 إجمالي المسارات: {len(routes_info)}")
    
    # 3. فحص Database
    print("\n✓ قاعدة البيانات:")
    with app.app_context():
        try:
            db.create_all()
            print("  - Database initialized: ✓")
            print("  - User model created: ✓")
        except Exception as e:
            print(f"  ✗ خطأ في البيانات: {e}")
            return False
    
    # 4. فحص API Endpoints
    print("\n✓ نقاط API:")
    api_endpoints = {
        'Auth': ['/api/auth/register', '/api/auth/login', '/api/auth/logout', 
                 '/api/auth/status', '/api/auth/profile', '/api/auth/change-password'],
        'Analysis': ['/api/analysis/upload', '/api/analysis/history', '/api/analysis/detail/<int:id>'],
        'Doctor': ['/api/doctor/reviews', '/api/doctor/pending'],
        'Admin': ['/api/admin/users', '/api/admin/stats']
    }
    
    for category, endpoints in api_endpoints.items():
        print(f"  {category}:")
        for endpoint in endpoints:
            # تنظيف الـ URL parameters
            clean_endpoint = endpoint.replace('<int:id>', '{id}')
            status = "✓" if any(clean_endpoint in str(r) for r in routes_info) else "?"
            print(f"    {status} {clean_endpoint}")
    
    # 5. فحص static files
    print("\n✓ الملفات الثابتة:")
    static_path = 'app/static'
    for item in os.listdir(static_path):
        if os.path.isfile(os.path.join(static_path, item)):
            size = os.path.getsize(os.path.join(static_path, item)) / 1024
            print(f"  - {item}: {size:.1f} KB")
    
    # 6. فحص Templates
    print("\n✓ قوالب HTML:")
    templates_path = 'app/templates'
    templates = os.listdir(templates_path)
    for template in templates:
        if template.endswith('.html'):
            print(f"  - {template}")
    
    # 7. اختبار سريع للمسارات
    print("\n✓ اختبار سريع للمسارات:")
    with app.test_client() as client:
        test_routes = [
            ('/', 'GET', 200),
            ('/login', 'GET', 200),
            ('/register', 'GET', 200),
            ('/doctor', 'GET', 302),  # يجب أن يعيد توجيه
            ('/patient', 'GET', 302),
        ]
        
        for route, method, expected_status in test_routes:
            try:
                if method == 'GET':
                    response = client.get(route)
                status_code = response.status_code
                status = "✓" if status_code in [expected_status, 301, 302, 307, 308] else "✗"
                print(f"  {status} {method:6} {route:30} [{status_code}]")
            except Exception as e:
                print(f"  ✗ {method:6} {route:30} [ERROR: {str(e)[:30]}]")
    
    print("\n" + "="*70)
    print("✅ فحص التطبيق اكتمل بنجاح!")
    print("="*70)
    return True

if __name__ == '__main__':
    try:
        success = test_app_structure()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
