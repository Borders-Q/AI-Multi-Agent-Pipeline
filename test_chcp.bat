@echo off
chcp 65001 >nul
goto :main

:main
echo [1/3] 启动后端服务 (FastAPI)...
cd /d "%~dp0"
start "天韬（SkyT）_Backend" /min cmd /c "python -m uvicorn server:app --host 0.0.0.0 --port 8000"
