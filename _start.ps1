$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8



$Host.UI.RawUI.WindowTitle = "天韬（SkyT） 系统 - 一键启动"

$baseDir = $PSScriptRoot

foreach ($port in @(8000, 5173, 8001)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "端口 $port 已被占用，请先运行 一键关闭.bat 或关闭占用进程。"
    }
}

$venvPython = Join-Path $baseDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    Write-Host "检测到项目虚拟环境，将使用: $pythonExe" -ForegroundColor Green
} else {
    $pythonExe = "python"
    Write-Host "未检测到 .venv，将回退系统 Python。建议先运行：一键安装依赖.bat" -ForegroundColor Yellow
}



Write-Host "==================================="

Write-Host "       天韬（SkyT） 系统 - 一键启动"

Write-Host "==================================="



Write-Host "[1/3] 启动后端服务 (FastAPI)..." -ForegroundColor Yellow

Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $baseDir -WindowStyle Minimized



Write-Host "[2/3] 启动前端服务 (Vite)..." -ForegroundColor Yellow

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory (Join-Path $baseDir "frontend") -WindowStyle Minimized



Write-Host "[3/3] 启动注册服务器..." -ForegroundColor Yellow

Start-Process -FilePath $pythonExe -ArgumentList "registry_server.py" -WorkingDirectory $baseDir -WindowStyle Minimized



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

try {
    $live = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/live" -UseBasicParsing -TimeoutSec 3
    if ($live.StatusCode -ne 200) { throw "后端健康检查失败" }
} catch {
    throw "后端未通过健康检查：$($_.Exception.Message)"
}

Write-Host "本机模式已启用：无需输入访问令牌，后端仅接受本机连接。" -ForegroundColor Cyan



Write-Host "所有服务已完全就绪！" -ForegroundColor Green

Write-Host "正在打开浏览器..." -ForegroundColor Cyan

Start-Process -FilePath "msedge" -ArgumentList "--app=http://127.0.0.1:5173", "--user-data-dir=$env:TEMP\skyt_edge_profile" -ErrorAction SilentlyContinue



Write-Host "==================================="

Write-Host "  天韬（SkyT） 系统已成功启动"

Write-Host "==================================="

Write-Host "1. 请勿关闭弹出的最小化黑色窗口，它们是系统的核心。" -ForegroundColor Magenta

Write-Host "2. 本控制台窗口将在 3 秒后自动关闭..." -ForegroundColor Magenta



Start-Sleep -Seconds 3

exit
