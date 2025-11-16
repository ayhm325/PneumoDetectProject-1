# 📚 PneumoDetect API Documentation
# توثيق كامل لواجهات API المتقدمة

## 🔐 مسارات المصادقة (Authentication Routes)

### 1. تسجيل مستخدم جديد
```
POST /register
Content-Type: application/json

{
  "username": "doctor_name",
  "email": "doctor@clinic.com",
  "password": "SecurePassword123",
  "role": "doctor"  // أو "patient"
}

Response (201):
{
  "success": true,
  "message": "تم إنشاء الحساب بنجاح",
  "data": {
    "user_id": 1,
    "username": "doctor_name"
  }
}
```

### 2. تسجيل الدخول
```
POST /login
Content-Type: application/json

{
  "username": "doctor_name",
  "password": "SecurePassword123",
  "remember_me": true  // اختياري
}

Response (200):
{
  "success": true,
  "message": "تم تسجيل الدخول بنجاح",
  "data": {
    "user_id": 1,
    "username": "doctor_name",
    "role": "doctor"
  }
}
```

---

## 🔬 مسارات التحليل (Analysis Routes)

### 3. تحليل صورة (للزوار - بدون حفظ)
```
POST /analyze
Content-Type: multipart/form-data

file: [image file]

Response (200):
{
  "success": true,
  "message": "تم التحليل بنجاح",
  "data": {
    "result": "NORMAL",  // أو "PNEUMONIA"
    "confidence": 0.95,
    "explanation": "الصورة طبيعية...",
    "saliency_url": "http://..."
  }
}
```

### 4. تحليل صورة وحفظها (للمسجلين)
```
POST /analyze_and_save
Authorization: Bearer token
Content-Type: multipart/form-data

file: [image file]

Response (201):
{
  "success": true,
  "message": "تم التحليل والحفظ بنجاح",
  "data": {
    "analysis_id": 42,
    "result": "PNEUMONIA",
    "confidence": 0.87,
    "image_url": "http://...",
    "saliency_url": "http://...",
    "created_at": "2025-11-13T10:30:00"
  }
}
```

### 5. الحصول على تفاصيل تحليل
```
GET /analysis/42
Authorization: Bearer token

Response (200):
{
  "success": true,
  "data": {
    "id": 42,
    "model_result": "PNEUMONIA",
    "confidence": 0.87,
    "review_status": "pending",
    "created_at": "2025-11-13T10:30:00"
  }
}
```

### 6. حذف تحليل
```
DELETE /analysis/42
Authorization: Bearer token

Response (200):
{
  "success": true,
  "message": "تم حذف التحليل بنجاح"
}
```

### 7. الحصول على إخطارات المستخدم
```
GET /notifications?page=1&unread_only=false
Authorization: Bearer token

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid-1234",
        "type": "ANALYSIS_READY",
        "message": "تحليل جديد في انتظار المراجعة",
        "is_read": false,
        "created_at": "2025-11-13T10:30:00"
      }
    ],
    "page": 1,
    "total": 5
  }
}
```

### 8. وضع علامة على إخطار كمقروء
```
PUT /notifications/uuid-1234/read
Authorization: Bearer token

Response (200):
{
  "success": true,
  "message": "تم وضع علامة على الإخطار كمقروء"
}
```

---

## 👨‍⚕️ مسارات الأطباء (Doctor Routes)

### 9. قائمة التحاليل
```
GET /doctor/analyses?page=1&status=pending&result=PNEUMONIA
Authorization: Bearer token (Doctor/Admin)

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 42,
        "patient_username": "patient_sami",
        "model_result": "PNEUMONIA",
        "confidence": 0.87,
        "review_status": "pending",
        "created_at": "2025-11-13T10:30:00"
      }
    ],
    "page": 1,
    "total": 15,
    "pages": 2
  }
}
```

### 10. مراجعة تحليل
```
POST /doctor/review/42
Authorization: Bearer token (Doctor/Admin)
Content-Type: application/json

{
  "notes": "تم الفحص الدقيق. الحالة تحتاج متابعة طارئة.",
  "status": "reviewed"  // أو "rejected"
}

Response (200):
{
  "success": true,
  "message": "تم تحديث مراجعة التحليل بنجاح",
  "data": {
    "analysis_id": 42,
    "reviewer": "dr_ahmad",
    "status": "reviewed",
    "updated_at": "2025-11-13T11:00:00"
  }
}
```

### 11. إحصائيات الطبيب
```
GET /doctor/stats
Authorization: Bearer token (Doctor/Admin)

Response (200):
{
  "success": true,
  "data": {
    "total_reviewed": 125,
    "pending_reviews": 8,
    "pneumonia_detected": 34,
    "normal_cases": 91,
    "avg_review_time": "2.5 hours"
  }
}
```

