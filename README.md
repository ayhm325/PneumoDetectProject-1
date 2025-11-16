# 🏥 PneumoDetect - نظام كشف الالتهاب الرئوي بالذكاء الاصطناعي

## 📋 نظرة عامة

**PneumoDetect** هو نظام ويب متقدم لتحليل صور الأشعة السينية للصدر باستخدام الذكاء الاصطناعي. يوفر كشف التهاب الرئة الآلي مع واجهة احترافية وآمنة.

### ✨ المميزات الرئيسية

- ✅ تحليل ذكي للصور باستخدام PyTorch و Transformers
- ✅ خرائط الإبراز لتصور قرارات النموذج
- ✅ نظام أدوار متقدم (مريض، طبيب، مدير)
- ✅ أمان عالي مع CSRF و XSS protection
- ✅ واجهة ثنائية اللغة (عربي/إنجليزي)
- ✅ نظام إخطارات متقدم
- ✅ لوحة إدارية شاملة
- ✅ نظام تدقيق أمني كامل

---

## 🏗️ البنية الأساسية

```
app/
├── __init__.py          # مصنع التطبيق
├── config.py            # الإعدادات
├── models.py            # نماذج البيانات
├── utils.py             # دوال مساعدة
├── routes/
│   ├── main.py         # المسارات الرئيسية
│   ├── auth.py         # المصادقة
│   ├── analysis.py     # التحليل
│   └── doctor.py       # لوحة الطبيب
├── ml/
│   └── processor.py    # معالج ML
├── static/
│   ├── css/
│   │   └── main.css    # الأنماط الموحدة
│   └── js/
│       └── core.js     # JavaScript الموحد
└── templates/          # قوالب HTML (6 ملفات)
```

---

## 🚀 البدء السريع

### 1. المتطلبات
- Python 3.9+
- pip أو conda

### 2. التثبيت

```bash
# استنساخ المشروع
git clone https://github.com/AyhmObeidat/PneumoDetect.git
cd PneumoDetect

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate     # Windows

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 3. التكوين

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل المتغيرات حسب الحاجة
export FLASK_ENV=development
export SKIP_ML=1  # لتخطي ML في التطوير
```

### 4. تشغيل التطبيق

```bash
# تطبيق الترحيلات
flask db upgrade

# تشغيل الخادم
python run.py
```

التطبيق سيكون متاحاً على: `http://localhost:5000`

---

## 🧪 الاختبار

### تشغيل البيانات الأولية
```bash
# في Python shell
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    db.create_all()
    # أضف مستخدمي الاختبار
```

### الاختبارات الآلية
```bash
SKIP_ML=1 pytest
```

---

## 🛠️ المتطلبات (4 فئات موحدة)

```
1. Web Framework (Flask Ecosystem)
   - Flask 3.0.0
   - flask-cors 4.0.0
   - Werkzeug 3.0.1
   - gunicorn 21.2.0

2. Database (SQLAlchemy & Migrations)
   - Flask-SQLAlchemy 3.1.1
   - Flask-Login 0.6.3
   - Flask-Migrate 4.0.5
   - alembic 1.13.0

3. ML & Image Processing (Optional)
   - torch 2.1.0
   - torchvision 0.16.0
   - pytorch-lightning 2.1.0
   - transformers 4.37.0
   - opencv-python 4.9.0.80

4. Utilities & Data
   - numpy 1.26.4
   - Pillow 11.3.0
   - redis 5.0.1
   - python-dateutil 2.8.2
   - pytz 2024.1
```

---

## 🔐 الأمان

- ✅ CSRF Protection (multi-source)
- ✅ XSS Prevention (sanitization)
- ✅ Data Ownership Checks
- ✅ Rate Limiting
- ✅ Audit Logging
- ✅ Password Hashing (werkzeug)

---

## 📚 التوثيق

- `QUICK_START.md` - دليل سريع للبدء
- `FRONTEND_INTEGRATION.md` - دليل الواجهة الأمامية
- `SECURITY_ENHANCEMENTS.md` - إجراءات الأمان
- `API_DOCUMENTATION.md` - توثيق الواجهات
- `DEPLOYMENT.md` - تعليمات النشر
- `DOCUMENTATION_INDEX.md` - فهرسة التوثيق الكاملة

---

## 🌐 الواجهات الرئيسية

| المسار | الطريقة | الوصف |
|--------|---------|-------|
| `/` | GET | الصفحة الرئيسية |
| `/login` | POST | تسجيل الدخول |
| `/register` | POST | إنشاء حساب |
| `/api/analysis` | POST | تحليل صورة |
| `/api/history` | GET | سجل التحليلات |
| `/health` | GET | فحص صحة النظام |

---

## 🎯 حالة المشروع

✅ **جاهز للإنتاج** (v1.0.0)
- Frontend منظم وموحد
- Backend آمن ومستقر
- Database مهاجر وممتحن
- توثيق شامل متاح

