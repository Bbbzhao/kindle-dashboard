# -*- coding: utf-8 -*-
"""生成README效果图：使用示例待办和示例消费数据（不含个人隐私）"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from render import render_dashboard, get_weather

# 示例待办（非真实个人数据）
sample_todos = {
    "life": [
        {"text": "周末去超市采购食材", "done": False},
        {"text": "给阳台的花浇水施肥", "done": False},
        {"text": "预约牙医复查", "done": True},
        {"text": "看完《鸟哥的Linux私房菜》", "done": False},
        {"text": "整理换季的衣物", "done": False},
    ],
    "work": [
        {"text": "整理本周项目进度报告", "done": False},
        {"text": "TAPD需求评审会议", "done": False},
        {"text": "能耗计费系统联调测试", "done": True},
        {"text": "回复客户邮件", "done": False},
    ],
}

# 示例DeepSeek消费（30天随机数据，非真实）
import random
from datetime import datetime, timedelta
random.seed(42)
sample_deepseek = {"daily": [], "today": 0}
for i in range(29, -1, -1):
    date = datetime.now() - timedelta(days=i)
    cost = round(random.uniform(0, 5), 2) if i > 0 else round(random.uniform(1, 8), 2)
    sample_deepseek["daily"].append({"date": date.strftime("%m-%d"), "cost": cost})
sample_deepseek["today"] = sample_deepseek["daily"][-1]["cost"]

# 真实天气（无隐私）
weather = get_weather()

# 渲染效果图
img = render_dashboard(sample_todos, weather, sample_deepseek)
# 转回横屏方向（1024x758），README展示更直观
img = img.rotate(-90, expand=True)
out = BASE_DIR / "docs"
out.mkdir(exist_ok=True)
img.save(out / "screenshot.png")
print(f"效果图已生成: {out / 'screenshot.png'} ({img.size[0]}x{img.size[1]})")
