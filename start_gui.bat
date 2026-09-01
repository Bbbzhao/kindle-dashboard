@echo off
title Kindle Dashboard 控制面板
cd /d D:\kindle-dashboard
echo ========================================
echo   Kindle Dashboard 控制面板
echo ========================================
echo 正在启动服务...
REM 停止旧GUI（防止端口冲突）
if exist output\gui.pid (
    set /p OLDPID=<output\gui.pid
    taskkill /F /PID %OLDPID% >nul 2>&1
)
REM 启动GUI（无窗口后台运行）
start "" "C:\Users\ake\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe" gui.py
REM 等待服务就绪（最多10秒）
set /a COUNT=0
:WAIT
timeout /t 1 /nobreak >nul
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul
if %errorlevel%==0 goto READY
set /a COUNT+=1
if %COUNT% lss 10 goto WAIT
echo [错误] 服务启动失败！请查看 output\gui_server.log
timeout /t 5 >nul
exit
:READY
echo 服务已启动，正在打开浏览器...
start http://localhost:8080
echo 浏览器已打开，本窗口可关闭，服务在后台运行。
timeout /t 3 >nul
exit
