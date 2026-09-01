#!/bin/sh
# Kindle仪表盘守护：利用 deferSuspend 无限延迟待机，让Kindle保持常亮
# 原理：监听 readyToSuspend 事件（进入待机前触发），设置 deferSuspend 大值
#       Kindle永远停留在"Ready to Suspend"状态，不会真正待机，SSH保持可用

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /mnt/us/dashboard/keepalive.log
}

# 开机自启时延迟启动（等待framework启动完成，避免冲突）
# 手动启动时通过参数 --no-delay 跳过延迟
if [ "$1" != "--no-delay" ] && [ -f /mnt/us/dashboard/keepalive_autostart ]; then
  log "开机自启模式，等待45秒让系统启动完成..."
  sleep 45
fi

# 停止framework（防触摸干扰 + 减少系统活动，upstart命令在/sbin需完整路径）
/sbin/stop framework 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
# 防屏保
lipc-set-prop com.lab126.powerd preventScreenSaver 1

log "仪表盘守护启动（deferSuspend防待机模式）"

# 确保dropbear运行
if ! pidof dropbear >/dev/null 2>&1; then
  /usr/sbin/dropbear -p 22 -r /mnt/us/usbnet/etc/dropbear_rsa_host_key 2>/dev/null || \
  /usr/sbin/dropbear -p 22 2>/dev/null
  log "dropbear已启动"
fi

# 主循环：等待readyToSuspend事件并无限延迟待机
while true; do
  # 等待进入待机前的事件（会阻塞直到该事件触发）
  lipc-wait-event -m com.lab126.powerd readyToSuspend 2>/dev/null

  # 进入待机前，无限延迟待机
  lipc-set-prop com.lab126.powerd deferSuspend 999999999 2>/dev/null
  log "已拦截待机，deferSuspend=999999999"

  # 确保dropbear运行
  if ! pidof dropbear >/dev/null 2>&1; then
    /usr/sbin/dropbear -p 22 -r /mnt/us/usbnet/etc/dropbear_rsa_host_key 2>/dev/null || \
    /usr/sbin/dropbear -p 22 2>/dev/null
    log "dropbear已重启"
  fi

  # 显示当前dashboard
  if [ -f /mnt/us/dashboard.png ]; then
    /usr/sbin/eips -f -g /mnt/us/dashboard.png 2>/dev/null
  fi

  sleep 2
done
