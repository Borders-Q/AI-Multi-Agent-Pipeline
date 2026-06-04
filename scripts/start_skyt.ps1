# Ai Multi Agent Start Script (Optimized)
# Uses project .venv when available, then falls back to system Python.

$ErrorActionPreference = "SilentlyContinue"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $projectRoot "frontend"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
    Write-Output "Project .venv not found. Run 一键安装依赖.bat first, or ensure system Python has all dependencies."
}

# Start all services in parallel
$server = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden
$frontend = Start-Process -FilePath "cmd" -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden
$registry = Start-Process -FilePath $pythonExe -ArgumentList "registry_server.py" -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden

$pids = @{
    server_pid = $server.Id
    frontend_pid = $frontend.Id
    registry_pid = $registry.Id
}
$pids | ConvertTo-Json | Set-Content -Path (Join-Path $projectRoot "skyt_pids.json")
Write-Output "Ai Multi Agent started with PIDs: $($server.Id), $($frontend.Id), $($registry.Id)"

# Wait for backend (usually ready in 2-3s now with lazy loading)
Write-Output "Waiting for backend..."
$retryCount = 0
while ($retryCount -lt 30) {
    $listening = netstat -ano 2>$null | Select-String "LISTENING" | Select-String ":8000"
    if ($listening) {
        Write-Output "  Backend ready!"
        break
    }
    Start-Sleep -Milliseconds 500
    $retryCount++
}

# Wait for frontend
Write-Output "Waiting for frontend..."
$retryCount = 0
while ($retryCount -lt 30) {
    $listening = netstat -ano 2>$null | Select-String "LISTENING" | Select-String ":5173"
    if ($listening) {
        Write-Output "  Frontend ready!"
        break
    }
    Start-Sleep -Milliseconds 500
    $retryCount++
}

# Open browser
Write-Output "Opening Ai Multi Agent frontend in browser..."
Start-Process msedge -ArgumentList "--app=http://127.0.0.1:5173" -ErrorAction SilentlyContinue
