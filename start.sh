#!/bin/bash
# PneumoDetect Startup Script for Linux/Mac

echo ""
echo "========================================"
echo "  PneumoDetect - Linux/Mac Startup"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error creating virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error activating virtual environment"
    exit 1
fi

# Install/upgrade requirements
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing requirements"
    exit 1
fi

# Create necessary directories
mkdir -p uploads
mkdir -p instance

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=development
export SKIP_ML=1
export SEED_DEMO=1

# Run the application
echo ""
echo "========================================"
echo "  Starting PneumoDetect..."
echo ""
echo "  URL: http://localhost:5000"
echo ""
echo "  Test accounts:"
echo "  - Doctor:  dr_ahmad / pass123"
echo "  - Patient: patient_sami / pass123"
echo "  - Admin:   admin / admin123"
echo "========================================"
echo ""

python run.py
