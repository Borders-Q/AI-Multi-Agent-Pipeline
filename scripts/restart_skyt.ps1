# 天韬（SkyT） Restart Script (Optimized)
$ErrorActionPreference = "SilentlyContinue"

Write-Output "Stopping all 天韬（SkyT） services..."

# Kill by port (fastest and most reliable method)
foreach ($port in @(8000, 5173, 8001)) {
    $lines = netstat -ano 2>$null | Select-String "LISTENING" | Select-String ":$port"
    foreach ($line in $lines) {
        $pid = ($line -split '\s+')[-1]
        if ($pid -match '^\d+$') {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

# Close 天韬（SkyT） browser windows
Get-Process | Where-Object { $_.MainWindowTitle -match "天韬（SkyT）" } | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1
Write-Output "All services stopped. Restarting..."

& "$PSScriptRoot\start_skyt.ps1"
Write-Host "Restart sequence completed."
