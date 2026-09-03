# -*- coding: utf-8 -*-
"""Kindle Dashboard 控制面板（Flask Web GUI）
功能：查看/修改配置、立即刷新、启动/停止自动刷新、查看日志、传书到Kindle
访问：http://localhost:8080/
"""
import os
import re
import sys
import json
import time
import uuid
import base64
import signal
import subprocess
import platform
from pathlib import Path

import logging
import logging.handlers

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

# pythonw.exe运行无stderr，Werkzeug日志输出会崩溃，重定向到文件
try:
    OUTPUT_DIR.mkdir(exist_ok=True)
    _server_log = str(OUTPUT_DIR / "gui_server.log")
    _fh = logging.FileHandler(_server_log, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _werkzeug_log = logging.getLogger("werkzeug")
    _werkzeug_log.handlers = []
    _werkzeug_log.addHandler(_fh)
    _werkzeug_log.setLevel(logging.INFO)
except Exception:
    pass

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
    cmd = [PYTHON_EXE, str(BASE_DIR / "kindle-daemon.py")]
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
    # 读取Kindle电量缓存（daemon/刷新时更新）
    battery = None
    try:
        bf = OUTPUT_DIR / "battery.json"
        if bf.exists():
            import json as _json
            battery = _json.loads(bf.read_text(encoding="utf-8"))
    except Exception:
        pass
    return jsonify({
        "config": cfg,
        "daemon": status,
        "battery": battery,
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


@app.route("/api/kindle/exit", methods=["POST"])
def api_kindle_exit():
    """退出仪表盘模式：SSH执行Kindle端dashboard-off.sh，恢复framework回到KUAL界面"""
    import threading

    def _do_exit():
        from refresh import ssh_run, log
        from settings import KINDLE_HOST
        log("退出仪表盘模式...")
        # 执行Kindle端退出脚本（停止keepalive + 恢复framework）
        ok, out = ssh_run(KINDLE_HOST,
            "sh /mnt/us/extensions/dashboard/bin/dashboard-off.sh; echo EXIT_OK",
            retries=2, timeout=30)
        log(f"退出结果: {'成功' if ok else '失败'} {str(out)[:80]}")

    threading.Thread(target=_do_exit, daemon=True).start()
    return jsonify({"ok": True, "msg": "正在退出仪表盘模式（后台执行）... Kindle将回到KUAL/原生界面"})


@app.route("/api/kindle/check", methods=["POST"])
def api_kindle_check():
    """测试当前配置IP的SSH连通性"""
    import socket
    import time
    from settings import KINDLE_HOST, KINDLE_PORT

    start = time.time()
    # 1. TCP端口测试
    tcp_ok = False
    try:
        with socket.create_connection((KINDLE_HOST, KINDLE_PORT), timeout=3):
            tcp_ok = True
    except Exception:
        pass

    # 2. SSH真实测试
    from refresh import ssh_run
    ssh_ok, out = ssh_run(KINDLE_HOST, "echo PONG", retries=1, timeout=8)
    latency = round((time.time() - start) * 1000)

    if ssh_ok:
        msg = f"✅ {KINDLE_HOST} SSH连接正常（{latency}ms）"
    elif tcp_ok:
        msg = f"⚠️ {KINDLE_HOST} 端口通但SSH握手失败（可能dropbear未启动）"
    else:
        msg = f"❌ {KINDLE_HOST} 不可达（IP可能已变，建议扫描局域网）"

    return jsonify({
        "host": KINDLE_HOST,
        "tcp": tcp_ok,
        "ssh": ssh_ok,
        "latency_ms": latency,
        "online": ssh_ok,
        "msg": msg,
    })


@app.route("/api/kindle/discover", methods=["POST"])
def api_kindle_discover():
    """扫描局域网找Kindle（22端口+SSH banner识别）"""
    import socket
    import concurrent.futures
    from settings import KINDLE_HOST

    prefix = ".".join(KINDLE_HOST.split(".")[:3])
    found = []

    def _check(ip):
        try:
            with socket.create_connection((ip, 22), timeout=1.5):
                s = socket.create_connection((ip, 22), timeout=2)
                s.settimeout(2)
                banner = s.recv(50)
                s.close()
                if b"SSH" in banner or b"ssh" in banner:
                    return ip
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        futures = [ex.submit(_check, f"{prefix}.{i}") for i in range(1, 255)]
        for f in concurrent.futures.as_completed(futures):
            ip = f.result()
            if ip:
                found.append(ip)

    return jsonify({
        "found": found,
        "prefix": prefix,
        "msg": f"扫描{prefix}.1-254完成，发现{len(found)}个SSH设备: {', '.join(found) if found else '无'}"
    })


ALLOWED_UPLOAD_EXT = {".epub", ".mobi", ".azw3", ".azw", ".pdf", ".txt",
                      ".fb2", ".cbz", ".cbr", ".docx", ".html"}
MAX_UPLOAD_MB = 25
KINDLE_DOCS_DIR = "/mnt/us/documents"


def _chunk_ssh_put(host, b64data, remote_path):
    """分块base64传输数据到Kindle（dropbear对大stdin不稳，分小块传）"""
    from refresh import ssh_run
    CHUNK = 180000
    total = (len(b64data) + CHUNK - 1) // CHUNK
    for i in range(total):
        part = b64data[i * CHUNK:(i + 1) * CHUNK]
        op = ">" if i == 0 else ">>"
        ok, out = ssh_run(host, f"base64 -d {op} {remote_path} && echo OK{i}",
                          retries=2, timeout=240, stdin_data=part)
        if not ok or f"OK{i}" not in str(out):
            return False, f"传输中断（块{i + 1}/{total}）"
    return True, "ok"


@app.route("/api/kindle/upload", methods=["POST"])
def api_kindle_upload():
    """上传书籍到Kindle documents/（免USB）"""
    from settings import KINDLE_HOST
    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "msg": "未收到文件"})

    results = []
    for f in files:
        name = f.filename or ""
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXT:
            results.append({"file": name, "ok": False,
                            "msg": f"不支持格式 {ext or '(无扩展名)'}"})
            continue
        # 文件名安全化（去shell危险字符，保留中文）
        safe = re.sub(r"['\"`;$&|<>()\s]+", "_", os.path.basename(name))
        if not safe:
            results.append({"file": name, "ok": False, "msg": "文件名非法"})
            continue
        # 保存到本地临时
        tmp = OUTPUT_DIR / f".up_{uuid.uuid4().hex}{ext}"
        try:
            f.save(tmp)
            size = tmp.stat().st_size
            if size == 0:
                raise ValueError("空文件")
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                results.append({"file": name, "ok": False,
                                "msg": f"超过{MAX_UPLOAD_MB}MB限制"})
                continue
            b64data = base64.b64encode(tmp.read_bytes())
        except Exception as e:
            results.append({"file": name, "ok": False, "msg": f"读取失败: {e}"})
            continue
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

        remote_path = f"{KINDLE_DOCS_DIR}/{safe}"
        ok, msg = _chunk_ssh_put(KINDLE_HOST, b64data, remote_path)
        if ok:
            from refresh import log
            log(f"已上传书籍: {safe} ({size // 1024}KB) → documents/")
            results.append({"file": name, "ok": True, "msg": f"已上传到 documents/{safe}"})
        else:
            results.append({"file": name, "ok": False, "msg": msg})

    ok_any = any(r["ok"] for r in results)
    return jsonify({"ok": ok_any, "results": results,
                    "msg": f"完成：成功{sum(1 for r in results if r['ok'])}个 / 失败{sum(1 for r in results if not r['ok'])}个"})


def _safe_print(msg):
    """安全打印（pythonw无控制台时print会崩溃）"""
    try:
        print(msg)
    except Exception:
        pass


if __name__ == "__main__":
    # 记录PID（供stop_gui.bat停止使用）
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / "gui.pid").write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    _safe_print("=" * 40)
    _safe_print("Kindle Dashboard 控制面板")
    _safe_print("访问 http://localhost:8080/")
    _safe_print("停止服务: stop_gui.bat")
    _safe_print("=" * 40)
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
