# -*- coding: utf-8 -*-
"""Kindle Dashboard 渲染引擎（参考 kindle2workbuddy）
渲染 1024×758 横屏灰度图，直接适配 KPW2 横放显示，无需旋转。
"""
import json
import os
import random
import requests
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from settings import (
    IMAGE_WIDTH, IMAGE_HEIGHT, GRAYSCALE,
    TODO_FILE, FONT_PATH,
    WEATHER_LAT, WEATHER_LON, WEATHER_CITY_CN,
)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PNG = OUTPUT_DIR / "dashboard.png"

# WMO天气代码 → 中文
WMO_CODES = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "强阵雨", 82: "暴雨",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "强雷暴",
}


# ==================== 数据获取 ====================

def get_todos():
    """从金鱼本读取待办"""
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"life": [], "work": []}


def get_weather():
    """获取佛山天气（Open-Meteo API）"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        current = data["current"]
        daily = data["daily"]
        code = current.get("weather_code", 0)

        return {
            "temp": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": current["relative_humidity_2m"],
            "wind_speed": round(current["wind_speed_10m"]),
            "description": WMO_CODES.get(code, "未知"),
            "temp_max": round(daily["temperature_2m_max"][0]),
            "temp_min": round(daily["temperature_2m_min"][0]),
        }
    except Exception:
        return None


def get_deepseek_cost():
    """获取DeepSeek消费（优先真实数据，未配置Token时用示例数据）"""
    try:
        from deepseek_data import get_daily_cost_30d, get_token
        if get_token():
            daily, today_cost, err = get_daily_cost_30d()
            if daily:
                return {"daily": daily, "today": today_cost}
    except Exception:
        pass

    # 兜底：示例数据（未配置Token或接口失败）
    try:
        now = datetime.now()
        daily = []
        for i in range(29, -1, -1):
            date = now - timedelta(days=i)
            cost = round(random.uniform(0, 5), 2) if i > 0 else round(random.uniform(1, 8), 2)
            daily.append({"date": date.strftime("%m-%d"), "cost": cost})
        return {"daily": daily, "today": daily[-1]["cost"]}
    except Exception:
        return {"daily": [], "today": 0}


# ==================== 渲染 ====================

def render_dashboard(todos=None, weather=None, deepseek=None):
    """渲染1024×758横屏灰度图"""
    if todos is None:
        todos = get_todos()
    if weather is None:
        weather = get_weather()
    if deepseek is None:
        deepseek = get_deepseek_cost()

    img = Image.new("L", (IMAGE_WIDTH, IMAGE_HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # 加载字体（按比例缩放）
    try:
        font_title = ImageFont.truetype(FONT_PATH, 40)
        font_subtitle = ImageFont.truetype(FONT_PATH, 28)
        font_text = ImageFont.truetype(FONT_PATH, 22)
        font_small = ImageFont.truetype(FONT_PATH, 18)
        font_tiny = ImageFont.truetype(FONT_PATH, 14)
        font_weather_big = ImageFont.truetype(FONT_PATH, 56)
    except Exception:
        font_title = font_subtitle = font_text = font_small = font_tiny = font_weather_big = ImageFont.load_default()

    def draw_center_title(x_left, y_top, y_bottom, text, font, fill):
        """在标题栏内垂直居中绘制文字"""
        bbox = draw.textbbox((0, 0), text, font=font)
        h = bbox[3] - bbox[1]
        y = y_top + (y_bottom - y_top - h) / 2 - bbox[1]
        draw.text((x_left, y), text, font=font, fill=fill)

    # ============ 标题栏 ============
    draw.text((30, 12), "个人仪表盘", font=font_title, fill=0)
    draw.text((250, 22), WEATHER_CITY_CN, font=font_small, fill=128)
    # 右上角更新时间
    update_text = f"更新 {datetime.now().strftime('%H:%M')}"
    update_w = draw.textlength(update_text, font=font_small)
    draw.text((994 - update_w, 22), update_text, font=font_small, fill=100)
    draw.line([(30, 60), (994, 60)], fill=0, width=2)

    y_offset = 75

    # ============ 天气卡片（左侧） ============
    draw.rectangle([30, y_offset, 330, y_offset + 165], outline=0, width=2)
    draw.rectangle([30, y_offset, 330, y_offset + 42], fill=0)
    draw_center_title(40, y_offset, y_offset + 42, "佛山天气", font_subtitle, 255)

    if weather:
        # 温度大字 + 描述（紧凑排版）
        draw.text((40, y_offset + 48), f'{weather["temp"]}°C', font=font_weather_big, fill=0)
        draw.text((185, y_offset + 60), weather["description"], font=font_small, fill=0)
        # 第二行：体感 | 湿度（小字体，留足边距）
        draw.text((40, y_offset + 118), f'体感{weather["feels_like"]}°C', font=font_small, fill=100)
        draw.text((160, y_offset + 118), f'湿度{weather["humidity"]}%', font=font_small, fill=100)
        # 第三行：风速 | 高低温（小字体，留足边距）
        draw.text((40, y_offset + 140), f'风{weather["wind_speed"]}km/h', font=font_small, fill=100)
        draw.text((160, y_offset + 140), f'高{weather["temp_max"]}° 低{weather["temp_min"]}°', font=font_small, fill=100)
    else:
        draw.text((40, y_offset + 70), "天气获取失败", font=font_text, fill=128)

    # ============ 生活待办（中左） ============
    draw.rectangle([345, y_offset, 520, y_offset + 165], outline=0, width=2)
    draw.rectangle([345, y_offset, 520, y_offset + 42], fill=0)
    draw_center_title(355, y_offset, y_offset + 42, "生活待办", font_subtitle, 255)

    y = y_offset + 52
    # 只显示未完成的待办
    life_todos = [t for t in todos.get("life", []) if not t.get("done")]
    if life_todos:
        for todo in life_todos[:5]:
            content = todo.get("content", "").lstrip("• ")
            # 按像素宽度裁剪（卡片可用165px）
            while content and draw.textlength(f"• {content}", font=font_text) > 155:
                content = content[:-1]
            if content != todo.get("content", "").lstrip("• "):
                content = content.rstrip("…") + "…"
            draw.text((355, y), f"• {content}", font=font_text, fill=0)
            y += 24
    else:
        draw.text((355, y), "暂无", font=font_text, fill=128)

    # ============ 工作待办（右侧） ============
    draw.rectangle([535, y_offset, 994, y_offset + 165], outline=0, width=2)
    draw.rectangle([535, y_offset, 994, y_offset + 42], fill=0)
    draw_center_title(545, y_offset, y_offset + 42, "工作待办", font_subtitle, 255)

    y = y_offset + 52
    # 只显示未完成的待办
    work_todos = [t for t in todos.get("work", []) if not t.get("done")]
    if work_todos:
        for todo in work_todos[:5]:
            content = todo.get("content", "").lstrip("• ")
            # 按像素宽度裁剪（卡片可用445px）
            while content and draw.textlength(f"• {content}", font=font_text) > 430:
                content = content[:-1]
            if content != todo.get("content", "").lstrip("• "):
                content = content.rstrip("…") + "…"
            draw.text((545, y), f"• {content}", font=font_text, fill=0)
            y += 24
    else:
        draw.text((545, y), "暂无", font=font_text, fill=128)

    y_offset += 185

    # ============ DeepSeek消费柱状图 ============
    draw.rectangle([30, y_offset, 994, y_offset + 470], outline=0, width=2)
    draw.rectangle([30, y_offset, 994, y_offset + 42], fill=0)
    draw_center_title(40, y_offset, y_offset + 42, f'DeepSeek 消费  |  今日: ¥{deepseek["today"]:.2f}', font_subtitle, 255)

    daily = deepseek.get("daily", [])
    if daily:
        chart_left = 80
        chart_right = 960
        chart_top = y_offset + 45
        chart_bottom = y_offset + 440
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top

        max_cost = max(d["cost"] for d in daily) if daily else 1
        if max_cost == 0:
            max_cost = 1

        bar_width = chart_width // len(daily) - 2 if daily else 10
        if bar_width < 6:
            bar_width = 6

        for i, d in enumerate(daily):
            bar_height = int((d["cost"] / max_cost) * (chart_height - 30))
            if bar_height < 2:
                bar_height = 2
            x = chart_left + i * (bar_width + 3)
            y_bar = chart_bottom - bar_height

            draw.rectangle([x, y_bar, x + bar_width, chart_bottom], fill=0)

            if i % 5 == 0 or i == len(daily) - 1:
                draw.text((x, chart_bottom + 5), d["date"], font=font_small, fill=100)

            if d["cost"] > 0:
                # 金额保留2位小数，用小字体
                cost_label = f'{d["cost"]:.2f}'
                draw.text((x, y_bar - 14), cost_label, font=font_tiny, fill=0)

        draw.text((55, chart_top), f'¥{max_cost:.0f}', font=font_small, fill=100)
        draw.text((55, chart_bottom - 16), "¥0", font=font_small, fill=100)

    # 底部更新时间
    draw.text((30, IMAGE_HEIGHT - 28), f'更新: {datetime.now().strftime("%Y-%m-%d %H:%M")}', font=font_small, fill=150)

    # 顺时针旋转90度：横向内容 → 竖屏尺寸(758×1024)，适配Kindle横放显示
    img = img.rotate(90, expand=True)

    return img


def render():
    """渲染并保存dashboard.png，返回文件路径"""
    todos = get_todos()
    weather = get_weather()
    deepseek = get_deepseek_cost()

    img = render_dashboard(todos, weather, deepseek)

    OUTPUT_DIR.mkdir(exist_ok=True)
    img.save(str(OUTPUT_PNG), "PNG")
    return OUTPUT_PNG


if __name__ == "__main__":
    png = render()
    print(f"渲染完成: {png} ({img.size[0]}x{img.size[1]})")
