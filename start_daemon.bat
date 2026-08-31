@echo off
chcp 65001 >nul
title Kindle Dashboard 守护进程
cd /d D:\kindle-dashboard
C:\Users\ake\.workbuddy\binaries\python\envs\default\Scripts\python.exe daemon.py
pause
