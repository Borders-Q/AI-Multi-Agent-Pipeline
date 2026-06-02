# Ai Multi Agent Start Script (Optimized)
# Uses uvicorn module call instead of server.py direct execution for faster startup

$ErrorActionPreference = "SilentlyContinue"

# Start all services in parallel
$server = Start-Process python -ArgumentList "-m uvicorn server:app --host 0.0.0.0 --port 8000" -WorkingDirectory "g:\Ai Multi Agent" -PassThru -WindowStyle Hidden
$frontend = Start-Process cmd -ArgumentList "/c cd /d g:\Ai Multi Agent\frontend && npm run dev -- --host 127.0.0.1" -PassThru -WindowStyle Hidden
$registry = Start-Process python -ArgumentList "registry_server.py" -WorkingDirectory "g:\Ai Multi Agent" -PassThru -WindowStyle Hidden

$pids = @{
    server_pid = $server.Id
    frontend_pid = $frontend.Id
    registry_pid = $registry.Id
}
$pids | ConvertTo-Json | Set-Content -Path "g:\Ai Multi Agent\skyt_pids.json"
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
