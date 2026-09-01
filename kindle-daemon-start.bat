@echo off
title Kindle Daemon
cd /d D:\kindle-dashboard
echo ========================================
echo   Kindle Dashboard 守护进程
echo ========================================
echo 正在启动守护进程（含GUI控制面板）...
REM 启动daemon（无窗口），自动拉起GUI
start "" "C:\Users\ake\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe" kindle-daemon.py
REM 等待就绪
timeout /t 5 /nobreak >nul
echo 守护进程已启动！
echo 控制面板: http://localhost:8080
echo 本窗口可关闭，服务在后台运行。
timeout /t 3 >nul
exit
