@echo off
ECHO Starting Time Tracker Application...
ECHO.
ECHO This will start the Time Tracker server and open it in your browser.
ECHO.

REM Create uploads directory if it doesn't exist
if not exist "uploads" mkdir uploads

REM Set environment variable to indicate desktop mode
SET DESKTOP_MODE=true

REM Start Python script
start /B "" python desktop_launcher.py

ECHO.
ECHO Time Tracker has been launched!
ECHO Please do not close this window while using the application.
ECHO.
