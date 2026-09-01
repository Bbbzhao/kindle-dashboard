#!/bin/sh
# 退出仪表盘模式：恢复framework，回到正常Kindle界面（KUAL）
# 停止keepalive守护（正则技巧避免匹配自身命令）
pkill -f '[k]eepalive.sh' 2>/dev/null
pkill -f '[l]ipc-wait-event' 2>/dev/null
# 清除RTC唤醒
echo 0 > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
# 恢复framework（upstart命令在/sbin，SSH shell的PATH不含/sbin需用完整路径）
/sbin/start framework 2>/dev/null
# 唤醒屏幕（E-ink需要刷新事件才重绘原生界面）
lipc-set-prop com.lab126.powerd wakeUp 1 2>/dev/null
echo "已退出仪表盘模式，Kindle恢复原生界面"
