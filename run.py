import sys
import os
import logging
from flask import jsonify, request
from flask_login import login_required, current_user

# Set development environment early to avoid ProductionConfig checks
os.environ.setdefault('FLASK_ENV', 'development')
# Provide safe defaults for secrets and DB
os.environ.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')
os.environ.setdefault('DATABASE_URI', 'sqlite:///instance/site.db')

# إضافة مسار المشروع
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, AnalysisResult
# Note: Delay importing ML model loader until runtime so we can skip heavy ML deps in dev
from werkzeug.security import generate_password_hash
from flask_migrate import upgrade

# =====================================================
# إعداد Logging
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# إنشاء التطبيق
# =====================================================
try:
    app = create_app()
    logger.info('✅ تم إنشاء التطبيق بنجاح')
except Exception as e:
    logger.error(f'❌ فشل إنشاء التطبيق: {e}', exc_info=True)
    sys.exit(1)


# =====================================================
# إعداد البيانات الأولية
# =====================================================
def setup_initial_data():
    """إنشاء مستخدمين تجريبيين إذا لم يكونوا موجودين."""
    with app.app_context():
        try:
            # تطبيق الترحيلات
            logger.info('🔄 جاري تطبيق الترحيلات...')
            try:
                upgrade()
                logger.info('✅ تم تطبيق الترحيلات بنجاح')
            except Exception as e:
                logger.warning(f'⚠️ تعذر تطبيق الترحيلات: {e}. سيتم إنشاء الجداول مباشرة.')
                # إذا فشلت الترحيلات، أنشئ الجداول مباشرة
                db.create_all()
                logger.info('✅ تم إنشاء الجداول بنجاح')
            # Optional demo user seeding (enabled by default in development)
            seed_demo = os.getenv('SEED_DEMO', '1').lower() in ['1', 'true', 'yes']
            if seed_demo:
                # إنشاء طبيب تجريبي
                if not User.query.filter_by(username='dr_ahmad').first():
                    hashed = generate_password_hash('pass123', method='pbkdf2:sha256')
                    doctor = User(
                        username='dr_ahmad',
                        email='ahmad@clinic.com',
                        password_hash=hashed,
                        role='doctor'
                    )
                    db.session.add(doctor)
                    logger.info('👨‍⚕️  تم إنشاء طبيب تجريبي: dr_ahmad / pass123')

                # إنشاء مريض تجريبي
                if not User.query.filter_by(username='patient_sami').first():
                    hashed = generate_password_hash('pass123', method='pbkdf2:sha256')
                    patient = User(
                        username='patient_sami',
                        email='sami@test.com',
                        password_hash=hashed,
                        role='patient'
                    )
                    db.session.add(patient)
                    logger.info('👨‍🦳 تم إنشاء مريض تجريبي: patient_sami / pass123')

                # إنشاء مدير
                if not User.query.filter_by(username='admin').first():
                    hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
                    admin = User(
                        username='admin',
                        email='admin@pneumodetect.com',
                        password_hash=hashed,
                        role='admin'
                    )
                    db.session.add(admin)
                    logger.info('👤 تم إنشاء مدير: admin / admin123')

                db.session.commit()
                logger.info('✅ تم إعداد البيانات الأولية بنجاح (demo seed)')
            else:
                logger.info('ℹ️ تم تخطي إنشاء المستخدمين التجريبيين (SEED_DEMO not set)')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'❌ خطأ في إعداد البيانات: {e}', exc_info=True)


# =====================================================
# واجهات برمجة التطبيقات
# =====================================================
@app.route('/api/patient/analyses', methods=['GET'])
@login_required
def get_patient_analyses():
    """Retrieve analyses for the logged-in patient."""
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        sort = request.args.get('sort', 'recent')

        query = AnalysisResult.query.filter_by(user_id=current_user.id)

        if status != 'all':
            query = query.filter_by(review_status=status)

        if sort == 'recent':
            query = query.order_by(AnalysisResult.created_at.desc())
        elif sort == 'oldest':
            query = query.order_by(AnalysisResult.created_at.asc())

        pagination = query.paginate(page=page, per_page=10, error_out=False)

        data = {
            'items': [result.to_dict() for result in pagination.items],
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }

        return jsonify({'success': True, 'data': data}), 200

    except Exception as e:
        logger.error(f"Error retrieving patient analyses: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to retrieve analyses'}), 500


# =====================================================
# تشغيل التطبيق
# =====================================================
if __name__ == '__main__':
    try:
        # 1. إعداد البيانات الأولية
        logger.info('🔧 جاري إعداد البيانات الأولية...')
        setup_initial_data()
        
        # 2. تحميل نموذج ML (قابل للتخطي أثناء التطوير المحلي)
        skip_ml = os.getenv('SKIP_ML', '0').lower() in ['1', 'true', 'yes']
        if not skip_ml:
            logger.info('🤖 جاري تحميل نموذج التعلم الآلي...')
            # استيراد المؤجل لتجنّب استيراد مكتبات ثقيلة (torch) عند عدم الحاجة
            from app.routes.analysis import load_ml_model
            with app.app_context():
                load_ml_model(app)
        else:
            logger.info('⚠️ تم تجاوز تحميل نموذج ML (SKIP_ML=1)')
        
        # 3. الحصول على الإعدادات
        debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        env = app.config.get('ENV', 'development')
        
        # 4. الطباعة المعلومات
        logger.info('=' * 60)
        logger.info('🚀 PneumoDetect - تطبيق تحليل صور الأشعة السينية')
        logger.info('=' * 60)
        logger.info(f'🔧 البيئة: {env}')
        logger.info(f'🐛 وضع التصحيح: {"✅" if debug_mode else "❌"}')
        logger.info(f'🌐 الخادم: http://{host}:{port}')
        logger.info(f'📊 قاعدة البيانات: {app.config["SQLALCHEMY_DATABASE_URI"]}')
        logger.info('=' * 60)
        logger.info('📝 حسابات تجريبية:')
        logger.info('  • طبيب: dr_ahmad / pass123')
        logger.info('  • مريض: patient_sami / pass123')
        logger.info('  • مدير: admin / admin123')
        logger.info('=' * 60)
        
        # 5. تشغيل الخادم
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            use_reloader=debug_mode
        )
        
    except KeyboardInterrupt:
        logger.info('⛔ تم إيقاف التطبيق من قبل المستخدم')
        sys.exit(0)
    except Exception as e:
        logger.error(f'❌ خطأ حرج في التطبيق: {e}', exc_info=True)
        sys.exit(1)
