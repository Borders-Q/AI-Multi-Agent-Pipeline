@set "@x=0" /*
@powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression ((Get-Content '%~f0' -Encoding UTF8) -join [Environment]::NewLine)"
@exit /b */
Write-Host '中文输出测试！' -ForegroundColor Cyan
Write-Host '这是 PowerShell 代码！' -ForegroundColor Green
