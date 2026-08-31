# -*- coding: utf-8 -*-
"""Kindle Dashboard 配置文件（参考 kindle2workbuddy）
支持从 config.json 覆盖参数（GUI控制面板修改入口）。
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ==================== Kindle SSH 配置 ====================
KINDLE_HOST = "192.168.x.x"         # Kindle WiFi IP（搜索框输入 ;711 查看，实际值在config.json）
KINDLE_PORT = 22
KINDLE_USER = "root"
KINDLE_REMOTE = "/mnt/us/dashboard.png"
SSH_KEY = "~/.ssh/id_kindle"        # SSH 私钥路径
EIPS_PATH = "/usr/sbin/eips"

# ==================== 刷新配置 ====================
REFRESH_INTERVAL = 240              # 守护进程刷新间隔（秒）
SSH_TIMEOUT = 15                    # SSH连接超时（秒）
SSH_RETRIES = 3                     # SSH失败重试次数
SSH_RETRY_DELAY = 15                # SSH重试间隔（秒）

# ==================== DHCP 自动发现 ====================
AUTO_DISCOVER_IP = True             # IP失效时自动扫描局域网找回
SUBNET_PREFIX = "192.168.20"        # 子网前缀（从KINDLE_HOST推导）

# ==================== 图片配置 ====================
IMAGE_WIDTH = 1024                  # KPW2横屏宽度
IMAGE_HEIGHT = 758                  # KPW2横屏高度
GRAYSCALE = True                    # 使用灰度图（E-ink更清晰）

# ==================== 数据源 ====================
TODO_FILE = r"D:\WorkBuddyData\Claw\todos_data.json"   # 金鱼本
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"               # 微软雅黑

# 天气配置（Open-Meteo，无需API Key）
WEATHER_LAT = 23.02                 # 佛山纬度
WEATHER_LON = 113.12                # 佛山经度
WEATHER_CITY_CN = "佛山"

# ==================== config.json 覆盖（GUI入口） ====================
CONFIG_FILE = BASE_DIR / "config.json"

def _load_config():
    """从 config.json 读取可覆盖参数"""
    cfg = {}
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return cfg

_cfg = _load_config()

KINDLE_HOST = _cfg.get("kindle_host", KINDLE_HOST)
KINDLE_PORT = int(_cfg.get("kindle_port", KINDLE_PORT))
KINDLE_USER = _cfg.get("kindle_user", KINDLE_USER)
SSH_KEY = _cfg.get("ssh_key", SSH_KEY)
REFRESH_INTERVAL = int(_cfg.get("refresh_interval", REFRESH_INTERVAL))
SSH_TIMEOUT = int(_cfg.get("ssh_timeout", SSH_TIMEOUT))
SSH_RETRIES = int(_cfg.get("ssh_retries", SSH_RETRIES))
SSH_RETRY_DELAY = int(_cfg.get("ssh_retry_delay", SSH_RETRY_DELAY))

# 从KINDLE_HOST推导子网前缀
_parts = KINDLE_HOST.split(".")
if len(_parts) == 4 and _parts[0].isdigit():
    SUBNET_PREFIX = ".".join(_parts[:3])

# DeepSeek网页端Token（config.json的deepseek_token字段）
DEEPSEEK_TOKEN = _cfg.get("deepseek_token", "")


def get_deepseek_token():
    """返回当前DeepSeek Token"""
    return DEEPSEEK_TOKEN
