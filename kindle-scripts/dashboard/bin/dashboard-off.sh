#!/bin/sh
# 退出仪表盘模式：恢复framework，回到正常Kindle界面（KUAL）
# 停止keepalive守护（正则技巧避免匹配自身命令）
pkill -f '[k]eepalive.sh' 2>/dev/null
pkill -f '[l]ipc-wait-event' 2>/dev/null
# 清除RTC唤醒
echo 0 > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
# 恢复framework（KPW2为upstart管理，兼容init.d）
start framework 2>/dev/null || /etc/init.d/framework start 2>/dev/null
echo "已退出仪表盘模式，Kindle恢复原生界面"
