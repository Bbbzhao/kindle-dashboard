# -*- coding: utf-8 -*-
"""Windows计划任务一键安装脚本（参考 kindle2workbuddy）
管理员PowerShell运行：& "D:\kindle-dashboard\install_task.ps1"
"""
$ErrorActionPreference = "Stop"

# 项目路径（自动检测当前脚本所在目录）
$ProjectDir = $PSScriptRoot
$PythonExe = "C:\Users\ake\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
$DaemonPy = Join-Path $ProjectDir "kindle-daemon.py"

Write-Host "=== Kindle Dashboard 计划任务安装 ===" -ForegroundColor Cyan
Write-Host "项目目录: $ProjectDir"
Write-Host "Python: $PythonExe"

# 1. 清理旧计划任务
$OldTasks = @("KindleDashboardDaemon", "KindleDashboardPush", "WorkBuddy Kindle Dashboard Refresh")
foreach ($task in $OldTasks) {
    $existing = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "删除旧计划任务: $task" -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $task -Confirm:$false
    }
}

# 2. 创建新计划任务
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$DaemonPy`"" -WorkingDirectory $ProjectDir

# 开机启动 + 唤醒恢复 + 防重复实例
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# 以当前用户身份运行
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Write-Host "注册计划任务: KindleDashboardPush" -ForegroundColor Green
Register-ScheduledTask -TaskName "KindleDashboardPush" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force

# 3. 立即启动一次
Write-Host "立即启动任务..." -ForegroundColor Green
Start-ScheduledTask -TaskName "KindleDashboardPush"

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Cyan
Write-Host "计划任务已注册: KindleDashboardPush"
Write-Host "开机自动启动 + 崩溃自动重启"
Write-Host ""
Write-Host "手动停止: Stop-ScheduledTask -TaskName KindleDashboardPush"
Write-Host "手动查看日志: $ProjectDir\output\refresh.log"
