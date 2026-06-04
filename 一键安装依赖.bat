@echo off
chcp 65001 >nul
setlocal

pushd "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_dependencies.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
    echo Dependency installation failed. Exit code: %EXIT_CODE%
) else (
    echo Dependency installation completed.
)
echo.
pause
popd
exit /b %EXIT_CODE%
