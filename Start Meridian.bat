@echo off
title Meridian Financial
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 launcher.py
    goto :done
)
where python >nul 2>nul
if %errorlevel%==0 (
    python launcher.py
    goto :done
)

echo.
echo Meridian needs Python 3.11 or newer, and none was found on this computer.
echo.
echo   1. Download it from https://www.python.org/downloads/
echo   2. Run the installer and tick "Add python.exe to PATH"
echo   3. Double-click "Start Meridian.bat" again
echo.
pause

:done
