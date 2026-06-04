import os

def write_gbk(filename, content):
    with open(filename, 'w', encoding='gbk') as f:
        f.write(content)

start_content = '@echo off\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0一键启动.ps1"\n'
stop_content = '@echo off\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0一键关闭.ps1"\n'
restart_content = '@echo off\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0一键重启.ps1"\n'

write_gbk('一键启动.bat', start_content)
write_gbk('一键关闭.bat', stop_content)
write_gbk('一键重启.bat', restart_content)
print("Saved bat launchers as GBK.")
