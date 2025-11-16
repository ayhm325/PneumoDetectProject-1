@echo off
REM PneumoDetect - Quick Start Script for Windows
REM استخدام: start.bat

color 0A
echo.
echo ███████████████████████████████████████████████████
echo     🚀 بدء تطبيق PneumoDetect
echo ███████████████████████████████████████████████████
echo.

REM تفعيل البيئة الافتراضية
if not exist "venv" (
    echo 📦 إنشاء بيئة افتراضية...
    python -m venv venv
)

echo ✓ تفعيل البيئة الافتراضية...
call venv\Scripts\activate.bat

echo 📚 تثبيت المتطلبات...
pip install -q -r requirements.txt

REM إنشاء مجلدات ضرورية
if not exist "uploads\originals" mkdir uploads\originals
if not exist "uploads\saliency_maps" mkdir uploads\saliency_maps
if not exist "uploads\temp_saliency" mkdir uploads\temp_saliency
if not exist "logs" mkdir logs
if not exist "instance" mkdir instance

echo.
echo ███████████████████████████████████████████████████
echo     🌐 تشغيل التطبيق...
echo ███████████████████████████████████████████████████
echo.
echo 📍 التطبيق متاح على:
echo    http://localhost:5000
echo.
echo 🔐 حسابات تجريبية:
echo    طبيب: dr_ahmad / pass123
echo    مريض: patient_sami / pass123
echo    مدير: admin / admin123
echo.
echo ⏸️  اضغط Ctrl+C لإيقاف التطبيق
echo.

python run.py

pause
