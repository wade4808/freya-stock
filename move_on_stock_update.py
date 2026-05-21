#!/usr/bin/env python3
"""
Move on Stock - 美股自动更新脚本
每小时更新一次，生成数据JSON供网页使用
"""
import json, os, sys, time
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

# ============================================================
# 配置 - 在这里添加你想跟踪的美股
# ============================================================
DEFAULT_TICKERS = ["GOOGL", "LI", "BG", "BABA"]

# 股票中文名映射
STOCK_NAMES = {
    "GOOGL": "谷歌", "LI": "理想汽车", "BG": "邦基", "BABA": "阿里巴巴",
    "AAPL": "苹果", "MSFT": "微软", "AMZN": "亚马逊", "NVDA": "英伟达",
    "META": "Meta", "TSLA": "特斯拉", "AMD": "AMD", "INTC": "英特尔",
    "NFLX": "奈飞", "DIS": "迪士尼", "BA": "波音", "JPM": "摩根大通",
    "V": "Visa", "WMT": "沃尔玛", "JNJ": "强生", "XOM": "埃克森美孚",
    "TSM": "台积电", "QQQ": "纳斯达克ETF", "SPY": "标普500ETF",
    "BABA": "阿里巴巴", "BIDU": "百度", "JD": "京东", "NIO": "蔚来",
    "XPEV": "小鹏", "LI": "理想汽车",
}

# 行业分类
SECTOR_MAP = {
    "GOOGL": "科技", "LI": "新能源车", "BG": "农业", "BABA": "电商/云",
    "AAPL": "科技", "MSFT": "科技", "AMZN": "电商/云", "NVDA": "半导体",
    "META": "社交媒体", "TSLA": "新能源车", "AMD": "半导体", "INTC": "半导体",
    "NFLX": "流媒体", "DIS": "娱乐", "BA": "航空航天", "JPM": "银行",
    "V": "金融科技", "WMT": "零售", "JNJ": "医药", "XOM": "能源",
    "TSM": "半导体", "QQQ": "ETF", "SPY": "ETF",
    "BABA": "电商", "BIDU": "互联网", "JD": "电商", "NIO": "新能源车",
    "XPEV": "新能源车",
}

