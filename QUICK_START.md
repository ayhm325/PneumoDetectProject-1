# 🚀 دليل البدء السريع - PneumoDetect Frontend

## الملفات الجديدة المهمة

### 1️⃣ main.css - نظام الأنماط الموحد
```
📁 app/static/css/main.css
```
**الاستخدام**: متضمن تلقائياً في جميع ملفات HTML
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
```

### 2️⃣ core.js - وحدة JavaScript المركزية
```
📁 app/static/js/core.js
```
**الاستخدام**: 
```html
<script src="{{ url_for('static', filename='js/core.js') }}"></script>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    PneumoApp.init();
    PneumoApp.Theme.init();
  });
</script>
```

## أمثلة استخدام سريعة

### إظهار تنبيه
```javascript
PneumoApp.Utils.notify('تم بنجاح!', 'success');
// أو
PneumoApp.Utils.notify('حدث خطأ', 'error');
```

### طلب API
```javascript
// GET
PneumoApp.API.get('/api/user-data')
  .then(data => console.log(data))
  .catch(err => console.error(err));

// POST
PneumoApp.API.post('/api/submit', { name: 'Ali' })
  .then(result => PneumoApp.Utils.notify('تم!', 'success'))
  .catch(err => PneumoApp.Utils.notify('خطأ', 'error'));
```

### التحقق من النموذج
```javascript
const form = document.getElementById('my-form');
if (PneumoApp.Forms.validate(form)) {
  const data = PneumoApp.Forms.getFormData(form);
  console.log(data);
}
```

### تبديل الوضع الليلي
```javascript
// تبديل يدوي
PneumoApp.Theme.toggle();

// الحصول على الوضع الحالي
const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
```

### معالجة DOM
```javascript
// البحث
const btn = PneumoApp.DOM.get('#submit-btn');

// إضافة حدث
PneumoApp.DOM.on(btn, 'click', () => {
  console.log('تم النقر على الزر');
});

// تعديل النص
PneumoApp.DOM.setText(btn, 'جاري المعالجة...');

// إضافة/إزالة أصناف
PneumoApp.DOM.toggleClass(btn, 'active');
```

## الألوان الأساسية

```javascript
// CSS Variables
--color-primary: #028876 (أخضر)
--color-secondary: #149cea (أزرق)
--color-accent: #4361ee (أرجواني)
--color-success: #10b981 (نجاح)
--color-error: #ef4444 (خطأ)
--color-warning: #f59e0b (تحذير)
```

## الفئات المتاحة

```html
<!-- أزرار -->
<button class="btn btn-primary">زر أساسي</button>
<button class="btn btn-secondary">زر ثانوي</button>
<button class="btn btn-outline">زر الحد</button>

<!-- تنبيهات -->
<div class="alert alert-success">نجح!</div>
<div class="alert alert-error">خطأ!</div>
<div class="alert alert-warning">تحذير</div>

<!-- بطاقات -->
<div class="card">
  <div class="card-header">الرأس</div>
  <div class="card-body">المحتوى</div>
  <div class="card-footer">التذييل</div>
</div>

<!-- نماذج -->
<form>
  <div class="form-group">
    <label for="name">الاسم</label>
    <input type="text" id="name" class="form-control">
    <span class="error-text">رسالة الخطأ</span>
  </div>
</form>
```

## التكامل مع الخادم

### CSRF Token
```html
<!-- في الرأس -->
<meta name="csrf-token" content="{{ csrf_token() }}">

<!-- يتم استخراجه تلقائياً بواسطة core.js -->
```

### المصادقة
```javascript
// التحقق من تسجيل الدخول
if (PneumoApp.Auth.isAuthenticated()) {
  // المستخدم مسجل دخول
  const user = PneumoApp.Auth.getCurrentUser();
}
```

## الملفات المتاحة

| الملف | الحجم | الغرض |
|------|------|-------|
| main.css | 12.7 KB | نظام CSS موحد ✅ |
| core.js | 13.4 KB | وحدة JS مركزية ✅ |
| style.css | 37 KB | أنماط إضافية (محفوظ) |
| script_professional.js | 43 KB | دوال خاصة (محفوظ) |

## معلومات إضافية

📖 للمزيد من التفاصيل، راجع:
- `FRONTEND_INTEGRATION.md` - دليل شامل
- `FRONTEND_COMPLETION_REPORT.md` - تقرير الإنجاز

🐛 عند مواجهة مشاكل:
1. افتح console (F12)
2. ابحث عن الأخطاء
3. تحقق من أن `core.js` محمل
4. تحقق من أن `main.css` محمل

✅ جاهز للاستخدام!

---
آخر تحديث: نوفمبر 2025