---

## 📞 الدعم

للأسئلة أو المشاكل:
1. راجع التوثيق في المجلد الجذري
2. تحقق من console (F12)
3. راجع لحظات الأخطاء في السجلات

---

## 📄 الترخيص

MIT License - انظر LICENSE.md

---

**آخر تحديث**: نوفمبر 2025 | **الإصدار**: 1.0.0

- Start the server (PowerShell):

```powershell
Set-Location 'C:\Users\user\Desktop\PneumoDetectProject'
#$env:FLASK_ENV = 'development'   # optional
$env:SKIP_ML = '1'
$env:MOCK_ANALYSIS = '1'
python run.py
```

- Quick smoke tests (PowerShell + curl). The first `GET` obtains the `XSRF-TOKEN` cookie. The POST without header should be rejected (403). The POST with `X-CSRF-Token` header taken from the cookie should return the mock JSON (200).

```powershell
# Save cookies to a file
curl.exe -i -c cookies.txt http://127.0.0.1:5000/

# POST without CSRF header (expected 403)
curl.exe -i -b cookies.txt -H "Content-Type: application/json" -d "{}" -X POST http://127.0.0.1:5000/api/analysis

# Extract XSRF token from cookie file (very small helper)
$token = (Select-String 'XSRF-TOKEN' cookies.txt).ToString().Split()[-1]
Write-Host "XSRF: $token"

# POST with CSRF header (expected 200 with mock JSON)
curl.exe -i -b cookies.txt -H "Content-Type: application/json" -H "X-CSRF-Token: $token" -d "{}" -X POST http://127.0.0.1:5000/api/analysis

Remove-Item cookies.txt -Force
```

- Python quick test (uses `requests`) — run from project root:

```powershell
python -c "import requests; s=requests.Session(); s.get('http://127.0.0.1:5000/'); print('cookies', s.cookies.get_dict()); r1=s.post('http://127.0.0.1:5000/api/analysis', json={}); print('no-header', r1.status_code); token=s.cookies.get('XSRF-TOKEN'); r2=s.post('http://127.0.0.1:5000/api/analysis', json={}, headers={'X-CSRF-Token': token}); print('with-header', r2.status_code, r2.text[:200])"
```

Notes:
- If you prefer not to run the ML model locally, keep `SKIP_ML=1` in development.
- When you want to enable the real model, unset `SKIP_ML` and ensure the required ML packages are installed and compatible with your environment.

### التثبيت والتشغيل

```bash
# 1. استنساخ المشروع
cd PneumoDetectProject

# 2. تثبيت المتطلبات
pip install -r requirements.txt

# 3. تعيين متغيرات البيئة (.env)
# تأكد من تعيين SECRET_KEY و HF_TOKEN

# 4. تشغيل التطبيق
python run.py
```

### الوصول إلى التطبيق
```
🌐 الرابط: http://localhost:5000
```

### حسابات تجريبية
```
👨‍⚕️ طبيب:   dr_ahmad / pass123
👨‍🦳 مريض:   patient_sami / pass123
👤 مدير:    admin / admin123
```

---

## 🔐 متغيرات البيئة (.env)

```env
# الأمان
SECRET_KEY=your-secret-key-here

# Hugging Face
HF_TOKEN=your-hf-token
MODEL_REPO=dima806/chest_xray_pneumonia_detection

# قاعدة البيانات
DATABASE_URI=sqlite:///site.db

# الملفات
UPLOAD_FOLDER=uploads

# المنفذ
PORT=5000
FLASK_ENV=development
FLASK_DEBUG=True
```

---

## 📚 API Endpoints

### المصادقة (Authentication)
```
POST /register          - تسجيل مستخدم جديد
POST /login            - تسجيل الدخول
POST /logout           - تسجيل الخروج
GET  /status           - حالة المستخدم الحالي
POST /change-password  - تغيير كلمة المرور
GET  /profile          - الملف الشخصي
PUT  /profile          - تحديث الملف الشخصي
```

### التحليل (Analysis)
```
POST /analyze              - تحليل مؤقت (للزوار)
POST /analyze_and_save     - تحليل وحفظ (للمسجلين)
GET  /analysis/<id>        - تفاصيل التحليل
GET  /uploads/<path>       - تحميل الملفات
DELETE /analysis/<id>      - حذف التحليل
```

### لوحة الطبيب (Doctor Panel)
```
GET  /doctor/my/results    - نتائجي
GET  /doctor/analyses      - قائمة التحاليل
POST /doctor/review/<id>   - مراجعة التحليل
GET  /doctor/stats         - إحصائياتي
GET  /doctor/report/<id>   - تقرير مفصل
```

---

## 🔧 التحسينات الاحترافية المطبقة

