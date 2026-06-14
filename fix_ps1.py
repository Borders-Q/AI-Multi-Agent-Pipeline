import os

def write_utf8_sig(filename, content):
    with open(filename, 'w', encoding='utf-8-sig') as f:
        f.write(content)

start_content = '''$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Host.UI.RawUI.WindowTitle = "天韬（SkyT）_Server_Terminal - 一键启动"
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "       天韬（SkyT） 系统 - 一键启动" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$baseDir = $PSScriptRoot

Write-Host "[1/3] 启动后端服务 (FastAPI)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $baseDir -WindowStyle Minimized

Write-Host "[2/3] 启动前端服务 (Vite)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory "$baseDir\\frontend" -WindowStyle Minimized

Write-Host "[3/3] 启动注册服务器..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "registry_server.py" -WorkingDirectory $baseDir -WindowStyle Minimized

Write-Host "`n正在等待所有服务(端口8000, 5173, 8001)就绪..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    $port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    $port8001 = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    
    if ($port5173 -and $port8000 -and $port8001) {
        Write-Host "所有服务已完全就绪！" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    $retryCount++
}

Write-Host "正在打开浏览器..." -ForegroundColor Yellow
try {
    Start-Process -FilePath "msedge" -ArgumentList "--app=http://127.0.0.1:5173" -ErrorAction Stop
} catch {
    Start-Process -FilePath "http://127.0.0.1:5173"
}

Write-Host "`n===================================" -ForegroundColor Green
Write-Host "  天韬（SkyT） 系统已成功启动" -ForegroundColor Green
Write-Host "  后端: http://localhost:8000"
Write-Host "  前端: http://localhost:5173"
Write-Host "===================================" -ForegroundColor Green
Write-Host "`n1. 所有服务现在均在【独立的最小化窗口】中后台运行！" -ForegroundColor Cyan
Write-Host "2. 您现在可以【安全关闭本黑色窗口】，服务绝不会断开！" -ForegroundColor Cyan
Write-Host "3. 如果想看报错日志，可以在任务栏点开对应的最小化窗口查看。" -ForegroundColor Cyan
Write-Host "4. 如果需要停止服务，请运行 一键关闭.bat。" -ForegroundColor Cyan

Write-Host "`n请按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''

stop_content = '''$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Host.UI.RawUI.WindowTitle = "天韬（SkyT）_Server_Terminal - 一键关闭"
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "       天韬（SkyT） 系统 - 一键关闭" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

function Kill-Port {
    param($Port)
    Write-Host "强制停止端口 $Port 的服务..." -NoNewline
    $process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($process) {
        Stop-Process -Id $process -Force -ErrorAction SilentlyContinue
        Write-Host " 已停止" -ForegroundColor Green
    } else {
        Write-Host " 未占用" -ForegroundColor DarkGray
    }
}

Kill-Port 8000
Kill-Port 5173
Kill-Port 8001

Write-Host "清理残余的控制台与浏览器窗口..." -NoNewline
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Server_Terminal*" -and $_.Id -ne $PID } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Backend*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Frontend*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Registry*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe' AND CommandLine LIKE '%127.0.0.1:5173%'" -ErrorAction SilentlyContinue | Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue
Write-Host " 已清理" -ForegroundColor Green

Write-Host "`n===================================" -ForegroundColor Green
Write-Host "  所有 天韬（SkyT） 服务已彻底强制关闭！" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 3
'''

restart_content = '''$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Host.UI.RawUI.WindowTitle = "天韬（SkyT）_Server_Terminal - 一键重启"
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "       天韬（SkyT） 系统 - 一键重启" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "【第一阶段：强制清理旧服务】" -ForegroundColor Yellow

function Kill-Port {
    param($Port)
    $process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($process) { Stop-Process -Id $process -Force -ErrorAction SilentlyContinue }
}

Kill-Port 8000
Kill-Port 5173
Kill-Port 8001

Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Backend*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Frontend*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）_Registry*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe' AND CommandLine LIKE '%127.0.0.1:5173%'" -ErrorAction SilentlyContinue | Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue
Write-Host "旧服务已彻底清理！" -ForegroundColor Green

Start-Sleep -Seconds 2

Write-Host "`n【第二阶段：重新启动服务】" -ForegroundColor Yellow
Write-Host ""

$baseDir = $PSScriptRoot

Write-Host "[1/3] 启动后端服务 (FastAPI)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $baseDir -WindowStyle Minimized

Write-Host "[2/3] 启动前端服务 (Vite)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory "$baseDir\\frontend" -WindowStyle Minimized

Write-Host "[3/3] 启动注册服务器..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "registry_server.py" -WorkingDirectory $baseDir -WindowStyle Minimized

Write-Host "`n正在等待所有服务(端口8000, 5173, 8001)就绪..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    $port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    $port8001 = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    
    if ($port5173 -and $port8000 -and $port8001) {
        Write-Host "所有服务已完全就绪！" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    $retryCount++
}

Write-Host "正在打开浏览器..."
try {
    Start-Process -FilePath "msedge" -ArgumentList "--app=http://127.0.0.1:5173" -ErrorAction Stop
} catch {
    Start-Process -FilePath "http://127.0.0.1:5173"
}

Write-Host "`n===================================" -ForegroundColor Green
Write-Host "  天韬（SkyT） 系统已成功重启" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host "`n1. 所有服务现在均在【独立的最小化窗口】中后台运行！" -ForegroundColor Cyan
Write-Host "2. 您现在可以【安全关闭本黑色窗口】，服务绝不会断开！" -ForegroundColor Cyan

Write-Host "`n请按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''

write_utf8_sig('_start.ps1', start_content)
write_utf8_sig('_stop.ps1', stop_content)
write_utf8_sig('_restart.ps1', restart_content)
print("Updated all English-named PS1 scripts perfectly with UTF-8 BOM.")
