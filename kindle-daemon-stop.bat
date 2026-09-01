@echo off
title Kindle Daemon Stop
cd /d D:\kindle-dashboard
echo ========================================
echo   停止 Kindle Dashboard 守护进程
echo ========================================
echo 正在停止守护进程（保留GUI控制面板）...
REM 写停止标志（daemon检测后优雅退出，GUI保留可继续查看状态）
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
goto DONE
:DONE
echo 守护进程已停止。
echo 控制面板仍可访问: http://localhost:8080
echo 如需重新启动: kindle-daemon-start.bat
timeout /t 3 >nul
exit
