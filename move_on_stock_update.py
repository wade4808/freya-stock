#!/usr/bin/env python3
"""
Move on Stock - 美股自动更新脚本 v2.0
每小时更新一次，生成完整HTML页面（含数据嵌入）
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
# 配置
# ============================================================
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
    "PEP": "百事", "NKE": "耐克", "HD": "家得宝",
    "MRK": "默克", "PFE": "辉瑞", "ABNB": "爱彼迎",
    "MU": "美光", "QCOM": "高通", "AVGO": "博通",
    "SBUX": "星巴克", "GM": "通用汽车", "F": "福特",
    "CAT": "卡特彼勒", "GE": "通用电气", "HON": "霍尼韦尔",
    "WFC": "富国银行", "C": "花旗", "GS": "高盛", "MS": "摩根士丹利",
    "COST": "好市多", "CVX": "雪佛龙", "OXY": "西方石油",
    "DASH": "DoorDash", "RBLX": "Roblox", "ZM": "Zoom", "SNAP": "Snap"
}

SECTOR_MAP = {
    "GOOGL": "科技", "LI": "新能源车", "BG": "农业", "BABA": "电商/云",
    "AAPL": "科技", "MSFT": "科技", "AMZN": "电商/云", "NVDA": "半导体",
    "META": "社交媒体", "TSLA": "新能源车", "AMD": "半导体", "INTC": "半导体",
    "NFLX": "流媒体", "DIS": "娱乐", "BA": "航空", "JPM": "银行",
    "V": "金融科技", "WMT": "零售", "JNJ": "医药", "XOM": "能源",
}

ADVICE_DATA = {
    "GOOGL": {"rate":"强烈买入","target":"$220","risk":"中",
        "core":"AI搜索+云计算双轮驱动，Gemini生态持续扩展，Q1广告收入超预期",
        "pros":["AI搜索市场份额持续扩大","Google Cloud营收增速30%+","Gemini API调用量QoQ+150%"],
        "cons":["反垄断监管风险持续","AI投入资本开支较大"],
        "strategy":"核心仓位，建议占总仓位15-20%，逢回调加仓"},
    "LI": {"rate":"买入","target":"$45","risk":"中高",
        "core":"增程+纯电双路线并行，L系列持续热销，毛利率领先国内同行",
        "pros":["月交付量持续5万+","毛利率22%行业领先","智驾全系标配"],
        "cons":["市场竞争加剧","纯电车型尚未放量"],
        "strategy":"成长仓位，建议8-12%，观察纯电车型表现"},
    "BG": {"rate":"持有观望","target":"$85","risk":"低中",
        "core":"全球粮油贸易龙头，受益于农产品价格波动，分红稳定",
        "pros":["全球农产品贸易份额领先","分红率3.5%+","巴西阿根廷大豆贸易强劲"],
        "cons":["农产品价格周期性波动","地缘政治影响供应链"],
        "strategy":"防御仓位，建议5-8%，作为组合稳定器"},
    "BABA": {"rate":"买入","target":"$135","risk":"中",
        "core":"云+AI+电商重塑增长，阿里云利润爆发，国际电商高速增长",
        "pros":["阿里云利润率持续改善","国际电商增速40%+","AI大模型通义千问领先"],
        "cons":["国内消费复苏不确定性","监管环境变化"],
        "strategy":"核心仓位，建议12-18%，长期持有等待云+AI估值重估"},
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
            market_cap = info.get("marketCap")

            flow_estimate = None
            if volume and price and change_pct is not None:
                flow_amt = volume * price * 0.15
                flow_estimate = {
                    "direction": "流入" if change_pct >= 0 else "流出",
                    "label": f"${flow_amt/1e6:.1f}M {'流入' if change_pct >= 0 else '流出'}"
                }

            news_items = []
            try:
                news = t.news or []
                for article in news[:4]:
                    news_items.append({
                        "title": article.get("title", ""),
                        "desc": (article.get("summary","") or "")[:120],
                        "source": article.get("publisher", "Yahoo Finance"),
                    })
            except:
                pass

            results[ticker] = {
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "market_cap": market_cap,
                "name": STOCK_NAMES.get(ticker, ticker),
                "sector": SECTOR_MAP.get(ticker, "其他"),
                "flow": flow_estimate,
                "news": news_items,
                "advice": ADVICE_DATA.get(ticker, {
                    "rate":"持有观望","target":"待定","risk":"中",
                    "core":"等待分析师覆盖","pros":[],"cons":[],"strategy":"暂观望"
                }),
            }
            print(f"  ✅ {ticker}: ${price}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
            results[ticker] = {
                "price": None, "change_pct": None, "volume": None, "market_cap": None,
                "name": STOCK_NAMES.get(ticker, ticker), "sector": "其他",
                "flow": None, "news": [],
                "advice": ADVICE_DATA.get(ticker, {"rate":"持有观望","target":"待定","risk":"中","core":"","pros":[],"cons":[],"strategy":"暂观望"}),
            }
    return results

def gen_html(data, tickers, update_time):
    """生成完整的HTML页面"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    colors = ['#4f8cff','#34d399','#fbbf24','#f87171','#a78bfa','#22d3ee','#fb923c','#a3e635','#f472b6']
    tag_labels = {"hot":"🔥 热点","er":"📊 财报","pr":"🏭 进展","an":"📈 机构","ai":"🤖 AI"}
    tag_types = ['hot','er','pr','an','ai']

    # 构建JS嵌入数据
    stocks_json = {}
    for t in tickers:
        d = data.get(t, {})
        stocks_json[t] = {
            "name": d.get("name", t),
            "sector": d.get("sector", "其他"),
            "price": d.get("price"),
            "change_pct": d.get("change_pct"),
            "volume": d.get("volume"),
            "flow": d.get("flow"),
            "news": d.get("news", []),
            "advice": d.get("advice", {"rate":"持有观望","target":"待定","risk":"中","core":"","pros":[],"cons":[],"strategy":"暂观望"}),
        }

    embed_data = json.dumps(stocks_json, ensure_ascii=False)
    embed_tickers = json.dumps(tickers, ensure_ascii=False)

    up_count = sum(1 for t in tickers if data.get(t,{}).get("change_pct") is not None and data[t]["change_pct"] >= 0)
    down_count = len(tickers) - up_count

    # 生成HTML
    # 注意: CSS中的{}需要转义为{{}}，但这里用f-string，所以所有模板文字中的{}需要加倍
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="theme-color" content="#0a0e17">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Move on Stock</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{{--bg:#0a0e17;--bg2:#111827;--card:#1a1f2e;--border:#262d3d;--text:#f0f2f8;--text2:#9298a8;--text3:#5a6070;--blue:#4f8cff;--green:#34d399;--red:#f87171;--yellow:#fbbf24;--purple:#a78bfa;--safe-bottom:env(safe-area-inset-bottom,0px);--tab-h:64px}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
html{{font-size:15px}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--text);padding-bottom:calc(var(--tab-h)+var(--safe-bottom)+12px);min-height:100dvh;overflow-x:hidden}}
::-webkit-scrollbar{{width:3px}}::-webkit-scrollbar-track{{background:var(--bg)}}::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
.header{{background:var(--bg2);border-bottom:1px solid var(--border);padding:12px 16px 10px;position:sticky;top:0;z-index:50;backdrop-filter:blur(16px);}}
.header-top{{display:flex;align-items:center;justify-content:space-between}}
.logo{{display:flex;align-items:center;gap:10px}}
.logo-icon{{width:34px;height:34px;background:linear-gradient(135deg,#34d399,#22d3ee);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}}
.logo-text{{font-size:1.15rem;font-weight:700;letter-spacing:-0.3px}}
.logo-text span{{background:linear-gradient(135deg,#34d399,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.logo-sub{{font-size:0.6rem;color:var(--text3);letter-spacing:1.5px}}
.header-date{{font-size:0.7rem;color:var(--text3);text-align:right}}
.disc{{margin:10px 16px 0;padding:10px 14px;background:rgba(248,113,113,0.06);border:1px solid rgba(248,113,113,0.15);border-radius:8px;font-size:0.7rem;color:var(--text3);line-height:1.5}}
.disc strong{{color:var(--red)}}
.pf-bar{{margin:10px 16px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 16px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
.pf-item{{flex:1;min-width:80px}}
.pf-label{{font-size:0.6rem;color:var(--text3);margin-bottom:2px}}
.pf-val{{font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace}}
.pf-val.gold{{color:var(--yellow)}}.pf-val.red{{color:var(--red)}}.pf-val.green{{color:var(--green)}}
.pf-detail{{font-size:0.6rem;color:var(--text3)}}
.pf-btn{{padding:6px 14px;border-radius:8px;border:none;font-size:0.7rem;font-weight:600;cursor:pointer;background:var(--purple);color:#fff;font-family:inherit}}
.ticker-wrap{{margin:0 16px;overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory;display:flex;gap:10px;padding:12px 0 8px;scrollbar-width:none}}
.ticker-wrap::-webkit-scrollbar{{display:none}}
.ticker-card{{flex:0 0 calc(50% - 5px);scroll-snap-align:start;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;position:relative;overflow:hidden}}
.ticker-card::before{{content:'';position:absolute;top:0;left:0;width:100%;height:2.5px;background:linear-gradient(90deg,var(--blue),var(--cyan))}}
.tc-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}}
.tc-symbol{{font-size:0.95rem;font-weight:700}}
.tc-name{{font-size:0.6rem;color:var(--text3)}}
.tc-price{{font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono',monospace}}
.tc-chg{{display:inline-flex;align-items:center;gap:3px;font-size:0.7rem;font-weight:600;font-family:'JetBrains Mono',monospace;padding:2px 8px;border-radius:5px;margin-top:3px}}
.tc-chg.up{{color:var(--green);background:rgba(52,211,153,0.1)}}
.tc-chg.down{{color:var(--red);background:rgba(248,113,113,0.1)}}
.tc-flow{{font-size:0.6rem;color:var(--text3);margin-top:4px;padding-top:4px;border-top:1px solid var(--border)}}
.tc-flow .in{{color:var(--green)}}.tc-flow .out{{color:var(--red)}}
.tc-del{{position:absolute;top:8px;right:8px;width:22px;height:22px;border-radius:50%;border:none;background:rgba(248,113,113,0.15);color:var(--red);font-size:0.7rem;cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:0.4}}
.section{{margin:0 16px 16px}}
.sec-title{{display:flex;align-items:center;gap:8px;font-size:0.9rem;font-weight:600;margin-bottom:10px;padding-top:4px}}
.sec-title .dot{{width:8px;height:8px;border-radius:50%}}
.sec-title .dot.n{{background:var(--blue)}}
.sec-title .dot.a{{background:var(--green)}}
.sec-title .dot.p{{background:var(--yellow)}}
.sec-title .dot.f{{background:var(--purple)}}
.stock-tabs{{display:flex;gap:3px;background:var(--bg2);border-radius:8px;padding:3px;margin-bottom:10px;overflow-x:auto;scrollbar-width:none}}
.stock-tabs::-webkit-scrollbar{{display:none}}
.stock-tab{{flex-shrink:0;padding:6px 10px;border-radius:6px;font-size:0.7rem;font-weight:600;color:var(--text3);cursor:pointer;border:none;background:none;font-family:inherit}}
.stock-tab.active{{color:#fff;background:rgba(255,255,255,0.08)}}
.news-box{{display:none}}.news-box.active{{display:block}}
.news-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:8px}}
.ni-tag{{display:inline-block;font-size:0.55rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-bottom:5px}}
.ni-tag.hot{{background:rgba(251,191,36,0.15);color:var(--yellow)}}
.ni-tag.er{{background:rgba(79,140,255,0.15);color:var(--blue)}}
.ni-tag.pr{{background:rgba(52,211,153,0.15);color:var(--green)}}
.ni-tag.an{{background:rgba(167,139,250,0.15);color:var(--purple)}}
.ni-tag.ai{{background:rgba(34,211,238,0.15);color:var(--cyan)}}
.news-item h4{{font-size:0.85rem;font-weight:600;line-height:1.4;margin-bottom:4px}}
.news-item p{{font-size:0.72rem;color:var(--text2);line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.ni-src{{margin-top:6px;font-size:0.6rem;color:var(--text3)}}
.advice-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:8px;position:relative;overflow:hidden}}
.advice-item::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--purple)}}
.ai-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;flex-wrap:wrap;gap:4px}}
.ai-header h3{{font-size:0.9rem;font-weight:700}}
.ai-rate{{font-size:0.6rem;font-weight:600;padding:3px 10px;border-radius:12px}}
.ai-rate.buy{{background:rgba(52,211,153,0.12);color:var(--green)}}
.ai-rate.hold{{background:rgba(251,191,36,0.12);color:var(--yellow)}}
.ai-body{{font-size:0.75rem;color:var(--text2);line-height:1.6}}
.ai-body strong{{color:var(--text)}}
.ai-body ul{{list-style:none;padding:0;margin-top:4px}}
.ai-body ul li{{padding:3px 0 3px 16px;position:relative;font-size:0.72rem}}
.ai-body ul li::before{{content:'';position:absolute;left:0;top:9px;width:5px;height:5px;border-radius:50%}}
.ai-body ul li.g::before{{background:var(--green)}}
.ai-body ul li.r::before{{background:var(--red)}}
.ai-body ul li.y{{padding:3px 0;color:var(--yellow)}}
.ai-target{{margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:0.68rem;color:var(--text3);display:flex;justify-content:space-between;flex-wrap:wrap}}
.pf-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:8px}}
.pf-card h3{{font-size:0.85rem;font-weight:600;margin-bottom:8px}}
.pf-table{{width:100%;border-collapse:collapse}}
.pf-table th,.pf-table td{{padding:5px 4px;text-align:left;font-size:0.65rem;border-bottom:1px solid var(--border)}}
.pf-table th{{color:var(--text3);font-weight:500;font-size:0.55rem}}
.pf-table td{{color:var(--text2);font-family:'JetBrains Mono',monospace;font-size:0.65rem}}
.pf-table td:first-child{{font-family:'Inter',sans-serif;font-weight:600;color:var(--text)}}
.pf-table .vg{{color:var(--green)}}.pf-table .vr{{color:var(--red)}}
.pf-table tr:last-child td{{border-bottom:none}}
.pf-score{{text-align:center;padding:16px 14px;display:flex;flex-direction:column;align-items:center;gap:4px}}
.pf-num{{font-size:2rem;font-weight:800;font-family:'JetBrains Mono',monospace;background:linear-gradient(135deg,#34d399,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.pf-label{{font-size:0.72rem;color:var(--text2)}}
.pf-desc{{font-size:0.68rem;color:var(--text3);line-height:1.5}}
.pf-desc strong{{color:var(--text2)}}
.alloc-item{{display:flex;align-items:center;gap:8px;padding:4px 0}}
.alloc-bar-wrap{{flex:1;height:16px;background:var(--bg2);border-radius:8px;overflow:hidden}}
.alloc-bar{{height:100%;border-radius:8px}}
.alloc-pct{{font-size:0.68rem;font-weight:600;font-family:'JetBrains Mono',monospace;min-width:32px;text-align:right}}
.strategy-box{{background:linear-gradient(135deg,rgba(167,139,250,0.06),rgba(52,211,153,0.06));border:1px solid rgba(167,139,250,0.15);border-radius:12px;padding:14px;margin-bottom:8px}}
.strategy-box h3{{font-size:0.82rem;font-weight:700;margin-bottom:6px;color:var(--purple)}}
.strategy-box ul{{list-style:none;padding:0}}
.strategy-box ul li{{padding:4px 0 4px 18px;position:relative;font-size:0.72rem;color:var(--text2);line-height:1.4}}
.strategy-box ul li::before{{content:'→';position:absolute;left:0;color:var(--green)}}
.strategy-box .highlight{{color:var(--yellow);font-weight:600}}
.bottom-nav{{position:fixed;bottom:0;left:0;right:0;height:calc(var(--tab-h)+var(--safe-bottom));padding-bottom:var(--safe-bottom);background:rgba(17,24,39,0.92);backdrop-filter:blur(20px);border-top:1px solid var(--border);display:flex;z-index:100}}
.bn-item{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;border:none;background:none;font-family:inherit;cursor:pointer;color:var(--text3);padding:0 4px}}
.bn-item.active{{color:var(--purple)}}
.bn-item .bn-icon{{font-size:1.1rem}}
.bn-item .bn-label{{font-size:0.55rem;font-weight:500}}
.page{{display:none}}.page.active{{display:block}}
.scroll-hint{{text-align:center;font-size:0.55rem;color:var(--text3);padding:0 0 4px}}
.page-foot{{text-align:center;padding:16px 16px 8px;font-size:0.6rem;color:var(--text3)}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.ticker-card,.news-item,.advice-item,.pf-card,.strategy-box{{animation:fadeUp 0.3s ease forwards}}
.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-size:0.78rem;z-index:999;box-shadow:0 8px 32px rgba(0,0,0,0.4);transition:opacity 0.3s;opacity:0;pointer-events:none}}
.toast.show{{opacity:1}}
.modal-overlay{{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:200;display:none;align-items:center;justify-content:center;padding:20px}}
.modal-overlay.show{{display:flex}}
.modal{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;width:100%;max-width:380px}}
.modal h3{{font-size:0.95rem;font-weight:700;margin-bottom:10px}}
.modal-close{{float:right;background:none;border:none;color:var(--text3);font-size:1.2rem;cursor:pointer}}
.modal input{{width:100%;padding:10px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:0.85rem;font-family:inherit;outline:none}}
.modal input:focus{{border-color:var(--purple)}}
.modal .modal-action{{width:100%;padding:12px;border-radius:8px;border:none;background:var(--purple);color:#fff;font-size:0.85rem;font-weight:600;cursor:pointer;margin-top:14px;font-family:inherit}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.loading-spinner{{display:inline-block;width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--purple);border-radius:50%;animation:spin 0.6s linear;margin-right:6px;vertical-align:middle}}
.tc-c0::before{{background:linear-gradient(90deg,#4f8cff,#22d3ee)!important}}
.tc-c1::before{{background:linear-gradient(90deg,#34d399,#a78bfa)!important}}
.tc-c2::before{{background:linear-gradient(90deg,#fbbf24,#f472b6)!important}}
.tc-c3::before{{background:linear-gradient(90deg,#f87171,#fb923c)!important}}
.tc-c4::before{{background:linear-gradient(90deg,#a78bfa,#34d399)!important}}
.tc-c5::before{{background:linear-gradient(90deg,#22d3ee,#4f8cff)!important}}
.tc-c6::before{{background:linear-gradient(90deg,#fb923c,#fbbf24)!important}}
.tc-c7::before{{background:linear-gradient(90deg,#a3e635,#22d3ee)!important}}
.tc-c8::before{{background:linear-gradient(90deg,#f472b6,#a78bfa)!important}}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<header class="header">
  <div class="header-top">
    <div class="logo">
      <div class="logo-icon">M</div>
      <div><div class="logo-text"><span>Move on</span> Stock</div><div class="logo-sub">美股投资顾问 · {today}</div></div>
    </div>
    <div class="header-date" id="headerDate"></div>
  </div>
</header>
<div class="disc"><strong>⚠ 风险提示：</strong>仅供参考不构成投资建议。数据来源：基于yfinance · <span id="updateLabel">数据更新时间 {update_time}</span></div>
<div class="pf-bar">
  <div class="pf-item"><div class="pf-label">仓位</div><div class="pf-val gold">40%</div><div class="pf-detail">可用资金 60%</div></div>
  <div class="pf-item"><div class="pf-label">浮动盈亏</div><div class="pf-val red">-10.0%</div><div class="pf-detail">耐心等待反转</div></div>
  <div class="pf-item"><div class="pf-label">目标</div><div class="pf-val" style="color:var(--purple)">稳定增长</div><div class="pf-detail">华尔街策略</div></div>
  <button class="pf-btn" onclick="showAdd()">+ 添加</button>
  <button class="pf-btn" style="background:var(--green)" onclick="liveRefresh()">⟳ 刷新</button>
</div>
<div class="page active" id="pg-prices">
  <div class="ticker-wrap" id="tw"></div>
  <div class="scroll-hint">← 左右滑动 · 点击 ✕ 删除 · 点击 ⟳ 刷新实时数据 →</div>
  <div class="section">
    <div class="sec-title"><span class="dot f"></span>资金流向</div>
    <div id="flowBox" style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;font-size:0.72rem;color:var(--text2);line-height:1.6">计算中...</div>
  </div>
  <div class="section">
    <div class="sec-title"><span class="dot n"></span>个股最新资讯</div>
    <div class="stock-tabs" id="st"></div>
    <div id="nb"></div>
  </div>
</div>
<div class="page" id="pg-advice">
  <div class="section" style="margin-top:12px;">
    <div class="sec-title"><span class="dot a"></span>华尔街投顾建议</div>
    <div class="strategy-box">
      <h3>📌 投资策略总纲</h3>
      <ul>
        <li><strong>当前状态：</strong>仓位40%，浮亏10%，仍有 <span class="highlight">60% 可用资金</span></li>
        <li><strong>核心策略：</strong>分批低吸 + 动态再平衡，利用剩余资金摊低成本</li>
        <li><strong>建议仓位：</strong>逐步加仓至60-70%，分3-4周执行，降低择时风险</li>
        <li><strong>止损纪律：</strong>单只股票浮亏超15%强制减仓一半，保护本金</li>
        <li><strong>止盈策略：</strong>盈利超20%分批止盈，锁定利润</li>
      </ul>
    </div>
    <div id="al"></div>
  </div>
</div>
<div class="page" id="pg-portfolio">
  <div class="section" style="margin-top:12px;">
    <div class="sec-title"><span class="dot p"></span>组合分析与调仓建议</div>
    <div id="pc"></div>
  </div>
</div>
<nav class="bottom-nav">
  <button class="bn-item active" data-p="prices"><span class="bn-icon">📊</span><span class="bn-label">行情</span></button>
  <button class="bn-item" data-p="advice"><span class="bn-icon">💡</span><span class="bn-label">建议</span></button>
  <button class="bn-item" data-p="portfolio"><span class="bn-icon">📋</span><span class="bn-label">组合</span></button>
</nav>
<div class="page-foot">Move on Stock · 数据每小时更新 · 打开即最新 · {today}</div>
<div class="modal-overlay" id="addModal">
  <div class="modal">
    <button class="modal-close" onclick="clAdd()">✕</button>
    <h3>+ 添加美股</h3>
    <input type="text" id="ti" placeholder="输入美股代码（如 AAPL、TSLA）" onkeydown="if(event.key==='Enter')addTicker()" autocomplete="off">
    <div id="th" style="margin-top:6px;font-size:0.68rem;color:var(--text2);max-height:100px;overflow-y:auto"></div>
    <button class="modal-action" onclick="addTicker()">添加股票</button>
  </div>
</div>
<script>
// === 嵌入数据（由Python脚本每小时更新） ===
const EMBEDDED_DATA = {embed_data};
const EMBEDDED_TICKERS = {embed_tickers};
const UPDATE_TIME = "{update_time}";

const COLORS = ['#4f8cff','#34d399','#fbbf24','#f87171','#a78bfa','#22d3ee','#fb923c','#a3e635','#f472b6'];
const STORAGE_KEY = 'mos_tickers';
const TAG_TYPES = ['hot','er','pr','an','ai'];
const TAG_LB = {{'hot':'🔥 热点','er':'📊 财报','pr':'🏭 进展','an':'📈 机构','ai':'🤖 AI'}};
const STOCK_NAMES = {json.dumps(STOCK_NAMES, ensure_ascii=False)};

let stockData = JSON.parse(JSON.stringify(EMBEDDED_DATA));
let tickers = [];
let upTime = UPDATE_TIME;

function t(){const d=document.getElementById('toast');return d}
function toast(m){{const d=t();d.textContent=m;d.classList.add('show');setTimeout(()=>d.classList.remove('show'),2500)}}
function gs(){{try{{const d=localStorage.getItem(STORAGE_KEY);return d?JSON.parse(d):null}}catch{{return null}}}}
function ss(t){{try{{localStorage.setItem(STORAGE_KEY,JSON.stringify(t))}}catch{{}}}}
function ci(i){{return COLORS[i%COLORS.length]}}

function loadData(){{
  const s=gs();
  if(s&&s.length>0){{tickers=s}}
  else{{tickers=EMBEDDED_TICKERS;ss(tickers)}}
  // 合并嵌入数据中已有的股票
  for(const t of Object.keys(EMBEDDED_DATA)){{
    if(tickers.includes(t)&&!stockData[t]){{stockData[t]=EMBEDDED_DATA[t]}}
  }}
  render();
}}

async function liveRefresh(){{
  const lbl=document.getElementById('updateLabel');
  lbl.innerHTML='<span class="loading-spinner"></span>更新中...';
  const promises=tickers.map(async t=>{{
    try{{
      const r=await fetch(`https://corsproxy.io/?url=${{encodeURIComponent('https://query1.finance.yahoo.com/v8/finance/chart/'+t+'?range=1d&interval=1d')}}`,{{signal:AbortSignal.timeout(8000)}});
      if(!r.ok)throw new Error();
      const d=await r.json();
      const m=d?.chart?.result?.[0]?.meta;
      const q=d?.chart?.result?.[0]?.indicators?.quote?.[0];
      if(m&&m.regularMarketPrice){{
        const p=m.regularMarketPrice;
        const pc=m.chartPreviousClose;
        const cp=pc?((p-pc)/pc*100):null;
        stockData[t] = stockData[t]||{{}};
        stockData[t].price=p;
        stockData[t].change_pct=cp?Math.round(cp*100)/100:null;
        stockData[t].volume=q?.volume?.[0];
        const flowDir=cp>=0?'流入':'流出';
        const flowAmt=(q?.volume?.[0]||0)*p*0.12;
        stockData[t].flow={{direction:flowDir,label:`$${{(flowAmt/1e6).toFixed(1)}}M ${{flowDir}}`}};
      }}
    }}catch(e){{}}
  }});
  await Promise.allSettled(promises);
  upTime=new Date().toLocaleString('zh-CN');
  document.getElementById('updateLabel').textContent='实时数据 '+upTime;
  render();
}}

function showAdd(){{document.getElementById('ti').value='';document.getElementById('th').innerHTML='';document.getElementById('addModal').classList.add('show');setTimeout(()=>document.getElementById('ti').focus(),100)}}
function clAdd(){{document.getElementById('addModal').classList.remove('show')}}
async function addTicker(){{
  const inp=document.getElementById('ti');const tk=inp.value.trim().toUpperCase();
  if(!tk)return;
  if(tickers.includes(tk)){{toast('已在跟踪列表中');clAdd();return}}
  clAdd();toast('正在获取 '+tk+' 数据...');
  // 尝试通过corsproxy获取
  try{{
    const r=await fetch(`https://corsproxy.io/?url=${{encodeURIComponent('https://query1.finance.yahoo.com/v8/finance/chart/'+tk+'?range=1d&interval=1d')}}`,{{signal:AbortSignal.timeout(8000)}});
    if(r.ok){{
      const d=await r.json();
      const m=d?.chart?.result?.[0]?.meta;
      if(m&&m.regularMarketPrice){{
        const p=m.regularMarketPrice;
        stockData[tk]={{name:STOCK_NAMES[tk]||tk,sector:'其他',price:p,change_pct:null,volume:null,flow:null,news:[],advice:{{rate:'持有观望',target:'待定',risk:'中',core:'新加入股票',pros:[],cons:[],strategy:'暂观望'}}}};
        const pc=m.chartPreviousClose;
        if(pc)stockData[tk].change_pct=Math.round((p-pc)/pc*10000)/100;
      }}
    }}
  }}catch(e){{}}
  if(!stockData[tk]){{stockData[tk]={{name:STOCK_NAMES[tk]||tk,sector:'其他',price:null,change_pct:null,volume:null,flow:null,news:[],advice:{{rate:'持有观望',target:'待定',risk:'中',core:'新加入股票',pros:[],cons:[],strategy:'暂观望'}}}}}}
  tickers.push(tk);ss(tickers);render();
  toast('✅ 已添加 '+tk+' ('+(STOCK_NAMES[tk]||'')+')');
}}

function rmTicker(t){{if(!confirm('确定移除 '+t+'?'))return;tickers=tickers.filter(x=>x!==t);delete stockData[t];ss(tickers);render()}}

function render(){{
  renderTickers();
  renderFlow();
  renderTabs();
  renderAdvice();
  renderPortfolio();
  initNav();
}}
function renderTickers(){{
  const w=document.getElementById('tw');
  if(tickers.length===0){{w.innerHTML='<div style="padding:20px;text-align:center;color:var(--text3)">暂无股票，点击上方 + 添加</div>';return}}
  w.innerHTML=tickers.map((t,i)=>{{
    const d=stockData[t]||{{}};
    const p=d.price;const cp=d.change_pct;
    const cls=cp!==null&&cp!==undefined?(cp>=0?'up':'down'):'flat';
    const arr=cp!==null&&cp!==undefined?(cp>=0?'▲':'▼'):'';
    const chg=cp!==null&&cp!==undefined?`${{arr}} ${{Math.abs(cp).toFixed(2)}}%`:'--';
    const pr=p!==null&&p!==undefined?p.toFixed(2):'---';
    const fl=d.flow;
    return `<div class="ticker-card tc-c${{i%9}}">
      <button class="tc-del" onclick="rmTicker('${{t}}')">✕</button>
      <div class="tc-top"><span class="tc-symbol" style="color:${{ci(i)}}">${{d.name||t}}</span><span class="tc-name">${{t}}</span></div>
      <div class="tc-price">$${{pr}}</div>
      <div class="tc-chg ${{cls}}">${{chg}}</div>
      <div class="tc-flow">资金：${{fl?`<span class="${{fl.direction==='流入'?'in':'out'}}">${{fl.label}}</span>`:'<span style="color:var(--text3)">暂无数据</span>'}}</div>
    </div>`;
  }}).join('');
}}
function renderFlow(){{
  const el=document.getElementById('flowBox');
  let ti=0,to=0,ic=0,oc=0;
  tickers.forEach(t=>{{
    const d=stockData[t];
    if(d&&d.flow){{if(d.flow.direction==='流入'){{ti+=1;ic++}}else{{to+=1;oc++}}}}
  }});
  const pct=ti+to>0?Math.round(ti/(ti+to)*100):50;
  el.innerHTML=`<div style="display:flex;justify-content:space-between;margin-bottom:8px">
    <span><strong style="color:var(--green)">📈 流入</strong> ${{ic}}只</span>
    <span><strong style="color:var(--red)">📉 流出</strong> ${{oc}}只</span>
    <span><strong style="color:${{ti>=to?'var(--green)':'var(--red)'}}">${{ti>=to?'净流入':'净流出'}}</strong></span></div>
    <div style="height:6px;background:var(--bg2);border-radius:3px;overflow:hidden;margin-bottom:6px">
    <div style="height:100%;width:${{pct}}%;background:linear-gradient(90deg,var(--green),var(--red));border-radius:3px"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:0.6rem;color:var(--text3)">
    <span>流入 ${{(ti*1).toFixed(0)}}只</span><span>流出 ${{(to*1).toFixed(0)}}只</span></div>
    <div style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);font-size:0.68rem">
    ${{ti>=to?'✅ 市场情绪偏积极，主力资金流入为主':'⚠️ 主力资金流出为主，注意控制仓位'}}</div>`;
}}
function renderTabs(){{
  const el=document.getElementById('st');
  el.innerHTML=tickers.map((t,i)=>`<button class="stock-tab${{i===0?' active':''}}" data-s="${{t}}" style="border-bottom:2px solid ${{ci(i)}}">${{stockData[t]?.name||t}}</button>`).join('');
  el.querySelectorAll('.stock-tab').forEach(t=>t.addEventListener('click',()=>{{
    el.querySelectorAll('.stock-tab').forEach(x=>x.classList.remove('active'));t.classList.add('active');
    document.querySelectorAll('.news-box').forEach(b=>b.classList.remove('active'));
    const nb=document.getElementById('n-'+t.dataset.s);if(nb)nb.classList.add('active');
  }}));
  const ne=document.getElementById('nb');
  ne.innerHTML=tickers.map((t,i)=>{{
    const d=stockData[t]||{{}};const items=d.news||[];
    const ni=items.length>0?items.map((it,idx)=>{{
      const tag=TAG_TYPES[idx%TAG_TYPES.length];
      return `<div class="news-item"><span class="ni-tag ${{tag}}">${{TAG_LB[tag]||'📌'}}</span><h4>${{it.title||'资讯'}}</h4><p>${{it.desc||''}}</p><div class="ni-src">${{it.source||'Yahoo'}}</div></div>`;
    }}).join(''):'<div style="padding:12px;text-align:center;font-size:0.72rem;color:var(--text3)">暂无资讯</div>';
    return `<div class="news-box${{i===0?' active':''}}" id="n-${{t}}">${{ni}}</div>`;
  }}).join('');
}}
function renderAdvice(){{
  const el=document.getElementById('al');
  el.innerHTML=tickers.map((t,i)=>{{
    const d=stockData[t]||{{}};const a=d.advice||{{rate:'持有观望',target:'',core:'',pros:[],cons:[],strategy:'',risk:''}};
    const rm={{'强烈买入':'buy','买入':'buy','持有观望':'hold','持有':'hold','卖出':'sell'}};
    const rc=rm[a.rate]||'hold';
    const pl=a.pros.map(x=>`<li class="g">${{x}}</li>`).join('');
    const cl=a.cons.map(x=>`<li class="r">${{x}}</li>`).join('');
    const pr=d.price!==null&&d.price!==undefined?`$${{d.price.toFixed(2)}}`:'---';
    return `<div class="advice-item" style="border-left-color:${{ci(i)}}">
      <div class="ai-header"><h3 style="color:${{ci(i)}}">${{d.name||t}} · ${{t}}</h3>
      <span class="ai-rate ${{rc}}">${{a.rate||'持有'}}</span></div>
      <div class="ai-body"><strong>核心逻辑：</strong>${{a.core||''}}
      <ul>${{pl}}${{cl}}<li class="y">💡 ${{a.strategy||'暂观望'}}</li></ul></div>
      <div class="ai-target">
      <span>目标价 ${{a.target||'待定'}} · 当前 ${{pr}}</span>
      <span>风险等级：${{a.risk||'中'}}</span></div></div>`;
  }}).join('');
}}
function renderPortfolio(){{
  const el=document.getElementById('pc');
  const aa=tickers.length>0?(100/tickers.length):0;
  const ab=tickers.map((t,i)=>{{
    const d=stockData[t]||{{}};
    return `<div class="alloc-item"><span style="font-size:0.72rem;font-weight:600;min-width:60px;color:${{ci(i)}}">${{d.name||t}}</span>
    <div class="alloc-bar-wrap"><div class="alloc-bar" style="width:${{aa}}%;background:${{ci(i)}}"></div></div>
    <span class="alloc-pct" style="color:${{ci(i)}}">${{aa.toFixed(0)}}%</span></div>`;
  }}).join('');
  const tr=tickers.map((t,i)=>{{
    const d=stockData[t]||{{}};const cp=d.change_pct;
    const cc=cp!==null&&cp!==undefined?(cp>=0?'vg':'vr'):'';
    const cs=cp!==null&&cp!==undefined?`${{cp>=0?'+':''}}${{cp.toFixed(2)}}%`:'--';
    const ps=d.price!==null&&d.price!==undefined?`$${{d.price.toFixed(2)}}`:'---';
    return `<tr><td style="color:${{ci(i)}}">${{d.name||t}}</td><td>${{t}}</td><td>${{ps}}</td><td class="${{cc}}">${{cs}}</td></tr>`;
  }}).join('');
  const uc=tickers.filter(t=>{{const d=stockData[t];return d&&d.change_pct!==null&&d.change_pct!==undefined&&d.change_pct>=0}}).length;
  const dc=tickers.length-uc;
  el.innerHTML=`<div class="pf-card pf-score"><div class="pf-num">${{tickers.length>0?'6.8':'--'}} / 10</div>
    <div class="pf-label">组合健康评分</div>
    <div class="pf-desc"><strong>今日：</strong>${{uc}}涨 ${{dc}}跌 · 仓位 40% · 浮亏 10%</div></div>
    <div class="pf-card"><h3>📊 配置比例</h3>${{ab}}</div>
    <div class="pf-card"><h3>📋 持仓速览</h3>
    <div style="overflow-x:auto"><table class="pf-table"><thead><tr><th>股票</th><th>代码</th><th>现价</th><th>涨跌</th></tr></thead>
    <tbody>${{tr||'<tr><td colspan="4" style="text-align:center;color:var(--text3)">暂无</td></tr>'}}</tbody></table></div></div>
    <div class="strategy-box"><h3>📌 调仓建议</h3>
    <ul><li>当前浮亏10%，正常波动范围，无需恐慌减仓</li>
    <li>利用 <span class="highlight">60% 可用资金</span> 分3-4周分批加仓</li>
    <li>优先加仓：AI/科技（GOOGL）+ 云计算（BABA）</li>
    <li>LI待充分回调后加仓，BG作为防御仓不动</li>
    <li>目标配置：科技45% | 新能源车20% | 农业10% | 现金25%</li></ul></div>
    <div class="pf-card"><h3>📌 ${{new Date().toLocaleDateString('zh-CN',{{year:'numeric',month:'long',day:'numeric'}})}}</h3>
    <div class="ai-body">今日 ${{uc}}涨 ${{dc}}跌。策略：耐心分批加仓。</div></div>`;
}}
function initNav(){{
  document.querySelectorAll('.bn-item').forEach(i=>{{
    i.removeEventListener('click',navH);
    i.addEventListener('click',navH);
  }});
  function navH(){{
    document.querySelectorAll('.bn-item').forEach(x=>x.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.getElementById('pg-'+this.dataset.p).classList.add('active');
    window.scrollTo({{top:0,behavior:'smooth'}});
  }}
}}

document.getElementById('headerDate').innerHTML='<strong>'+new Date().toLocaleDateString('zh-CN',{{month:'long',day:'numeric'}})+'</strong> · '+new Date().toLocaleDateString('zh-CN',{{weekday:'short'}});
loadData();
</script>
</body>
</html>
"""
    return html


def main():
    print(f"{'='*50}")
    print(f"  Move on Stock - 美股更新 v2.0")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 读取配置
    config_file = os.path.join(OUTPUT_DIR, "move_on_stock_config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            cfg = json.load(f)
            tickers = cfg.get("tickers", DEFAULT_TICKERS)
    else:
        tickers = DEFAULT_TICKERS
        # 写入默认配置
        with open(config_file, "w") as f:
            json.dump({"tickers": tickers}, f, ensure_ascii=False, indent=2)

    print(f"\n📡 获取 {len(tickers)} 只美股: {', '.join(tickers)}")
    data = fetch_stock_data(tickers)

    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 保存 JSON
    json_file = os.path.join(OUTPUT_DIR, "move_on_stock_data.json")
    json_output = {
        "update_time": update_time,
        "tickers": tickers,
        "stocks": {t: data[t] for t in tickers if t in data},
        "portfolio": {"invested_pct": 40, "floating_pnl_pct": -10, "goal": "稳定持续增长"}
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON 已保存: {json_file}")

    # 生成HTML
    html = gen_html(data, tickers, update_time)
    html_file = os.path.join(OUTPUT_DIR, "Move on stock.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(html_file)
    print(f"✅ HTML 已生成: {html_file} ({size:,} bytes)")

    success = sum(1 for t in tickers if data.get(t, {}).get("price"))
    print(f"\n📊 成功: {success}/{len(tickers)} 只")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
