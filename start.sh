#!/bin/bash
# PneumoDetect - Quick Start Script
# استخدام: ./start.sh أو bash start.sh

echo "🚀 بدء PneumoDetect..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# تفعيل البيئة الافتراضية
if [ ! -d "venv" ]; then
    echo "📦 إنشاء بيئة افتراضية..."
    python3 -m venv venv
fi

# تفعيل البيئة
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# تثبيت المتطلبات
echo "📚 تثبيت المتطلبات..."
pip install -q -r requirements.txt

# إنشاء مجلدات ضرورية
mkdir -p uploads/originals uploads/saliency_maps uploads/temp_saliency
mkdir -p logs instance

# تشغيل التطبيق
echo "🌐 تشغيل التطبيق..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 التطبيق متاح على: http://localhost:5000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python run.py
