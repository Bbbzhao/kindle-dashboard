# -*- coding: utf-8 -*-
"""Kindle Dashboard 推送脚本（参考 kindle2workbuddy）
解决SSH不稳定：使用 SSH ControlMaster 连接复用 + 重试机制。
一次SSH连接完成 传输+eips刷新，避免多次连接导致断开。
"""
import os
import sys
import json
import time
import socket
import subprocess
import platform
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from settings import (
    KINDLE_HOST, KINDLE_PORT, KINDLE_USER, KINDLE_REMOTE,
    SSH_KEY, EIPS_PATH, SSH_TIMEOUT, SSH_RETRIES, SSH_RETRY_DELAY,
)
from render import render

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PNG = OUTPUT_DIR / "dashboard.png"
LOG_FILE = OUTPUT_DIR / "refresh.log"

# Windows隐藏子进程窗口
NO_WINDOW = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

# SSH公共选项（去掉ControlMaster，Kindle的dropbear不支持）
SSH_OPTS = [
    "-i", os.path.expanduser(SSH_KEY),
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", f"ConnectTimeout={SSH_TIMEOUT}",
    "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=3",
]


def log(msg):
    """记录日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_bin(name):
    """查找ssh可执行文件（优先Git Bash版，Windows OpenSSH密钥权限检查过严）"""
    candidates = [
        f"C:/Program Files/Git/usr/bin/{name}.exe",
        f"C:/Windows/System32/OpenSSH/{name}.exe",
        name,
    ]
    for c in candidates:
        try:
            subprocess.run([c, "-V"], capture_output=True, timeout=5, creationflags=NO_WINDOW)
            return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return name


def tcp_port_open(host, port=22, timeout=3):
    """TCP端口探测，比ping可靠（Kindle常不回ping但SSH端口开着）"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def ssh_run(host, command, retries=None, timeout=30, stdin_data=None):
    """执行SSH命令，带重试机制"""
    if retries is None:
        retries = SSH_RETRIES

    ssh_bin = find_bin("ssh")
    cmd = [ssh_bin] + SSH_OPTS + ["-p", str(KINDLE_PORT), f"{KINDLE_USER}@{host}", command]

    for attempt in range(1, retries + 1):
        try:
            if stdin_data is not None:
                r = subprocess.run(cmd, input=stdin_data, capture_output=True,
                                   timeout=timeout, creationflags=NO_WINDOW)
            else:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=timeout, creationflags=NO_WINDOW)
            if r.returncode == 0:
                return True, r.stdout
            log(f"SSH尝试{attempt}/{retries}失败: {r.stderr.strip()[:150]}")
        except subprocess.TimeoutExpired:
            log(f"SSH尝试{attempt}/{retries}超时")
        except Exception as e:
            log(f"SSH尝试{attempt}/{retries}异常: {e}")

        if attempt < retries:
            time.sleep(SSH_RETRY_DELAY)

    return False, ""


BATTERY_FILE = OUTPUT_DIR / "battery.json"


def get_kindle_battery(host, timeout=12):
    """查询Kindle电量与充电状态（SSH），结果缓存到 output/battery.json"""
    # 遍历电源设备读 capacity/status（兼容不同型号路径）
    cmd = (
        "for d in /sys/class/power_supply/*; do "
        "c=$(cat $d/capacity 2>/dev/null); "
        "s=$(cat $d/status 2>/dev/null); "
        "if [ -n \"$c\" ]; then echo \"${c}|${s}\"; break; fi; "
        "done"
    )
    ok, out = ssh_run(host, cmd, retries=1, timeout=timeout)
    result = {"level": None, "charging": None, "status": None, "ok": False, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}

    if ok:
        out = (out or "").strip().splitlines()
        for line in out:
            if "|" in line:
                level_s, status_s = line.split("|", 1)
                try:
                    result["level"] = int(level_s.strip())
                except (ValueError, TypeError):
                    continue
                result["status"] = status_s.strip()
                result["charging"] = result["status"] == "Charging"
                result["ok"] = True
                break

    # 缓存写入（GUI读取）
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        BATTERY_FILE.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    if result["ok"]:
        log(f"Kindle电量: {result['level']}% {result['status']}")
    else:
        log("Kindle电量查询失败")
    return result


def push_and_refresh(host):
    """base64+stdin传输 + eips刷新，合并为单次SSH连接（避免dropbear频率限制）"""
    import base64

    # 1. 检查Kindle在线（TCP/22）
    if not tcp_port_open(host):
        log(f"Kindle不在线: {host}")
        return False
    log(f"Kindle在线: {host}")

    # 2. base64编码图片
    with open(OUTPUT_PNG, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode()
    log(f"图片已编码: {len(b64_data)}字符")

    # 3. 单次连接完成：传输+刷新（framework stop由keepalive管理，避免系统不稳）
    remote_cmd = (
        f"base64 -d > {KINDLE_REMOTE} && "
        f"{EIPS_PATH} -f -g {KINDLE_REMOTE} && echo REFRESH_OK"
    )
    log(f"传输+刷新 → {KINDLE_USER}@{host}")
    ok, out = ssh_run(host, remote_cmd, timeout=60, stdin_data=b64_data.encode())
    if not ok or "REFRESH_OK" not in str(out):
        log(f"失败: {str(out)[:150]}")
        return False
    log("传输+刷新成功")
    return True


def main():
    """主函数"""
    log("=" * 50)
    log("开始刷新dashboard")

    # 0. 查询Kindle电量/充电状态（渲染到仪表盘+缓存供GUI）
    battery = get_kindle_battery(KINDLE_HOST)

    # 1. 渲染图片（1024×758横屏，右上角含电量）
    png = render(battery)
    log(f"渲染完成: {png}")

    # 2. 推送到Kindle（带重试）
    success = push_and_refresh(KINDLE_HOST)

    if success:
        log("全部完成")
        return 0
    else:
        log("推送失败，将在下个周期重试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
