#!/bin/sh
# 退出仪表盘模式：停止keepalive，恢复framework，回到正常Kindle界面（KUAL）
# 1. 停止keepalive（PID文件方式最可靠）
if [ -f /mnt/us/dashboard/keepalive.pid ]; then
  KPID=$(cat /mnt/us/dashboard/keepalive.pid 2>/dev/null)
  if [ -n "$KPID" ]; then
    kill "$KPID" 2>/dev/null
    log="已停止keepalive (PID $KPID)"
  fi
  rm -f /mnt/us/dashboard/keepalive.pid
fi
# 2. 兜底：pkill（正则技巧避免匹配自身命令）
pkill -f '[k]eepalive.sh' 2>/dev/null
pkill -f '[l]ipc-wait-event' 2>/dev/null
# 3. 清除RTC唤醒
echo 0 > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
# 4. 删除开机自启标志（重启Kindle后保持原生界面，不再进入仪表盘）
rm -f /mnt/us/dashboard/keepalive_autostart 2>/dev/null
# 5. 恢复framework（upstart命令在/sbin，SSH shell的PATH不含/sbin需用完整路径）
/sbin/start framework 2>/dev/null
# 6. 唤醒屏幕（E-ink需要刷新事件才重绘原生界面）
lipc-set-prop com.lab126.powerd wakeUp 1 2>/dev/null
echo "已退出仪表盘模式，Kindle恢复原生界面（重启后不再自动进入仪表盘）"
