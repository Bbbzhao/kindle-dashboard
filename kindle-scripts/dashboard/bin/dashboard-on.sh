#!/bin/sh
# 启动仪表盘模式：创建自启标志 + 运行keepalive.sh（防待机守护）
# 创建开机自启标志（重启Kindle后自动进入仪表盘模式）
touch /mnt/us/dashboard/keepalive_autostart 2>/dev/null
# 运行keepalive.sh（前台阻塞运行）
exec /mnt/us/dashboard/bin/keepalive.sh --no-delay
