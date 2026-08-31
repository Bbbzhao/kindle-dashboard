# -*- coding: utf-8 -*-
"""DeepSeek 消费数据获取（网页端Token方案）
通过 platform.deepseek.com 私有接口获取真实消费数据。

接口（均为平台私有面板接口，可能随时变动）：
- GET /api/v0/users/get_user_summary  → 余额、累计消费
- GET /api/v0/usage/cost?month=M&year=Y → 每日费用明细

Token获取：登录 platform.deepseek.com → F12 → Network → 请求头 Authorization
"""
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
CACHE_FILE = BASE_DIR / "output" / "deepseek_cache.json"

BASE_URL = "https://platform.deepseek.com"
TIMEOUT = 10

# 缓存有效期（秒）：5分钟，避免频繁请求平台接口
CACHE_TTL = 300


def get_token():
    """从config.json读取DeepSeek网页端Token"""
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cfg.get("deepseek_token", "")
    except Exception:
        pass
    return ""


def _headers():
    """构造请求头"""
    token = get_token()
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }


def _request(path, params=None):
    """请求平台接口"""
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=_headers(),
                         params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}", "detail": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def get_balance():
    """获取账户余额信息
    返回: ({"balance": 26.26, "total_cost": 83.74}, None) 或 (None, 错误信息)
    """
    data = _request("/api/v0/users/get_user_summary")
    if "error" in data:
        return None, data["error"]
    try:
        biz = data.get("data", {}).get("biz_data", {})
        normal = biz.get("normal_wallets", [])
        bonus = biz.get("bonus_wallets", [])
        costs = biz.get("total_costs", [])

        balance = float(normal[0].get("balance", 0)) if normal else 0.0
        bonus_balance = float(bonus[0].get("balance", 0)) if bonus else 0.0
        total_cost = float(costs[0].get("amount", 0)) if costs else 0.0

        return {
            "balance": balance + bonus_balance,
            "normal_balance": balance,
            "bonus_balance": bonus_balance,
            "total_cost": total_cost,
        }, None
    except Exception as e:
        return None, f"解析失败: {e}"


def get_monthly_cost(year, month):
    """获取指定月份费用明细
    返回: (biz_data[0]原始dict, None) 或 (None, 错误)
    """
    data = _request("/api/v0/usage/cost", params={"month": month, "year": year})
    if "error" in data:
        return None, data["error"]
    try:
        biz_data = data.get("data", {}).get("biz_data", [])
        if biz_data and isinstance(biz_data, list):
            return biz_data[0], None
        return None, "biz_data为空"
    except Exception as e:
        return None, f"解析失败: {e}"


def _parse_daily_cost(biz_data):
    """从biz_data解析每日消费（单位CNY元）
    结构: biz_data = {"days": [{"date": "...", "data": [{"model": "...", "usage": [{"type": "...", "amount": "..."}]}]}]}
    每天消费 = 所有模型的usage金额之和
    """
    daily_map = {}
    days = biz_data.get("days", []) if isinstance(biz_data, dict) else []
    for day in days:
        date_str = str(day.get("date", ""))[:10]
        if not date_str:
            continue
        total = 0.0
        for model_entry in day.get("data", []):
            for usage in model_entry.get("usage", []):
                try:
                    total += float(usage.get("amount", 0) or 0)
                except (TypeError, ValueError):
                    pass
        daily_map[date_str] = round(total, 4)
    return daily_map


def get_daily_cost_30d():
    """获取近30天每日消费
    返回: (daily列表, today_cost, 错误信息)
    """
    # 读取缓存
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - cache.get("ts", 0) < CACHE_TTL:
                return cache.get("daily", []), cache.get("today", 0), None
        except Exception:
            pass

    today = datetime.now()
    daily_map = {}

    # 近30天可能跨2个月
    months = set()
    for i in range(30):
        d = today - timedelta(days=i)
        months.add((d.year, d.month))

    errors = []
    for year, month in sorted(months):
        biz_data, err = get_monthly_cost(year, month)
        if err or biz_data is None:
            errors.append(f"{year}-{month}: {err}")
            continue
        daily_map.update(_parse_daily_cost(biz_data))

    # 组装近30天
    daily = []
    today_cost = 0
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        cost = daily_map.get(key, 0.0)
        daily.append({"date": d.strftime("%m-%d"), "cost": cost})
        if i == 0:
            today_cost = cost

    # 写入缓存
    try:
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "ts": time.time(),
            "daily": daily,
            "today": today_cost,
        }), encoding="utf-8")
    except Exception:
        pass

    return daily, today_cost, "; ".join(errors) if errors else None


def get_deepseek_summary():
    """整合：余额 + 今日消费 + 30天趋势"""
    balance, bal_err = get_balance()
    daily, today_cost, cost_err = get_daily_cost_30d()

    return {
        "balance": balance.get("balance") if balance else None,
        "normal_balance": balance.get("normal_balance") if balance else None,
        "total_cost": balance.get("total_cost") if balance else None,
        "daily": daily,
        "today": today_cost,
        "errors": [e for e in (bal_err, cost_err) if e],
    }


if __name__ == "__main__":
    token = get_token()
    if not token:
        print("❌ 未配置DeepSeek Token（config.json的deepseek_token字段）")
    else:
        print(f"✅ 已配置Token（{token[:8]}...）")
        summary = get_deepseek_summary()
        print(f"余额: ¥{summary['balance']}")
        print(f"累计消费: ¥{summary['total_cost']}")
        print(f"今日消费: ¥{summary['today']}")
        print(f"30天数据: {len(summary['daily'])}条")
        print(f"近7天: {[(d['date'], d['cost']) for d in summary['daily'][-7:]]}")
        if summary["errors"]:
            print(f"警告: {summary['errors']}")
