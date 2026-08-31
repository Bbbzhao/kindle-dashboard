# -*- coding: utf-8 -*-
"""Kindle Dashboard 控制面板（Flask Web GUI）
功能：查看/修改配置、立即刷新、启动/停止自动刷新、查看日志
访问：http://localhost:8080/
"""
import os
import sys
import json
import time
import signal
import subprocess
import platform
from pathlib import Path

from flask import Flask, jsonify, request, render_template

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from settings import CONFIG_FILE, BASE_DIR as SETTINGS_DIR
import settings

app = Flask(__name__)

OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = OUTPUT_DIR / "refresh.log"
STOP_FLAG = OUTPUT_DIR / "daemon_stop.flag"
STATUS_FILE = OUTPUT_DIR / "daemon_status.json"

PYTHON_EXE = sys.executable
NO_WINDOW = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


# ==================== 配置读写 ====================

def read_config():
    """读取当前配置"""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "kindle_host": settings.KINDLE_HOST,
        "kindle_port": settings.KINDLE_PORT,
        "kindle_user": settings.KINDLE_USER,
        "ssh_key": settings.SSH_KEY,
        "refresh_interval": settings.REFRESH_INTERVAL,
        "ssh_timeout": settings.SSH_TIMEOUT,
        "ssh_retries": settings.SSH_RETRIES,
        "ssh_retry_delay": settings.SSH_RETRY_DELAY,
        "deepseek_token": settings.get_deepseek_token() if hasattr(settings, "get_deepseek_token") else "",
    }


def save_config(cfg):
    """保存配置到config.json"""
    CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 刷新settings模块（使新配置立即生效）
    for key, val in cfg.items():
        attr = {
            "kindle_host": "KINDLE_HOST",
            "kindle_port": "KINDLE_PORT",
            "kindle_user": "KINDLE_USER",
            "ssh_key": "SSH_KEY",
            "refresh_interval": "REFRESH_INTERVAL",
            "ssh_timeout": "SSH_TIMEOUT",
            "ssh_retries": "SSH_RETRIES",
            "ssh_retry_delay": "SSH_RETRY_DELAY",
        }.get(key)
        if attr:
            setattr(settings, attr, int(val) if key not in ("kindle_host", "kindle_user", "ssh_key") else val)


# ==================== daemon 管理 ====================

def get_daemon_status():
    """读取daemon运行状态"""
    try:
        if STATUS_FILE.exists():
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            # 校验进程是否真的在运行
            pid = data.get("pid")
            if pid and platform.system() == "Windows":
                try:
                    # Windows下用tasklist检查（处理GBK编码）
                    r = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}"],
                        capture_output=True, timeout=5, creationflags=NO_WINDOW
                    )
                    out = r.stdout.decode("gbk", errors="ignore")
                    data["running"] = str(pid) in out
                except Exception:
                    data["running"] = True  # 状态文件写了就认为在运行
            return data
    except Exception:
        pass
    return {"running": False, "pid": None, "last_update": None, "interval": settings.REFRESH_INTERVAL}


def start_daemon():
    """启动守护进程（后台）"""
    if get_daemon_status().get("running"):
        return False, "守护进程已在运行"
    # 清理停止标志
    try:
        if STOP_FLAG.exists():
            STOP_FLAG.unlink()
    except Exception:
        pass
    cmd = [PYTHON_EXE, str(BASE_DIR / "daemon.py")]
    subprocess.Popen(cmd, cwd=str(BASE_DIR), creationflags=NO_WINDOW,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return True, "守护进程已启动"


def stop_daemon():
    """停止守护进程"""
    status = get_daemon_status()
    if not status.get("running"):
        # 即使状态未知，也写入停止标志兜底
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            STOP_FLAG.write_text("stop", encoding="utf-8")
        except Exception:
            pass
        return True, "守护进程未运行（已写停止标志兜底）"

    pid = status.get("pid")
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        STOP_FLAG.write_text("stop", encoding="utf-8")
    except Exception:
        pass

    # 等待daemon自己退出（最多10秒）
    for _ in range(10):
        time.sleep(1)
        s = get_daemon_status()
        if not s.get("running"):
            return True, "守护进程已停止"
    # 超时则强制结束
    if pid:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5, creationflags=NO_WINDOW)
            return True, "守护进程已强制停止"
        except Exception:
            pass
    return False, "停止失败"


# ==================== 立即刷新 ====================

def do_refresh():
    """立即执行一次刷新"""
    from refresh import main as refresh_main
    # 防止阻塞GUI，后台执行
    cmd = [PYTHON_EXE, str(BASE_DIR / "refresh.py")]
    subprocess.Popen(cmd, cwd=str(BASE_DIR), creationflags=NO_WINDOW,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, "刷新任务已触发（后台执行）"


def read_log(tail=30):
    """读取最近日志"""
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
            return lines[-tail:]
    except Exception:
        pass
    return []


# ==================== 路由 ====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    cfg = read_config()
    status = get_daemon_status()
    log = read_log()
    return jsonify({
        "config": cfg,
        "daemon": status,
        "log": log,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.get_json(force=True)
    # 校验必要字段
    required = ["kindle_host", "kindle_port", "kindle_user", "ssh_key", "refresh_interval"]
    for k in required:
        if k not in data or str(data[k]).strip() == "":
            return jsonify({"ok": False, "msg": f"缺少必要参数: {k}"})
    try:
        refresh = int(data.get("refresh_interval", 240))
        if refresh < 30:
            return jsonify({"ok": False, "msg": "刷新周期不能小于30秒"})
        save_config(data)
        return jsonify({"ok": True, "msg": "配置已保存并生效"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"保存失败: {e}"})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    ok, msg = do_refresh()
    return jsonify({"ok": ok, "msg": msg})


@app.route("/api/daemon/start", methods=["POST"])
def api_daemon_start():
    ok, msg = start_daemon()
    return jsonify({"ok": ok, "msg": msg})


@app.route("/api/daemon/stop", methods=["POST"])
def api_daemon_stop():
    ok, msg = stop_daemon()
    return jsonify({"ok": ok, "msg": msg})


if __name__ == "__main__":
    # 记录PID（供stop_gui.bat停止使用）
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / "gui.pid").write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    print("=" * 40)
    print("Kindle Dashboard 控制面板")
    print("访问 http://localhost:8080/")
    print("停止服务: stop_gui.bat")
    print("=" * 40)
    app.run(host="0.0.0.0", port=8080, debug=False)
