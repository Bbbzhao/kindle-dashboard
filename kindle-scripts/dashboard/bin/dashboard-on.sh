#!/bin/sh
# 启动仪表盘模式：创建自启标志 + 后台启动keepalive.sh（防待机+防屏保）
# 创建开机自启标志（重启Kindle后自动进入仪表盘模式）
touch /mnt/us/dashboard/keepalive_autostart 2>/dev/null
# setsid脱离KUAL进程组后台启动（否则KUAL退出时keepalive被一起杀掉）
setsid /mnt/us/dashboard/bin/keepalive.sh --no-delay </dev/null >/dev/null 2>&1 &
echo "仪表盘守护已后台启动"
