#!/bin/sh
# Kindle仪表盘守护：防待机 + 防屏保（锁屏）
# 原理：
#   1. deferSuspend 999999999：无限延迟待机（拦截readyToSuspend）
#   2. preventScreenSaver 1：禁用屏保（锁屏）
#   3. 定期eips刷新仪表盘：即使屏保出现，10秒内被覆盖回仪表盘
#   4. 所有设置每10秒重置一次（防止被powerd/系统重置）

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

log "仪表盘守护启动（防待机+防屏保模式）"

# 主循环：定期执行所有防护设置
while true; do
  # 防屏保（锁屏）——每轮重置，防止被powerd清除
  lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
  # 防待机——保持deferSuspend大值
  lipc-set-prop com.lab126.powerd deferSuspend 999999999 2>/dev/null

  # 确保dropbear运行（SSH保活）
  if ! pidof dropbear >/dev/null 2>&1; then
    /usr/sbin/dropbear -p 22 -r /mnt/us/usbnet/etc/dropbear_rsa_host_key 2>/dev/null || \
    /usr/sbin/dropbear -p 22 2>/dev/null
    log "dropbear已启动"
  fi

  # 定期刷新仪表盘（覆盖可能出现的屏保/锁屏画面）
  if [ -f /mnt/us/dashboard.png ]; then
    /usr/sbin/eips -g /mnt/us/dashboard.png 2>/dev/null
  fi

  # 每10秒一轮
  sleep 10
done
