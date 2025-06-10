@echo off
echo Starting Time Tracker Pro...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

:: Start the backend server
echo Starting backend server...
start "Time Tracker Backend" cmd /k "cd backend && python app.py"

:: Wait a moment for the server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Open the frontend in the default browser
echo Opening Time Tracker in your browser...
start "" "%CD%\index.html"

echo.
echo Time Tracker Pro is now running!
echo.
echo Backend server: http://localhost:5000
echo Frontend: File opened in your default browser
echo.
echo To stop the application:
echo 1. Close this window
echo 2. Close the backend server window
echo.
pause