### 12. سجل التغييرات للتحليل
```
GET /doctor/analysis/42/history
Authorization: Bearer token (Doctor/Admin/Owner)

Response (200):
{
  "success": true,
  "data": {
    "analysis_id": 42,
    "history": [
      {
        "previous_status": "pending",
        "new_status": "reviewed",
        "changed_by": "dr_ahmad",
        "reason": "تم الفحص الدقيق...",
        "changed_at": "2025-11-13T11:00:00"
      }
    ],
    "total_changes": 2
  }
}
```

---

## 👤 مسارات ملف المستخدم (Profile Routes)

### 13. الحصول على الملف الشخصي
```
GET /profile
Authorization: Bearer token

Response (200):
{
  "success": true,
  "data": {
    "id": 1,
    "username": "dr_ahmad",
    "email": "ahmad@clinic.com",
    "role": "doctor",
    "created_at": "2025-11-01T10:00:00"
  }
}
```

### 14. تحديث الملف الشخصي
```
PUT /profile
Authorization: Bearer token
Content-Type: application/json

{
  "email": "new_email@clinic.com",
  "full_name": "Dr. Ahmad"
}

Response (200):
{
  "success": true,
  "message": "تم تحديث الملف الشخصي"
}
```

### 15. تغيير كلمة المرور
```
POST /change-password
Authorization: Bearer token
Content-Type: application/json

{
  "old_password": "OldPassword123",
  "new_password": "NewPassword456"
}

Response (200):
{
  "success": true,
  "message": "تم تغيير كلمة المرور بنجاح"
}
```

---

## 👨‍💼 مسارات الإدارة (Admin Routes)

### 16. إحصائيات النظام
```
GET /admin/stats/system
Authorization: Bearer token (Admin only)

Response (200):
{
  "success": true,
  "data": {
    "total_users": 156,
    "total_doctors": 12,
    "total_patients": 140,
    "total_admins": 2,
    "total_analyses": 845,
    "pneumonia_detected": 234,
    "normal_cases": 611,
    "pending_reviews": 8,
    "pneumonia_percentage": 27.69
  }
}
```

### 17. إحصائيات المستخدمين
```
GET /admin/stats/users?page=1&role=doctor
Authorization: Bearer token (Admin only)

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 2,
        "username": "dr_ahmad",
        "role": "doctor",
        "total_reviewed": 125,
        "pending_reviews": 8
      }
    ],
    "page": 1,
    "total": 12
  }
}
```

### 18. إحصائيات التحليلات
```
GET /admin/stats/analyses?days=30&status=reviewed&result=PNEUMONIA
Authorization: Bearer token (Admin only)

Response (200):
{
  "success": true,
  "data": {
    "period": "30 أيام",
    "total_analyses": 450,
    "by_result": {
      "pneumonia": 125,
      "normal": 325,
      "pneumonia_percentage": 27.78
    },
    "by_status": {
      "pending": 8,
      "reviewed": 435,
      "rejected": 7
    },
    "confidence": {
      "average": 0.87,
      "high": 380,
      "medium": 50,
      "low": 20
    }
  }
}
```

### 19. تحديث حالة المستخدم
```
PUT /admin/users/5/status
Authorization: Bearer token (Admin only)
Content-Type: application/json

{
  "is_active": false
}

Response (200):
{
  "success": true,
  "message": "تم تحديث حالة المستخدم: معطّل"
}
```

### 20. التقرير الشامل للنظام
```
GET /admin/report/system
Authorization: Bearer token (Admin only)

Response (200):
{
  "success": true,
  "data": {
    "generated_at": "2025-11-13T12:00:00",
    "general_stats": { ... },
    "activity": {
      "analyses_today": 15
    },
    "top_doctors": [
      { "username": "dr_ahmad", "review_count": 125 }
    ]
  }
}
```

---

## 🔒 رموز الأخطاء (Error Codes)

| الكود | الوصف |
|------|-------|
| `VALIDATION_ERROR` | خطأ في التحقق من البيانات |
| `UNAUTHORIZED` | غير مصرح (بدون تسجيل دخول) |
| `FORBIDDEN` | ممنوع (صلاحيات غير كافية) |
| `NOT_FOUND` | المورد غير موجود |
| `USER_EXISTS` | اسم المستخدم موجود بالفعل |
| `EMAIL_EXISTS` | البريد موجود بالفعل |
| `RATE_LIMIT_EXCEEDED` | تم تجاوز حد الطلبات |
| `INTERNAL_ERROR` | خطأ في الخادم |

---

## 📝 ملاحظات مهمة

1. **Authentication**: جميع المسارات المحمية تحتاج رمز الجلسة (Session Cookie)
2. **Rate Limiting**: تحديد 5 محاولات تسجيل دخول كل 5 دقائق
3. **File Upload**: الحد الأقصى لحجم الملف 50 MB
4. **Pagination**: الحد الأقصى للعناصر في الصفحة 100
5. **Timestamps**: جميع الأوقات في صيغة ISO 8601 UTC

---

*آخر تحديث: 13 نوفمبر 2025*
