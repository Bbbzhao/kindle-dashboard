@echo off
title Kindle Daemon Stop
cd /d D:\kindle-dashboard
echo ========================================
echo   停止 Kindle Dashboard 守护进程
echo ========================================
echo 正在停止守护进程...
REM 写停止标志（daemon检测后优雅退出，并自动停止GUI）
if not exist output mkdir output
echo stop > output\daemon_stop.flag
REM 等待daemon退出（最多15秒）
set /a COUNT=0
:WAIT
timeout /t 1 /nobreak >nul
if not exist output\daemon_status.json goto DONE
set /p RUNNING=<output\daemon_status.json
echo %RUNNING% | findstr /C:"\"running\": true" >nul
if errorlevel 1 goto DONE
set /a COUNT+=1
if %COUNT% lss 15 goto WAIT
echo 守护进程未响应，强制停止...
if exist output\gui.pid (
    set /p GPID=<output\gui.pid
    taskkill /F /PID %GPID% >nul 2>&1
)
goto DONE
:DONE
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Kindle Daemon*" >nul 2>&1
echo 守护进程已停止，控制面板也已关闭。
timeout /t 2 >nul
exit
