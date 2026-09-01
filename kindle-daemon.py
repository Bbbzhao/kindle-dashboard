# -*- coding: utf-8 -*-
"""Kindle Dashboard 守护进程（参考 kindle2workbuddy）
每 REFRESH_INTERVAL 秒调用 refresh.py 刷新一次。
启动时自动拉起GUI控制面板（8080端口），停止时同时停止GUI。
支持GUI控制：检测停止标志文件，写入运行状态。
"""
import os
import sys
import json
import time
import socket
import subprocess
import platform
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from settings import REFRESH_INTERVAL
from refresh import main as refresh_dashboard, log

OUTPUT_DIR = BASE_DIR / "output"
STOP_FLAG = OUTPUT_DIR / "daemon_stop.flag"
STATUS_FILE = OUTPUT_DIR / "daemon_status.json"
GUI_PID_FILE = OUTPUT_DIR / "gui.pid"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
GUI_PORT = 8080


def _port_open(port, host="127.0.0.1"):
    """检查端口是否被监听"""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


def _start_gui():
    """启动GUI控制面板（如果未运行）"""
    if _port_open(GUI_PORT):
        log(f"GUI已在运行（端口{GUI_PORT}）")
        return
    try:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        p = subprocess.Popen(
            [pythonw, str(BASE_DIR / "gui.py")],
            cwd=str(BASE_DIR), creationflags=NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(f"GUI已自动启动（PID {p.pid}，端口{GUI_PORT}）")
        # 等待端口就绪（最多15秒）
        for _ in range(15):
            if _port_open(GUI_PORT):
                break
            time.sleep(1)
        if not _port_open(GUI_PORT):
            log("警告: GUI端口未就绪，请检查output/gui_server.log")
    except Exception as e:
        log(f"GUI启动失败: {e}")


def _stop_gui():
    """停止GUI控制面板"""
    try:
        if GUI_PID_FILE.exists():
            pid = GUI_PID_FILE.read_text(encoding="utf-8").strip()
            if pid:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=5, creationflags=NO_WINDOW)
                log(f"GUI已停止（PID {pid}）")
                return
        # 兜底：按命令行匹配
        if platform.system() == "Windows":
            r = subprocess.run(["wmic", "process", "where",
                                "name='pythonw.exe' and commandline like '%gui.py%'",
                                "call", "terminate"],
                               capture_output=True, timeout=5, creationflags=NO_WINDOW)
    except Exception as e:
        log(f"GUI停止异常: {e}")


def _write_status(running):
    """写入daemon运行状态"""
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        STATUS_FILE.write_text(json.dumps({
            "running": running,
            "pid": os.getpid() if running else None,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
            "interval": REFRESH_INTERVAL,
        }), encoding="utf-8")
    except Exception:
        pass


def daemon_loop():
    """守护进程主循环"""
    _write_status(True)
    log("Kindle守护进程启动")
    log(f"刷新间隔: {REFRESH_INTERVAL}秒")

    # 自动拉起GUI控制面板（无需手动开启）
    _start_gui()

    # 清理残留停止标志
    try:
        if STOP_FLAG.exists():
            STOP_FLAG.unlink()
    except Exception:
        pass

    try:
        while True:
            # 检查停止标志
            if STOP_FLAG.exists():
                log("收到停止信号，守护进程退出（保留GUI控制面板）")
                _write_status(False)
                return

            try:
                refresh_dashboard()
            except Exception as e:
                log(f"刷新出错: {e}")

            # 每轮循环更新状态
            _write_status(True)

            # 分小段sleep，期间检查停止标志
            for _ in range(REFRESH_INTERVAL):
                if STOP_FLAG.exists():
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        log("守护进程被手动中断")
        _write_status(False)


if __name__ == "__main__":
    try:
        daemon_loop()
    except Exception as e:
        log(f"守护进程异常退出: {e}")
        _write_status(False)
        sys.exit(1)