# 预置操作建议（华尔街投顾级别）
ADVICE_DATA = {
    "GOOGL": {
        "rate": "buy", "rate_text": "强烈买入", "target": "220",
        "core": "AI搜索+云计算双轮驱动，Gemini生态持续扩展，Q1广告收入超预期",
        "pros": ["AI搜索市场份额持续扩大", "Google Cloud营收增速30%+", "Gemini API调用量QoQ+150%", "Waymo估值超450亿"],
        "cons": ["反垄断监管风险持续", "AI投入资本开支较大"],
        "strategy": "核心仓位，建议占总仓位15-20%，逢回调加仓",
        "risk": "中"
    },
    "LI": {
        "rate": "buy", "rate_text": "买入", "target": "45",
        "core": "增程+纯电双路线并行，L系列持续热销，毛利率领先国内同行",
        "pros": ["月交付量持续5万+", "毛利率22%行业领先", "智驾全系标配", "海外市场开始拓展"],
        "cons": ["市场竞争加剧（问界等）", "纯电车型尚未放量"],
        "strategy": "成长仓位，建议8-12%，观察纯电车型表现",
        "risk": "中高"
    },
    "BG": {
        "rate": "hold", "rate_text": "持有", "target": "85",
        "core": "全球粮油贸易龙头，受益于农产品价格波动，分红稳定",
        "pros": ["全球农产品贸易份额领先", "分红率3.5%+", "巴西阿根廷大豆贸易强劲"],
        "cons": ["农产品价格周期性波动", "地缘政治影响供应链"],
        "strategy": "防御仓位，建议5-8%，作为组合稳定器",
        "risk": "低中"
    },
    "BABA": {
        "rate": "buy", "rate_text": "买入", "target": "135",
        "core": "云+AI+电商重塑增长，阿里云利润爆发，国际电商高速增长",
        "pros": ["阿里云利润率持续改善", "国际电商增速40%+", "AI大模型通义千问领先", "股票回购力度大"],
        "cons": ["国内消费复苏不确定性", "监管环境变化", "拼多多/抖音竞争"],
        "strategy": "核心仓位，建议12-18%，长期持有等待云+AI估值重估",
        "risk": "中"
    }
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(OUTPUT_DIR, "move_on_stock_data.json")
CONFIG_FILE = os.path.join(OUTPUT_DIR, "move_on_stock_config.json")

def load_config():
    """从配置文件读取要跟踪的股票列表"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("tickers", DEFAULT_TICKERS)
    return DEFAULT_TICKERS

def fetch_stock_data(tickers):
    """使用yfinance批量获取美股数据"""
    results = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            hist = t.history(period="2d")

            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            prev_close = info.get("previousClose") or (hist["Close"].iloc[-2] if len(hist) >= 2 else None)
            change_pct = None
            change_amt = None

            if price and prev_close and prev_close > 0:
                change_amt = price - prev_close
                change_pct = (change_amt / prev_close) * 100

            high = info.get("dayHigh") or (hist["High"].iloc[-1] if len(hist) >= 1 else None)
            low = info.get("dayLow") or (hist["Low"].iloc[-1] if len(hist) >= 1 else None)
            volume = info.get("volume") or (hist["Volume"].iloc[-1] if len(hist) >= 1 else None)
            market_cap = info.get("marketCap")

            # 估计资金流向（基于价格方向*成交量）
            avg_volume = hist["Volume"].mean() if len(hist) >= 1 else volume
            flow_direction = "流入" if (change_pct or 0) >= 0 else "流出"
            flow_estimate = None
            if volume and price:
                flow_amt = volume * price * 0.15  # 估算主力资金占比15%
                flow_estimate = {
                    "direction": flow_direction,
                    "amount": flow_amt,
                    "label": f"约${flow_amt/1e6:.1f}M {'流入' if (change_pct or 0) >= 0 else '流出'}"
                }

            # 获取新闻
            news_items = []
            try:
                news = t.news or []
                for article in news[:5]:
                    news_items.append({
                        "title": article.get("title", ""),
                        "desc": article.get("summary", "")[:120] if article.get("summary") else "",
                        "source": article.get("publisher", "Yahoo Finance"),
                        "date": article.get("providerPublishTime", ""),
                        "link": article.get("link", "")
                    })
            except:
                pass

            results[ticker] = {
                "price": price,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "change_amt": round(change_amt, 2) if change_amt is not None else None,
                "high": high,
                "low": low,
                "volume": volume,
                "market_cap": market_cap,
                "name": STOCK_NAMES.get(ticker, ticker),
                "sector": SECTOR_MAP.get(ticker, "其他"),
                "flow": flow_estimate,
                "news": news_items,
                "advice": ADVICE_DATA.get(ticker, {
                    "rate": "hold", "rate_text": "持有",
                    "core": "等待分析师覆盖",
                    "pros": [], "cons": [],
                    "strategy": "暂观望", "risk": "中",
                    "target": "待更新"
                }),
                "update_time": datetime.now().strftime("%H:%M")
            }
            print(f"  ✅ {ticker} ({STOCK_NAMES.get(ticker, '')}): ${price}")
            time.sleep(0.5)  # 避免请求过快

        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
            results[ticker] = {
                "price": None, "change_pct": None, "change_amt": None,
                "high": None, "low": None, "volume": None, "market_cap": None,
                "name": STOCK_NAMES.get(ticker, ticker),
                "sector": SECTOR_MAP.get(ticker, "其他"),
                "flow": None, "news": [],
                "advice": ADVICE_DATA.get(ticker, {
                    "rate": "hold", "rate_text": "持有",
                    "core": "等待分析师覆盖",
                    "pros": [], "cons": [],
                    "strategy": "暂观望", "risk": "中",
                    "target": "待更新"
                }),
                "update_time": datetime.now().strftime("%H:%M")
            }
    return results

def save_data(data, tickers):
    """保存数据到JSON"""
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tickers": tickers,
        "stocks": data,
        "portfolio": {
            "invested_pct": 40,
            "floating_pnl_pct": -10,
            "goal": "稳定持续增长"
        }
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已保存: {DATA_FILE}")
    print(f"   共更新 {len(data)} 只股票")

def main():
    print(f"{'='*50}")
    print(f"  Move on Stock - 美股更新")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    tickers = load_config()
    print(f"\n📡 正在获取 {len(tickers)} 只美股数据: {', '.join(tickers)}")

    data = fetch_stock_data(tickers)
    save_data(data, tickers)

    # 统计
    success = sum(1 for v in data.values() if v["price"] is not None)
    print(f"\n📊 成功: {success}/{len(tickers)} 只")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
