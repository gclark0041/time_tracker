@echo off
echo ===================================
echo Building Time Tracker Application
echo ===================================

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Create a database if it doesn't exist
echo Setting up database...
python -c "from app import db; db.create_all()"

:: Build the application using PyInstaller
echo Building executable...
pyinstaller TimeTracker.spec

echo ===================================
echo Build complete! 
echo Application is in the "dist\TimeTracker" folder
echo ===================================
pause
