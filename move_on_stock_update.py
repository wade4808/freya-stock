#!/usr/bin/env python3
"""
Move on Stock - 美股数据更新脚本
每小时更新一次，生成 move_on_stock_data.json 供网页使用
"""
import json, os, sys, time
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DEFAULT_TICKERS = ["GOOGL", "LI", "BG", "BABA"]

STOCK_NAMES = {
    "GOOGL": "谷歌", "LI": "理想汽车", "BG": "邦基", "BABA": "阿里巴巴",
    "AAPL": "苹果", "MSFT": "微软", "AMZN": "亚马逊", "NVDA": "英伟达",
    "META": "Meta", "TSLA": "特斯拉", "AMD": "AMD", "INTC": "英特尔",
    "NFLX": "奈飞", "DIS": "迪士尼", "BA": "波音", "JPM": "摩根大通",
    "V": "Visa", "WMT": "沃尔玛", "JNJ": "强生", "XOM": "埃克森美孚",
    "TSM": "台积电", "QQQ": "纳指ETF", "SPY": "标普ETF",
    "BIDU": "百度", "JD": "京东", "NIO": "蔚来", "XPEV": "小鹏",
    "COIN": "Coinbase", "PLTR": "Palantir", "UBER": "优步",
    "ADBE": "Adobe", "CRM": "Salesforce", "ORCL": "甲骨文",
    "PYPL": "PayPal", "MCD": "麦当劳", "KO": "可口可乐",
    "NKE": "耐克", "MU": "美光", "QCOM": "高通", "AVGO": "博通",
    "SBUX": "星巴克", "COST": "好市多", "CVX": "雪佛龙",
    "GS": "高盛", "MS": "摩根士丹利", "CAT": "卡特彼勒", "GE": "通用电气",
    "SNAP": "Snap", "ZM": "Zoom", "DASH": "DoorDash", "RBLX": "Roblox"
}

SECTOR_MAP = {
    "GOOGL": "科技", "LI": "新能源车", "BG": "农业", "BABA": "电商/云",
    "AAPL": "科技", "MSFT": "科技", "AMZN": "电商/云", "NVDA": "半导体",
    "META": "社交媒体", "TSLA": "新能源车", "AMD": "半导体", "INTC": "半导体",
    "NFLX": "流媒体", "DIS": "娱乐", "JPM": "银行", "V": "金融科技",
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_stock_data(tickers):
    """使用yfinance批量获取美股数据"""
    results = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            hist = t.history(period="5d")

            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            prev_close = info.get("previousClose") or (hist["Close"].iloc[-2] if len(hist) >= 2 else None)
            change_pct = None
            if price and prev_close and prev_close > 0:
                change_pct = round((price - prev_close) / prev_close * 100, 2)

            volume = info.get("volume") or (hist["Volume"].iloc[-1] if len(hist) >= 1 else None)

            flow_estimate = None
            if volume and price and change_pct is not None:
                flow_amt = volume * price * 0.15
                flow_estimate = {
                    "direction": "流入" if change_pct >= 0 else "流出",
                    "label": "${:.1f}M {}".format(flow_amt / 1e6, "流入" if change_pct >= 0 else "流出")
                }

            news_items = []
            try:
                news = t.news or []
                for article in news[:4]:
                    news_items.append({
                        "title": article.get("title", ""),
                        "desc": (article.get("summary", "") or "")[:120],
                        "source": article.get("publisher", "Yahoo Finance"),
                    })
            except Exception:
                pass

            results[ticker] = {
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "name": STOCK_NAMES.get(ticker, ticker),
                "sector": SECTOR_MAP.get(ticker, "其他"),
                "flow": flow_estimate,
                "news": news_items,
            }
            print("  [OK] {}: ${}".format(ticker, price))
            time.sleep(0.3)
        except Exception as e:
            print("  [ERR] {}: {}".format(ticker, e))
            results[ticker] = {
                "price": None, "change_pct": None, "volume": None,
                "name": STOCK_NAMES.get(ticker, ticker), "sector": "其他",
                "flow": None, "news": [],
            }
    return results


def main():
    print("=" * 50)
    print("  Move on Stock - 美股数据更新")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    # 读取或创建配置
    config_file = os.path.join(OUTPUT_DIR, "move_on_stock_config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            cfg = json.load(f)
            tickers = cfg.get("tickers", DEFAULT_TICKERS)
    else:
        tickers = DEFAULT_TICKERS
        with open(config_file, "w") as f:
            json.dump({"tickers": tickers}, f, ensure_ascii=False, indent=2)

    print("\n[FETCH] 获取 {} 只美股: {}".format(len(tickers), ", ".join(tickers)))
    data = fetch_stock_data(tickers)

    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 保存 JSON
    json_file = os.path.join(OUTPUT_DIR, "move_on_stock_data.json")
    output = {
        "update_time": update_time,
        "tickers": tickers,
        "stocks": data,
        "portfolio": {"invested_pct": 40, "floating_pnl_pct": -10, "goal": "稳定持续增长"}
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n[SAVED] " + json_file)

    success = sum(1 for t in tickers if data.get(t, {}).get("price"))
    print("[DONE] 成功: {}/{} 只".format(success, len(tickers)))
    print("=" * 50)


if __name__ == "__main__":
    main()
