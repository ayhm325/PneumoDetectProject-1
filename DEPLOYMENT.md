# 🚀 دليل النشر والتطبيق - PneumoDetect

## جدول المحتويات
1. [المتطلبات](#المتطلبات)
2. [التطوير المحلي](#التطوير-المحلي)
3. [النشر باستخدام Docker](#النشر-باستخدام-docker)
4. [النشر على الخادم](#النشر-على-الخادم)
5. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## 📋 المتطلبات

### الحد الأدنى
- Python 3.10+
- pip و virtualenv
- 4GB RAM (للنموذج الكامل)
- 5GB مساحة تخزين

### لـ GPU (اختياري)
- NVIDIA GPU مع CUDA 12.1
- cuDNN 8.x
- PyTorch GPU version

### للإنتاج
- Docker و Docker Compose
- PostgreSQL 14+
- Redis 7+
- Nginx (للـ reverse proxy)

---

## 🛠️ التطوير المحلي

### 1. استنساخ المشروع
```bash
git clone https://github.com/AyhmObeidat/PneumoDetect.git
cd PneumoDetect
```

### 2. إنشاء بيئة افتراضية
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. تثبيت المتطلبات
```bash
# المتطلبات الأساسية
pip install -r requirements.txt

# متطلبات التطوير (اختيارية)
pip install -r requirements-dev.txt
```

### 4. إعداد المتغيرات البيئية
```bash
# انسخ ملف المثال
cp .env.example .env

# عدّل .env بمتغيراتك
# تأكد من تعيين:
# - FLASK_ENV=development
# - HF_TOKEN (من Hugging Face)
```

### 5. تشغيل التطبيق
```bash
python run.py
```

سيكون التطبيق متاح على: `http://localhost:5000`

### 6. تشغيل الاختبارات
```bash
pytest tests/ -v --cov=app
```

---

## 🐳 النشر باستخدام Docker

### 1. بناء الصور
```bash
# بناء صورة التطبيق
docker build -t pneumodetect:latest .

# أو استخدام docker-compose
docker-compose build
```

### 2. تشغيل التطبيق
```bash
# إنشاء ملف .env.docker
cat > .env.docker << EOF
FLASK_ENV=production
SECRET_KEY=your-strong-secret-key
DB_USER=pneumodetect
DB_PASSWORD=secure-password
HF_TOKEN=your-token
EOF

# تشغيل الخدمات
docker-compose up -d
```

### 3. التحقق من الحالة
```bash
# عرض السجلات
docker-compose logs -f web

# التحقق من الصحة
curl http://localhost:5000/health
```

### 4. إيقاف الخدمات
```bash
docker-compose down
```

---

## 🌍 النشر على الخادم

### على Ubuntu/Debian

#### 1. إعداد الخادم
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت المتطلبات
sudo apt install -y python3.11 python3-pip python3-venv
sudo apt install -y postgresql postgresql-contrib redis-server nginx
```

#### 2. إنشاء مستخدم التطبيق
```bash
sudo useradd -m -s /bin/bash pneumodetect
sudo usermod -aG www-data pneumodetect
```

#### 3. نسخ المشروع
```bash
cd /home/pneumodetect
sudo git clone https://github.com/AyhmObeidat/PneumoDetect.git
sudo chown -R pneumodetect:pneumodetect /home/pneumodetect/PneumoDetect
```

#### 4. إعداد البيئة الافتراضية
```bash
cd /home/pneumodetect/PneumoDetect
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. إعداد قاعدة البيانات
```bash
sudo -u postgres createdb pneumodetect
sudo -u postgres createuser pneumodetect
# عيّن كلمة المرور...
```

#### 6. تهيئة قاعدة البيانات
```bash
# من داخل virtualenv
flask db upgrade
```

#### 7. إنشاء خدمة systemd
```bash
sudo tee /etc/systemd/system/pneumodetect.service > /dev/null <<EOF
[Unit]
Description=PneumoDetect Web Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=pneumodetect
WorkingDirectory=/home/pneumodetect/PneumoDetect
Environment="PATH=/home/pneumodetect/PneumoDetect/venv/bin"
ExecStart=/home/pneumodetect/PneumoDetect/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 run:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pneumodetect
sudo systemctl start pneumodetect
```

#### 8. إعداد Nginx
```bash
sudo tee /etc/nginx/sites-available/pneumodetect > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }

    location /uploads {
        alias /home/pneumodetect/PneumoDetect/uploads;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/pneumodetect /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. إعداد SSL (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: "ModuleNotFoundError"
**الحل:**
```bash
# تأكد من تفعيل البيئة الافتراضية
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# أعد تثبيت المتطلبات
pip install --force-reinstall -r requirements.txt
```

### المشكلة: "Database connection refused"
**الحل:**
```bash
# تحقق من حالة قاعدة البيانات
sudo systemctl status postgresql

# أعد تشغيل قاعدة البيانات
sudo systemctl restart postgresql
```

### المشكلة: "Model download failed"
**الحل:**
```bash
# تأكد من تعيين HF_TOKEN
export HF_TOKEN=your-token

# حاول التحميل يدوياً
python -c "
from transformers import AutoModel
model = AutoModel.from_pretrained('dima806/chest_xray_pneumonia_detection')
"
```

### المشكلة: "GPU not detected"
**الحل:**
```bash
# تحقق من الـ GPU
python -c "import torch; print(torch.cuda.is_available())"

# أعد تثبيت PyTorch مع CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### عرض السجلات
```bash
# في التطوير
tail -f app.log

# في docker
docker-compose logs -f web

# في systemd
sudo journalctl -u pneumodetect -f
```

---

## 📊 المراقبة والصيانة

### المراقبة
```bash
# تحقق من الصحة
curl http://localhost:5000/health

# عرض معلومات النظام (للمدير)
curl -H "Cookie: session=..." http://localhost:5000/api/system-info
```

### النسخ الاحتياطية
```bash
# نسخ احتياطية من قاعدة البيانات
pg_dump pneumodetect > backup_$(date +%Y%m%d).sql

# نسخ احتياطية من الملفات المرفوعة
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

### التنظيف
```bash
# حذف الملفات المؤقتة
rm -rf __pycache__ .pytest_cache

# تنظيف قاعدة البيانات
python -c "from app import db; db.create_all()"
```

---

## 🔐 أفضل الممارسات الأمنية

1. **لا تستخدم `debug=True` في الإنتاج**
2. **عيّن SECRET_KEY قوي**
3. **استخدم HTTPS في الإنتاج**
4. **حدّث المكتبات بانتظام**
5. **راجع سجلات الأمان**
6. **استخدم جدران الحماية (Firewall)**
7. **قيّد أذونات الملفات**

---

## 📞 الدعم والمساعدة

- 📧 البريد الإلكتروني: support@pneumodetect.com
- 🐛 تقارير الأخطاء: GitHub Issues
- 💬 المناقشات: GitHub Discussions

---

**آخر تحديث:** 15 نوفمبر 2025
