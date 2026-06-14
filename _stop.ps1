$ErrorActionPreference = "Continue"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8



$Host.UI.RawUI.WindowTitle = "天韬（SkyT） 系统 - 一键关闭"



Write-Host "==================================="

Write-Host "       天韬（SkyT） 系统 - 一键关闭"

Write-Host "==================================="



Write-Host "正在关闭后台服务(端口8000, 5173, 8001)..." -ForegroundColor Yellow

Get-NetTCPConnection -LocalPort 8000, 5173, 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Where-Object { $_ -ne 0 -and $_ -ne $PID } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }



Write-Host "正在清理附属残留进程..." -ForegroundColor Yellow

Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue



Write-Host "正在关闭 天韬（SkyT） 专属浏览器页面..." -ForegroundColor Yellow

# 1. 安全且精确地关闭浏览器中的 天韬（SkyT） 窗口（绝不会关闭您的 IDE 或其他不相干窗口）

Get-Process msedge, chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*天韬（SkyT）*' } | ForEach-Object {

    $_.CloseMainWindow() | Out-Null

    Start-Sleep -Milliseconds 200

    if (!$_.HasExited) {

        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue

    }

}

# 2. 清理后台专属 Profile 残留（不影响默认浏览器）

Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*skyt_edge_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }



Write-Host "===================================" -ForegroundColor Green

Write-Host "  所有系统服务已彻底停止，相关网页已关闭" -ForegroundColor Green

Write-Host "===================================" -ForegroundColor Green

Write-Host "本窗口将在 3 秒后自动关闭..." -ForegroundColor Magenta



Start-Sleep -Seconds 3

exit

