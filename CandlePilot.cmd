@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "CP_PY=py -3"
) else (
    set "CP_PY=python"
)
%CP_PY% -c "import kiteconnect, keyring" >nul 2>nul
if errorlevel 1 (
    echo Installing Candle Pilot dependencies for this Windows user...
    %CP_PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed. Check Python and network access.
        pause
        exit /b 1
    )
)
%CP_PY% desktop.py
if errorlevel 1 pause
