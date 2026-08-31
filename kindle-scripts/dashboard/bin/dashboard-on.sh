#!/bin/sh
# 启动仪表盘模式：framework stop + 防睡眠 + RTC自动唤醒
# 直接运行keepalive.sh（前台阻塞运行）
exec /mnt/us/dashboard/bin/keepalive.sh
