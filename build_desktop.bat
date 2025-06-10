@echo off
echo Building Time Tracker Desktop Application...
echo.
python build_desktop.py
echo.
if %ERRORLEVEL% EQU 0 (
    echo Build completed successfully!
    echo The application is available in the "dist\TimeTracker" folder.
) else (
    echo Build failed. Please check the error messages above.
)
pause
