@echo off
chcp 65001 >nul
title Kindle Dashboard 控制面板
cd /d D:\kindle-dashboard
REM 无窗口运行GUI服务（pythonw.exe），启动后自动打开浏览器
echo 正在启动 Kindle Dashboard 控制面板...
C:\Users\ake\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe gui.py
REM 自动打开浏览器
start http://localhost:8080
exit
