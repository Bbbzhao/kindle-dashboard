#!/bin/sh
# 退出仪表盘模式：恢复framework，回到正常Kindle界面
# 停止keepalive守护（如有）
pkill -f keepalive.sh 2>/dev/null
pkill -f "echo mem" 2>/dev/null
# 清除RTC唤醒
echo 0 > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
# 恢复framework
/etc/init.d/framework start
echo "已退出仪表盘模式，Kindle恢复原生界面"
