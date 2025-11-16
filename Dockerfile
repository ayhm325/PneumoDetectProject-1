# استخدم صورة Python 3.11
FROM python:3.11-slim

# عيّن متغير البيئة للتطبيق
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# اضبط دليل العمل
WORKDIR /app

# ثبّت المتطلبات النظامية
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# انسخ متطلبات Python
COPY requirements.txt .

# ثبّت متطلبات Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# انسخ رمز التطبيق
COPY . .

# كشف المنفذ
EXPOSE 5000

# أمر البدء
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "run:app"]
