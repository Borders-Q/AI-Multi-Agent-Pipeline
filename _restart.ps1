$ErrorActionPreference = "Continue"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8



$Host.UI.RawUI.WindowTitle = "Ai Multi Agent 系统 - 一键重启"

$baseDir = $PSScriptRoot



Write-Host "==================================="

Write-Host "       Ai Multi Agent 系统 - 一键重启"

Write-Host "==================================="



Write-Host "`n【第一阶段：强制清理旧服务】" -ForegroundColor Cyan

Write-Host "正在关闭后台服务(端口8000, 5173, 8001)..."

Get-NetTCPConnection -LocalPort 8000, 5173, 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Where-Object { $_ -ne 0 -and $_ -ne $PID } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }



Write-Host "正在清理附属残留进程..."

Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue



Write-Host "正在关闭残留的专属网页..."

# 1. 安全且精确地关闭浏览器中的 Ai Multi Agent 窗口（绝不会关闭您的 IDE 或其他不相干窗口）

Get-Process msedge, chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*Ai Multi Agent*' } | ForEach-Object {

    $_.CloseMainWindow() | Out-Null

    Start-Sleep -Milliseconds 200

    if (!$_.HasExited) {

        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue

    }

}

# 2. 清理后台专属 Profile 残留（不影响默认浏览器）

Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*skyt_edge_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }



Write-Host "旧服务已彻底清理！正在等待系统释放端口资源..." -ForegroundColor Green

Start-Sleep -Seconds 2



Write-Host "`n【第二阶段：重新启动服务】" -ForegroundColor Cyan

Write-Host "[1/3] 启动后端服务 (FastAPI)..." -ForegroundColor Yellow

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $baseDir -WindowStyle Minimized



Write-Host "[2/3] 启动前端服务 (Vite)..." -ForegroundColor Yellow

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory (Join-Path $baseDir "frontend") -WindowStyle Minimized



Write-Host "[3/3] 启动注册服务器..." -ForegroundColor Yellow

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python", "registry_server.py" -WorkingDirectory $baseDir -WindowStyle Minimized



Write-Host "`n正在等待所有服务(端口8000, 5173, 8001)就绪..." -ForegroundColor Yellow

$maxRetries = 30

for ($i = 0; $i -lt $maxRetries; $i++) {

    $port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue

    $port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

    $port8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue

    if ($port8000 -and $port5173 -and $port8001) {

        break

    }

    Start-Sleep -Milliseconds 500

}



Write-Host "所有服务已完全就绪！" -ForegroundColor Green

Write-Host "正在打开浏览器..." -ForegroundColor Cyan

Start-Process -FilePath "msedge" -ArgumentList "--app=http://127.0.0.1:5173", "--user-data-dir=$env:TEMP\skyt_edge_profile" -ErrorAction SilentlyContinue



Write-Host "==================================="

Write-Host "  Ai Multi Agent 系统已成功重启"

Write-Host "==================================="

Write-Host "1. 请勿关闭弹出的最小化黑色窗口，它们是系统的核心。" -ForegroundColor Magenta

Write-Host "2. 本控制台窗口将在 3 秒后自动关闭..." -ForegroundColor Magenta



Start-Sleep -Seconds 3

exit

