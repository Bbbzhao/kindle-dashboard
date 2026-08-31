# -*- coding: utf-8 -*-
"""Kindle Dashboard 守护进程（参考 kindle2workbuddy）
每 REFRESH_INTERVAL 秒调用 refresh.py 刷新一次。
支持GUI控制：检测停止标志文件，写入运行状态。
"""
import os
import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from settings import REFRESH_INTERVAL
from refresh import main as refresh_dashboard, log

OUTPUT_DIR = BASE_DIR / "output"
STOP_FLAG = OUTPUT_DIR / "daemon_stop.flag"
STATUS_FILE = OUTPUT_DIR / "daemon_status.json"


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
    log("守护进程启动")
    log(f"刷新间隔: {REFRESH_INTERVAL}秒")

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
                log("收到停止信号，守护进程退出")
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