### 1. **نماذج محسّنة** (Models)
- ✅ إضافة `created_at`, `updated_at` timestamps
- ✅ Validation methods للتحقق من البيانات
- ✅ `to_dict()` لتحويل النماذج إلى قواموس
- ✅ العلاقات محسّنة مع cascade delete

### 2. **المصادقة والأمان** (Auth)
- ✅ Rate limiting (تحديد معدل الطلبات)
- ✅ Validation قوي للبيانات
- ✅ إضافة `change-password` و `profile`
- ✅ Remember me functionality
- ✅ معالجة شاملة للأخطاء

### 3. **معالجة الأخطاء** (Error Handling)
- ✅ Decorators للمعالجة الموحدة
- ✅ استجابات API موحدة `APIResponse`
- ✅ Logging لجميع الأخطاء والعمليات الحرجة
- ✅ رسائل خطأ واضحة بالعربية

### 4. **التحليل** (Analysis)
- ✅ Validation شامل للصور
- ✅ معالجة آمنة للملفات (Path Traversal Protection)
- ✅ حذف التحاليل (مع حذف الملفات)
- ✅ دعم الرجوع للتفاصيل

### 5. **لوحة الطبيب** (Doctor Dashboard)
- ✅ إحصائيات متقدمة
- ✅ فلترة وبحث محسّن
- ✅ Pagination محسّن
- ✅ تقارير مفصلة

### 6. **الواجهة الأمامية** (Frontend)
- ✅ JavaScript محسّن مع `script_professional.js`
- ✅ إدارة الحالة (State Management)
- ✅ معالجة الأخطاء الشاملة
- ✅ إشعارات حديثة
- ✅ Internationalization (i18n)

### 7. **الإعدادات** (Configuration)
- ✅ `config.py` لإدارة الإعدادات بسهولة
- ✅ دعم عدة بيئات (development, testing, production)
- ✅ متغيرات البيئة محمية

### 8. **الأدوات المساعدة** (Utilities)
- ✅ `utils.py` بأدوات مساعدة شاملة
- ✅ `APIResponse` لاستجابات موحدة
- ✅ Decorators للتحقق والتحديد
- ✅ Validators للصور والملفات

---

## 📊 إحصائيات المشروع

| العنصر | الحالة | ملاحظات |
|--------|--------|--------|
| **Models** | ✅ محسّن | Validation، Timestamps، Methods |
| **Authentication** | ✅ محسّن | Rate Limiting، Profile Management |
| **Analysis** | ✅ محسّن | Error Handling، Security |
| **Doctor Dashboard** | ✅ محسّن | Stats، Advanced Filtering |
| **Error Handling** | ✅ جديد | Decorators، Logging، Unified Responses |
| **Configuration** | ✅ جديد | Multi-env، Best Practices |
| **Utilities** | ✅ جديد | Helper Functions، Validators |
| **Frontend JS** | ✅ جديد | Professional Script، i18n، State Management |
| **Security** | ✅ محسّن | Password Hashing، Path Traversal Protection |
| **Documentation** | ✅ شامل | README، Comments، API Docs |

---

## 🐛 معالجة الأخطاء

النظام يستخدم نظام معالجة أخطاء موحد:

```json
{
  "success": false,
  "message": "رسالة الخطأ بالعربية",
  "code": 400,
  "error_code": "ERROR_TYPE",
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## 📝 Logging

يتم تسجيل جميع العمليات المهمة في `app.log`:

```
2025-11-13 10:30:00 - app - INFO - ✅ تم تحميل النموذج بنجاح
2025-11-13 10:31:00 - app.routes.auth - INFO - دخول ناجح: dr_ahmad
2025-11-13 10:32:00 - app.routes.analysis - INFO - تحليل ناجح: NORMAL (98.5%)
```

---

## 🧪 الاختبار

```bash
# اختبار الـ API
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "dr_ahmad", "password": "pass123"}'

# تحميل صورة
curl -F "file=@image.jpg" http://localhost:5000/analyze
```

---

## 🚀 النشر في الإنتاج

### مع Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

### مع Docker (اختياري)

```bash
docker build -t pneumodetect .
docker run -p 5000:5000 pneumodetect
```

---

## 📞 الدعم والمساعدة

- 📧 البريد الإلكتروني: support@pneumodetect.com
- 🐛 البلاغ عن الأخطاء: GitHub Issues
- 📖 التوثيق: docs/README

---

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT.

---

## 👨‍💻 المطورون

تم تطوير هذا المشروع بعناية فائقة مع التركيز على:
- ✅ أفضل الممارسات البرمجية
- ✅ الأمان والخصوصية
- ✅ قابلية التوسع
- ✅ سهولة الصيانة
- ✅ تجربة المستخدم الممتازة

---

**آخر تحديث**: 13 نوفمبر 2025
**الإصدار**: 1.0.0 (Professional Edition)
