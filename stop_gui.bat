@echo off
chcp 65001 >nul
title 停止 Kindle Dashboard 控制面板
cd /d D:\kindle-dashboard
set /p PID=<output\gui.pid
if defined PID (
    taskkill /F /PID %PID% >nul 2>&1
    if %errorlevel%==0 (
        echo Kindle Dashboard 控制面板已停止
    ) else (
        echo 进程可能已停止，尝试清理残留...
        taskkill /F /IM pythonw.exe >nul 2>&1
    )
) else (
    echo 未找到GUI进程记录
)
timeout /t 2 >nul
exit
