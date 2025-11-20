@echo off
REM PneumoDetect Startup Script for Windows

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   PneumoDetect - Windows Startup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error creating virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error activating virtual environment
    pause
    exit /b 1
)

REM Install/upgrade requirements
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error installing requirements
    pause
    exit /b 1
)

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "instance" mkdir instance

REM Set environment variables
set FLASK_APP=run.py
set FLASK_ENV=development
set SKIP_ML=1
set SEED_DEMO=1

REM Run the application
echo.
echo ========================================
echo   Starting PneumoDetect...
echo.
echo   URL: http://localhost:5000
echo.
echo   Test accounts:
echo   - Doctor:  dr_ahmad / pass123
echo   - Patient: patient_sami / pass123
echo   - Admin:   admin / admin123
echo ========================================
echo.

python run.py

pause
