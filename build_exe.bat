@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Kerala PSC Coach - Windows EXE build
echo ========================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher not found. Install Python 3.10+ from python.org and retry.
    goto :failed
)

py -3 -m pip install --upgrade pip
if errorlevel 1 goto :failed
py -3 -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed

echo.
echo Running tests...
py -3 -m unittest discover -s tests -v
if errorlevel 1 goto :failed

echo.
echo Building the one-file Windows app...
py -3 -m PyInstaller --clean --noconfirm --onefile --windowed --name KeralaPSCCoach PSCapp.pyw
if errorlevel 1 goto :failed

echo.
echo Build complete:
echo   %~dp0dist\KeralaPSCCoach.exe
echo.
pause
exit /b 0

:failed
echo.
echo Build failed. Read the error above, then retry.
pause
exit /b 1
