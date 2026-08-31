#!/bin/sh
#
# ;usbnetwork command script
#
# $Id: usbnetwork.sh 11150 2014-11-23 20:44:26Z NiLuJe $
#
##

USBNET_BASEDIR="/mnt/us/usbnet"
USBNET_BINDIR="${USBNET_BASEDIR}/bin"
USBNET_SCRIPT="${USBNET_BINDIR}/usbnetwork"

# Kindle Dashboard autostart（开机自启防待机守护）
if [ -f /mnt/us/dashboard/keepalive_autostart ] && [ -x /mnt/us/dashboard/bin/keepalive.sh ]; then
    if ! pidof keepalive.sh > /dev/null 2>&1; then
        nohup /mnt/us/dashboard/bin/keepalive.sh > /dev/null 2>&1 &
    fi
fi

# If we're an unprivileged user, try to remedy that...
if [ "$(id -u)" -ne 0 -a -x "/var/local/mkk/gandalf" ] ; then
	exec /var/local/mkk/su -s /bin/ash -c ${USBNET_SCRIPT}
else
	exec ${USBNET_SCRIPT}
fi

return 0
