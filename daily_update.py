#!/usr/bin/env python3
"""
Freya's Stock 自动更新脚本 v2.0
使用东方财富实时API获取A股行情和新闻，每天收盘后自动更新
"""

import json, os, sys, time
from datetime import datetime

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ============================================================
# 配置
# ============================================================
STOCKS = [
    {"name": "亨通光电", "code": "600487", "mkt": 1, "color": "#4f8cff", "sector": "通信", "sector_en": "tech"},
    {"name": "沪电股份", "code": "002463", "mkt": 0, "color": "#34d399", "sector": "PCB", "sector_en": "tech"},
    {"name": "生益科技", "code": "600183", "mkt": 1, "color": "#fbbf24", "sector": "覆铜板", "sector_en": "tech"},
    {"name": "亨通股份", "code": "600226", "mkt": 1, "color": "#f472b6", "sector": "多元", "sector_en": "chem"},
    {"name": "紫金矿业", "code": "601899", "mkt": 1, "color": "#fb923c", "sector": "矿业", "sector_en": "resource"},
    {"name": "景旺电子", "code": "603228", "mkt": 1, "color": "#a78bfa", "sector": "PCB", "sector_en": "tech"},
    {"name": "洛阳钼业", "code": "603993", "mkt": 1, "color": "#22d3ee", "sector": "矿业", "sector_en": "resource"},
    {"name": "中国神华", "code": "601088", "mkt": 1, "color": "#a3e635", "sector": "煤炭", "sector_en": "energy"},
    {"name": "华光环能", "code": "600475", "mkt": 1, "color": "#f87171", "sector": "环保", "sector_en": "energy"},
]

OUTPUT_FILE = "index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/"
}

# ============================================================
# 获取实时行情（东方财富 API）
# ============================================================
def fetch_prices():
    """从东方财富获取实时行情"""
    # 批量获取所有股票行情
    secids = ",".join([f"{s['mkt']}.{s['code']}" for s in STOCKS])
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": 2,
        "invt": 2,
        "fields": "f2,f3,f4,f12,f14,f15,f16,f17,f18,f20,f21",
        "secids": secids
    }

    results = {}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                code = str(item.get("f12", ""))
                results[code] = {
                    "price": item.get("f2"),
                    "change_pct": item.get("f3"),
                    "change_amt": item.get("f4"),
                    "high": item.get("f15"),
                    "low": item.get("f16"),
                    "open": item.get("f17"),
                    "volume": item.get("f18"),
                    "amount": item.get("f20"),
                }
        print(f"✅ 行情API返回 {len(results)} 只数据")
    except Exception as e:
        print(f"⚠️ 行情API失败: {e}")

    return results


# ============================================================
# 获取个股新闻（东方财富 API）
# ============================================================
def fetch_news_batch():
    """批量获取9只股票的最新新闻"""
    all_news = {}
    tag_types = ["hot", "er", "pr", "rk", "an", "ai"]

    for s in STOCKS:
        secid = f"{s['mkt']}.{s['code']}"
        news_list = []

        try:
            url = "https://push2.eastmoney.com/api/qt/stock/news/get"
            params = {"secid": secid, "count": 6}
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = resp.json()

            if data.get("data") and data["data"].get("list"):
                articles = data["data"]["list"]
                for i, art in enumerate(articles[:4]):
                    title = art.get("title", "").replace("&#xA0;", "").strip()
                    if not title:
                        continue
                    content = art.get("content", "")[:80] if art.get("content") else ""
                    if not content:
                        content = art.get("intro", "")[:80] if art.get("intro") else ""
                    date_str = art.get("date", "")
                    source = art.get("source", "东方财富")
                    tag = tag_types[i % len(tag_types)]

                    news_list.append({
                        "title": title,
                        "desc": content,
                        "source": f"{source}",
                        "tag": tag,
                        "date": date_str
                    })

            # Also try the search API for supplementary news
            if len(news_list) < 3:
                try:
                    search_url = "https://search-api-web.eastmoney.com/search/jsonp"
                    search_params = {
                        "param": json.dumps({
                            "uid": "",
                            "keyword": s["name"],
                            "type": ["cmsArticleWebOld"],
                            "client": "web",
                            "clientType": "web",
                            "clientVersion": "curr",
                            "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default", "pageIndex": 1, "pageSize": 5}}
                        })
                    }
                    sresp = requests.get(search_url, params=search_params, headers=HEADERS, timeout=10)
                    sdata = sresp.json()
                    # Parse the search results
                    if sdata.get("result") and sdata["result"].get("cmsArticleWebOld", {}).get("list"):
                        for art in sdata["result"]["cmsArticleWebOld"]["list"]:
                            if len(news_list) >= 4:
                                break
                            title = art.get("title", "").replace("&#xA0;", "").strip()
                            if not title or any(n["title"] == title for n in news_list):
                                continue
                            news_list.append({
                                "title": title,
                                "desc": art.get("summary", "")[:80] if art.get("summary") else "",
                                "source": art.get("source", ""),
                                "tag": tag_types[len(news_list) % len(tag_types)],
                                "date": ""
                            })
                except Exception:
                    pass

            all_news[s["name"]] = news_list
            print(f"  {s['name']}: {len(news_list)} 条新闻")

        except Exception as e:
            print(f"  ⚠️ {s['name']} 新闻获取失败: {e}")
            all_news[s["name"]] = []

        time.sleep(0.3)  # 避免触发风控

    return all_news


# ============================================================
# 备用新闻（API失败时使用）
# ============================================================
FALLBACK_NEWS = {
    "亨通光电": [
        {"title": "亨通光电光通信量价齐升 Q1净利+98%", "desc": "AI数据中心驱动光纤需求，空芯光纤商用持续落地", "source": "自动更新", "tag": "er"},
        {"title": "亨通光电中标中国电信空芯光缆项目", "desc": "空芯光纤衰减指标达0.03-0.08dB/km，技术领先", "source": "自动更新", "tag": "hot"},
    ],
    "沪电股份": [
        {"title": "沪电股份AI服务器PCB需求旺盛", "desc": "Q1净利+62.9%，泰国工厂营收超2025全年", "source": "自动更新", "tag": "er"},
        {"title": "沪电股份布局CoWoP/mSAP技术", "desc": "在常州设立子公司，布局下一代封装技术", "source": "自动更新", "tag": "ai"},
    ],
    "生益科技": [
        {"title": "生益科技覆铜板双轮驱动", "desc": "覆铜板+PCB高端化，AI材料批量供货", "source": "自动更新", "tag": "pr"},
        {"title": "松山湖52亿高性能覆铜板项目推进", "desc": "计划2026年下半年启动，产能扩张进行中", "source": "自动更新", "tag": "hot"},
    ],
    "亨通股份": [
        {"title": "亨通股份氨基酸项目投产", "desc": "Q1营收同比+82%，铜箔业务国产替代空间大", "source": "自动更新", "tag": "er"},
        {"title": "杠杆资金加速流入亨通股份", "desc": "融资余额增幅超100%，关注度显著提升", "source": "自动更新", "tag": "hot"},
    ],
    "紫金矿业": [
        {"title": "紫金矿业Q1归母净利200.8亿+97.5%", "desc": "铜金价格高位运行，业绩爆发式增长", "source": "自动更新", "tag": "er"},
        {"title": "20家机构覆盖紫金矿业", "desc": "买入15家增持5家，目标均价44.95元", "source": "自动更新", "tag": "an"},
    ],
    "景旺电子": [
        {"title": "景旺电子AI服务器PCB量产", "desc": "800G光模块批量供货，1.6T积极推进", "source": "自动更新", "tag": "ai"},
        {"title": "景旺电子珠海泰国双基地推进", "desc": "产能扩张有序进行，中长期增长可期", "source": "自动更新", "tag": "pr"},
    ],
    "洛阳钼业": [
        {"title": "洛阳钼业Q1净利77.6亿+96.66%", "desc": "铜金钨全面开花，铜金双极战略初现", "source": "自动更新", "tag": "er"},
        {"title": "洛阳钼业每股派0.286元", "desc": "合计派发约61亿元，分红方案已公布", "source": "自动更新", "tag": "hot"},
    ],
    "中国神华": [
        {"title": "神华4月发电量同比+14.8%", "desc": "煤炭销售+0.2%，电力业务快速增长", "source": "自动更新", "tag": "pr"},
        {"title": "20家机构买入评级 目标价53.81", "desc": "负债率仅29%，高股息防御配置首选", "source": "自动更新", "tag": "an"},
    ],
    "华光环能": [
        {"title": "华光环能氢能电解槽技术领先", "desc": "1500Nm³/h达行业最高压力，500MW基地已建成", "source": "自动更新", "tag": "ai"},
        {"title": "华光环能海外市场持续拓展", "desc": "签约印尼伊拉克等多国，海外收入目标+40%", "source": "自动更新", "tag": "pr"},
    ],
}


# ============================================================
# 获取备用行情（API失败时使用搜索结果）
# ============================================================
def fetch_fallback_price(name):
    """从搜索结果中获取备用价格数据"""
    # 从上次搜索缓存中读取（如果存在）
    cache_file = ".price_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    return {}


# ============================================================
# 生成 HTML
# ============================================================
COLOR_MAP = {s["name"]: s["color"] for s in STOCKS}

ADVICE_DATA = {
    "亨通光电": {"rate": "bull", "rate_text": "积极看多", "cat": "tech",
        "core": "AI数据中心驱动光纤需求爆发，空芯光纤全球领先",
        "pros": ["Q1净利+98%，AI长协订单充足", "空芯光纤商用持续落地", "机构密集调研"],
        "cons": ["年内涨幅已大，有回调风险"],
        "action": "强势标的可持有，注意高位波动", "target": "机构关注度极高"},
    "沪电股份": {"rate": "bull", "rate_text": "积极看多", "cat": "tech",
        "core": "AI服务器PCB核心供应商，泰国工厂超预期放量",
        "pros": ["Q1净利+62.9%创新高", "泰国工厂营收超2025全年", "布局CoWoP/mSAP技术"],
        "cons": ["短期主力资金有流出"],
        "action": "AI PCB龙头，可中长期持有", "target": "机构目标价 114.5"},
    "生益科技": {"rate": "bull", "rate_text": "谨慎看多", "cat": "tech",
        "core": "覆铜板+PCB双轮驱动，AI+航天双概念加持",
        "pros": ["Q1净利+44%", "AI低损耗材料批量供货", "松山湖52亿项目推进"],
        "cons": ["高管拟减持，短期涨幅大"],
        "action": "中期看好，注意回调风险", "target": "多家机构买入评级"},
    "亨通股份": {"rate": "wait", "rate_text": "谨慎观望", "cat": "chem",
        "core": "营收大增但估值高位，铜箔业务有看点",
        "pros": ["Q1营收+82%", "铜箔国产替代有空间"],
        "cons": ["PE处历史96%分位", "股权质押风险"],
        "action": "小仓位或观望，注意高估值风险", "target": "动态PE较高"},
    "紫金矿业": {"rate": "mix", "rate_text": "逢低关注", "cat": "resource",
        "core": "Q1净利翻倍，铜金高位运行，回调后吸引力增强",
        "pros": ["Q1净利+97.5%", "机构目标价44.95空间48%"],
        "cons": ["近期主力资金持续流出"],
        "action": "逢回调分批低吸长线持有", "target": "机构目标价 44.95"},
    "景旺电子": {"rate": "mix", "rate_text": "中期看好", "cat": "tech",
        "core": "AI高端PCB+光模块核心标的，新产能即将释放",
        "pros": ["AI服务器PCB量产", "800G光模块批量供货", "珠海泰国双基地推进"],
        "cons": ["Q1利润降28%"],
        "action": "关注产能释放，中期布局", "target": "机构目标价 75.43"},
    "洛阳钼业": {"rate": "mix", "rate_text": "逢低关注", "cat": "resource",
        "core": "铜金钨全面开花，Q1净利+97%，分红在即",
        "pros": ["Q1净利+96.7%", "5月27日分红除权", "22家机构买入"],
        "cons": ["近期连续回调"],
        "action": "分红前可关注，中长期持有", "target": "机构目标价 25.66"},
    "中国神华": {"rate": "bull", "rate_text": "稳健配置", "cat": "energy",
        "core": "煤炭+电力一体化龙头，防守属性强",
        "pros": ["负债率仅29%", "发电量+14.8%", "20家机构买入目标价53.81"],
        "cons": ["Q1净利-10.7%", "煤价偏弱"],
        "action": "组合防御配置可长期持有", "target": "机构目标价 53.81"},
    "华光环能": {"rate": "wait", "rate_text": "关注转型", "cat": "energy",
        "core": "氢能+火改+海外三线并进，转型预期强",
        "pros": ["氢能电解槽技术领先", "火改NOx降40%+", "海外多国签约"],
        "cons": ["Q1营收-6.4%净利-10%"],
        "action": "关注氢能+火改订单落地", "target": "华安证券增持评级"},
}

SECTOR_CN = {"tech": "科技制造", "resource": "资源", "energy": "能源", "chem": "多元"}

def gen_html(prices, news_data, today):
    up = sum(1 for s in STOCKS if prices.get(s["code"], {}).get("price") and prices[s["code"]].get("change_pct", 0) >= 0)
    down = len(STOCKS) - up

    tickers = ""
    for s in STOCKS:
        sid = s["code"]
        p = prices.get(sid, {})
        price = p.get("price", "---")
        chg = p.get("change_pct")
        if chg is not None:
            cls = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            chg_s = f"{arr} {abs(chg):.2f}%"
        else:
            cls, chg_s = "flat", "待更新"
        tickers += f'''
    <div class="ticker-card tc">
      <div class="tc-top">
        <span class="tc-symbol" style="color:{s['color']}">{s['name']}</span>
        <span class="tc-name">{sid}</span>
      </div>
      <div class="tc-price">{price}</div>
      <div class="tc-chg {cls}">{chg_s}</div>
    </div>'''

    tabs = ""
    news_boxes = ""
    for i, s in enumerate(STOCKS):
        sid = s["code"]
        act = " active" if i == 0 else ""
        tabs += f'''
      <button class="stock-tab{act}" data-s="{sid}" style="border-bottom:2px solid {s['color']}">{s['name']}</button>'''

        items = news_data.get(s["name"], [])
        if not items:
            items = FALLBACK_NEWS.get(s["name"], [{"title": f"{s['name']} 资讯更新中", "desc": "请稍后刷新查看", "source": "系统", "tag": "er"}])

        ni = ""
        tag_map = {"hot": ("hot", "🔥 热点"), "er": ("er", "📊 财报"), "pr": ("pr", "🏭 进展"),
                   "rk": ("rk", "⚠ 风险"), "an": ("an", "📈 机构"), "ai": ("ai", "🤖 AI"), "bb": ("bb", "🔄 回购")}
        for it in items[:4]:
            t, lb = tag_map.get(it.get("tag", "er"), ("er", "📊"))
            ni += f'''
      <div class="news-item">
        <span class="ni-tag {t}">{lb}</span>
        <h4>{it["title"]}</h4>
        <p>{it.get("desc", "")}</p>
        <div class="ni-src">{it.get("source", "东方财富")}</div>
      </div>'''

        news_boxes += f'''
    <div class="news-box{act}" id="n-{sid}">{ni}</div>'''

    advice = ""
    for s in STOCKS:
        a = ADVICE_DATA.get(s["name"], {})
        r = a.get("rate", "wait")
        rt = a.get("rate_text", "关注")
        ct = SECTOR_CN.get(a.get("cat", "tech"), "")
        pl = "".join([f'<li class="g">{x}</li>' for x in a.get("pros", [])])
        cl = "".join([f'<li class="r">{x}</li>' for x in a.get("cons", [])])
        pv = prices.get(s["code"], {}).get("price", "---")
        advice += f'''
    <div class="advice-item" style="border-left-color:{s['color']}">
      <div class="ai-header">
        <h3 style="color:{s['color']}">{s['name']} {s['code']} <span class="cat-badge {a.get('cat','tech')}">{ct}</span></h3>
        <span class="ai-rate {r}">{rt}</span>
      </div>
      <div class="ai-body"><strong>核心：</strong>{a.get("core","")}{pl}{cl}<li class="y">建议：{a.get("action","")}</li></ul></div>
      <div class="ai-target">{a.get("target","")} · 当前 {pv}</div>
    </div>'''

    rows = ""
    for s in STOCKS:
        p = prices.get(s["code"], {})
        chg = p.get("change_pct")
        chg_cls = "vg" if chg is not None and chg >= 0 else "vr"
        chg_s = f"{chg:+.2f}%" if chg is not None else "待更新"
        rows += f'''
          <tr><td>{s['name']}</td><td>{s['code']}</td><td>{p.get('price','---')}</td><td class="{chg_cls}">{chg_s}</td><td style="font-size:0.6rem;color:{s['color']}">{s['sector']}</td></tr>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="theme-color" content="#0a0e17">
<title>Freya's Stock</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
  html{{font-size:15px}}
  body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0e17;color:#f0f2f8;padding-bottom:calc(64px+env(safe-area-inset-bottom,0px)+12px);min-height:100dvh;overflow-x:hidden}}
  ::-webkit-scrollbar{{width:3px}}
  ::-webkit-scrollbar-track{{background:#0a0e17}}
  ::-webkit-scrollbar-thumb{{background:#262d3d;border-radius:2px}}
  .header{{background:#111827;border-bottom:1px solid #262d3d;padding:12px 16px 10px;position:sticky;top:0;z-index:50;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}}
  .header-top{{display:flex;align-items:center;justify-content:space-between}}
  .logo{{display:flex;align-items:center;gap:10px}}
  .logo-icon{{width:34px;height:34px;background:linear-gradient(135deg,#f472b6,#a78bfa);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}}
  .logo-text{{font-size:1.15rem;font-weight:700;letter-spacing:-0.3px}}
  .logo-text span{{background:linear-gradient(135deg,#f472b6,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .logo-sub{{font-size:0.6rem;color:#5a6070;letter-spacing:1.5px;text-transform:uppercase}}
  .header-date{{font-size:0.7rem;color:#5a6070;text-align:right}}
  .header-date strong{{color:#9298a8;font-weight:500}}
  .disc{{margin:12px 16px 0;padding:10px 14px;background:rgba(248,113,113,0.06);border:1px solid rgba(248,113,113,0.15);border-radius:8px;font-size:0.7rem;color:#5a6070;line-height:1.5}}
  .disc strong{{color:#f87171;font-weight:600}}
  .ticker-wrap{{margin:0 16px;overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory;display:flex;gap:10px;padding:14px 0 10px;scrollbar-width:none}}
  .ticker-wrap::-webkit-scrollbar{{display:none}}
  .ticker-card{{flex:0 0 calc(50% - 5px);scroll-snap-align:start;background:#1a1f2e;border:1px solid #262d3d;border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;min-width:0}}
  .ticker-card::before{{content:'';position:absolute;top:0;left:0;width:100%;height:2.5px}}
  .tc:nth-child(1)::before{{background:linear-gradient(90deg,#4f8cff,#22d3ee)}}
  .tc:nth-child(2)::before{{background:linear-gradient(90deg,#34d399,#22d3ee)}}
  .tc:nth-child(3)::before{{background:linear-gradient(90deg,#fbbf24,#fb923c)}}
  .tc:nth-child(4)::before{{background:linear-gradient(90deg,#f472b6,#a78bfa)}}
  .tc:nth-child(5)::before{{background:linear-gradient(90deg,#fb923c,#f87171)}}
  .tc:nth-child(6)::before{{background:linear-gradient(90deg,#a78bfa,#f472b6)}}
  .tc:nth-child(7)::before{{background:linear-gradient(90deg,#22d3ee,#34d399)}}
  .tc:nth-child(8)::before{{background:linear-gradient(90deg,#a3e635,#fbbf24)}}
  .tc:nth-child(9)::before{{background:linear-gradient(90deg,#f87171,#fb923c)}}
  .tc-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
  .tc-symbol{{font-size:1rem;font-weight:700;letter-spacing:-0.3px}}
  .tc-name{{font-size:0.6rem;color:#5a6070}}
  .tc-price{{font-size:1.35rem;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-0.5px}}
  .tc-chg{{display:inline-flex;align-items:center;gap:3px;font-size:0.72rem;font-weight:600;font-family:'JetBrains Mono',monospace;padding:2px 8px;border-radius:5px;margin-top:4px}}
  .tc-chg.up{{color:#34d399;background:rgba(52,211,153,0.1)}}
  .tc-chg.down{{color:#f87171;background:rgba(248,113,113,0.1)}}
  .tc-chg.flat{{color:#9298a8;background:rgba(146,152,168,0.05)}}
  .section{{margin:0 16px 18px}}
  .sec-title{{display:flex;align-items:center;gap:8px;font-size:0.95rem;font-weight:600;margin-bottom:12px;padding-top:6px}}
  .sec-title .dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
  .sec-title .dot.n{{background:#4f8cff}}
  .sec-title .dot.a{{background:#34d399}}
  .sec-title .dot.p{{background:#fbbf24}}
  .stock-tabs{{display:flex;gap:3px;background:#111827;border-radius:8px;padding:3px;margin-bottom:12px;overflow-x:auto;scrollbar-width:none}}
  .stock-tabs::-webkit-scrollbar{{display:none}}
  .stock-tab{{flex-shrink:0;padding:7px 12px;border-radius:6px;font-size:0.72rem;font-weight:600;color:#5a6070;cursor:pointer;border:none;background:none;font-family:inherit;white-space:nowrap}}
  .stock-tab:active{{transform:scale(0.96)}}
  .stock-tab.active{{color:#fff;background:rgba(255,255,255,0.08)}}
  .news-box{{display:none}}
  .news-box.active{{display:block}}
  .news-item{{background:#1a1f2e;border:1px solid #262d3d;border-radius:10px;padding:14px 16px;margin-bottom:10px}}
  .ni-tag{{display:inline-block;font-size:0.6rem;font-weight:600;letter-spacing:0.3px;text-transform:uppercase;padding:2px 7px;border-radius:4px;margin-bottom:6px}}
  .ni-tag.hot{{background:rgba(251,191,36,0.15);color:#fbbf24}}
  .ni-tag.er{{background:rgba(79,140,255,0.15);color:#4f8cff}}
  .ni-tag.pr{{background:rgba(52,211,153,0.15);color:#34d399}}
  .ni-tag.rk{{background:rgba(248,113,113,0.15);color:#f87171}}
  .ni-tag.an{{background:rgba(167,139,250,0.15);color:#a78bfa}}
  .ni-tag.ai{{background:rgba(34,211,238,0.15);color:#22d3ee}}
  .ni-tag.bb{{background:rgba(251,146,60,0.15);color:#fb923c}}
  .news-item h4{{font-size:0.88rem;font-weight:600;line-height:1.4;margin-bottom:5px}}
  .news-item p{{font-size:0.75rem;color:#9298a8;line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
  .ni-src{{margin-top:8px;font-size:0.65rem;color:#5a6070}}
  .advice-item{{background:#1a1f2e;border:1px solid #262d3d;border-radius:10px;padding:16px;margin-bottom:10px;position:relative;overflow:hidden}}
  .advice-item::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%}}
  .ai-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
  .ai-header h3{{font-size:0.95rem;font-weight:700}}
  .ai-rate{{font-size:0.65rem;font-weight:600;padding:3px 10px;border-radius:12px;flex-shrink:0}}
  .ai-rate.bull{{background:rgba(52,211,153,0.12);color:#34d399}}
  .ai-rate.caut{{background:rgba(248,113,113,0.12);color:#f87171}}
  .ai-rate.mix{{background:rgba(167,139,250,0.12);color:#a78bfa}}
  .ai-rate.wait{{background:rgba(251,191,36,0.12);color:#fbbf24}}
  .ai-body{{font-size:0.78rem;color:#9298a8;line-height:1.65}}
  .ai-body strong{{color:#f0f2f8}}
  .ai-body ul{{list-style:none;padding:0;margin-top:6px}}
  .ai-body ul li{{padding:3px 0 3px 16px;position:relative;font-size:0.75rem}}
  .ai-body ul li::before{{content:'';position:absolute;left:0;top:9px;width:5px;height:5px;border-radius:50%}}
  .ai-body ul li.g::before{{background:#34d399}}
  .ai-body ul li.r::before{{background:#f87171}}
  .ai-body ul li.y::before{{background:#fbbf24}}
  .ai-target{{margin-top:10px;padding-top:10px;border-top:1px solid #262d3d;font-size:0.7rem;color:#5a6070}}
  .ai-target strong{{color:#9298a8}}
  .pf-card{{background:#1a1f2e;border:1px solid #262d3d;border-radius:10px;padding:16px;margin-bottom:10px}}
  .pf-card h3{{font-size:0.9rem;font-weight:600;margin-bottom:10px}}
  .pf-table{{width:100%;border-collapse:collapse}}
  .pf-table th,.pf-table td{{padding:6px 5px;text-align:left;font-size:0.68rem;border-bottom:1px solid #262d3d}}
  .pf-table th{{color:#5a6070;font-weight:500;font-size:0.6rem;text-transform:uppercase;letter-spacing:0.3px}}
  .pf-table td{{color:#9298a8;font-family:'JetBrains Mono',monospace;font-size:0.68rem}}
  .pf-table td:first-child{{font-family:'Inter',sans-serif;font-weight:600;color:#f0f2f8}}
  .pf-table .vg{{color:#34d399}}
  .pf-table .vr{{color:#f87171}}
  .pf-table tr:last-child td{{border-bottom:none}}
  .pf-score{{text-align:center;padding:20px 16px;display:flex;flex-direction:column;align-items:center;gap:6px}}
  .pf-num{{font-size:2.2rem;font-weight:800;font-family:'JetBrains Mono',monospace;letter-spacing:-1px;background:linear-gradient(135deg,#f472b6,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .pf-label{{font-size:0.75rem;color:#9298a8}}
  .pf-desc{{font-size:0.7rem;color:#5a6070;line-height:1.6;max-width:320px}}
  .pf-desc strong{{color:#9298a8}}
  .cat-badge{{display:inline-block;font-size:0.55rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:6px}}
  .cat-badge.tech{{background:rgba(79,140,255,0.15);color:#4f8cff}}
  .cat-badge.resource{{background:rgba(251,191,36,0.15);color:#fbbf24}}
  .cat-badge.energy{{background:rgba(251,146,60,0.15);color:#fb923c}}
  .cat-badge.chem{{background:rgba(167,139,250,0.15);color:#a78bfa}}
  .bottom-nav{{position:fixed;bottom:0;left:0;right:0;height:calc(64px+env(safe-area-inset-bottom,0px));padding-bottom:env(safe-area-inset-bottom,0px);background:rgba(17,24,39,0.92);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-top:1px solid #262d3d;display:flex;z-index:100}}
  .bn-item{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;height:100%;border:none;background:none;font-family:inherit;cursor:pointer;color:#5a6070;padding:0 4px}}
  .bn-item.active{{color:#a78bfa}}
  .bn-item .bn-icon{{font-size:1.2rem}}
  .bn-item .bn-label{{font-size:0.6rem;font-weight:500;letter-spacing:0.2px}}
  .page{{display:none}}.page.active{{display:block}}
  .scroll-hint{{text-align:center;font-size:0.6rem;color:#5a6070;padding:2px 0 6px;letter-spacing:1px}}
  .page-foot{{text-align:center;padding:20px 16px 12px;font-size:0.65rem;color:#5a6070;line-height:1.7}}
  .page-foot a{{color:#a78bfa;text-decoration:none}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
  .ticker-card,.news-item,.advice-item,.pf-card{{animation:fadeUp 0.4s ease forwards}}
</style>
</head>
<body>

<header class="header">
  <div class="header-top">
    <div class="logo">
      <div class="logo-icon">F</div>
      <div><div class="logo-text"><span>Freya's</span> Stock</div><div class="logo-sub">A股投资跟踪</div></div>
    </div>
    <div class="header-date" id="headerDate"></div>
  </div>
</header>

<div class="disc"><strong>⚠ 声明：</strong>仅供参考不构成投资建议。数据来源：东方财富 · {today}</div>

<div class="page active" id="page-prices">
  <div class="ticker-wrap" id="tickerWrap">{tickers}</div>
  <div class="scroll-hint">← 左右滑动查看全部 9 只 →</div>
  <div class="section">
    <div class="sec-title"><span class="dot n"></span>个股最新资讯</div>
    <div class="stock-tabs" id="stockTabs">{tabs}</div>
    {news_boxes}
  </div>
</div>

<div class="page" id="page-advice">
  <div class="section" style="margin-top:14px;">
    <div class="sec-title"><span class="dot a"></span>操作建议</div>
    {advice}
  </div>
</div>

<div class="page" id="page-portfolio">
  <div class="section" style="margin-top:14px;">
    <div class="sec-title"><span class="dot p"></span>组合总览</div>
    <div class="pf-card">
      <h3>📊 持仓速览</h3>
      <div style="overflow-x:auto">
      <table class="pf-table">
        <thead><tr><th>股票</th><th>代码</th><th>价格</th><th>涨跌</th><th>分类</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      </div>
    </div>
    <div class="pf-card pf-score">
      <div class="pf-num">7.5 / 10</div>
      <div class="pf-label">组合健康评分</div>
      <div class="pf-desc">
        <strong>配置：</strong>科技制造4只 | 资源矿业2只 | 能源2只 | 多元1只<br>
        <strong>今日：</strong>{up}涨 {down}跌<br>
        <strong>策略：</strong>科技制造为核心仓位，资源类逢回调布局
      </div>
    </div>
    <div class="pf-card">
      <h3>📌 {today}</h3>
      <div class="ai-body" style="font-size:0.78rem;color:#9298a8;line-height:1.7;">
        <p>今日 {up} 涨 {down} 跌。数据来源：东方财富实时行情。</p>
        <p style="margin-top:8px;">建议保持核心科技仓位，资源类逢低布局，保持组合平衡。</p>
      </div>
    </div>
  </div>
</div>

<nav class="bottom-nav">
  <button class="bn-item active" data-page="prices"><span class="bn-icon">📊</span><span class="bn-label">行情</span></button>
  <button class="bn-item" data-page="advice"><span class="bn-icon">💡</span><span class="bn-label">建议</span></button>
  <button class="bn-item" data-page="portfolio"><span class="bn-icon">📋</span><span class="bn-label">组合</span></button>
</nav>

<div class="page-foot">Freya's Stock · 东方财富数据 · {today}</div>

<script>
document.getElementById('headerDate').innerHTML='<strong>'+new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric'})+'</strong> · '+new Date().toLocaleDateString('zh-CN',{weekday:'short'});
const st=document.querySelectorAll('.stock-tab'),sb=document.querySelectorAll('.news-box');
st.forEach(t=>t.addEventListener('click',()=>{st.forEach(x=>x.classList.remove('active'));t.classList.add('active');sb.forEach(b=>b.classList.remove('active'));document.getElementById('n-'+t.dataset.s).classList.add('active')}));
const ni=document.querySelectorAll('.bn-item'),pg=document.querySelectorAll('.page');
ni.forEach(i=>i.addEventListener('click',()=>{ni.forEach(x=>x.classList.remove('active'));i.classList.add('active');pg.forEach(p=>p.classList.remove('active'));document.getElementById('page-'+i.dataset.page).classList.add('active');window.scrollTo({top:0,behavior:'smooth'})}));
document.getElementById('tickerWrap')?.addEventListener('scroll',()=>{document.querySelector('.scroll-hint').style.opacity='0'});
</script>
</body>
</html>'''


# ============================================================
# 主函数
# ============================================================
def main():
    print(f"{'='*50}")
    print(f"  Freya's Stock 自动更新 v2.0")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    today = datetime.now().strftime("%Y年%m月%d日")

    # 1. 获取实时行情
    print("\n📡 获取实时行情...")
    prices = fetch_prices()
    print(f"   获得 {len(prices)} 只股票行情")

    # 2. 获取新闻
    print("\n📰 获取个股新闻...")
    news = fetch_news_batch()

    # 统计成功数
    success = sum(1 for s in STOCKS if s["code"] in prices and prices[s["code"]].get("price"))
    news_count = sum(len(v) for v in news.values())
    print(f"\n   ✅ 行情: {success}/{len(STOCKS)} 只")
    print(f"   ✅ 新闻: {news_count} 条")

    # 3. 生成 HTML
    print("\n📄 生成HTML...")
    html = gen_html(prices, news, today)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(OUTPUT_FILE)
    print(f"   ✅ {OUTPUT_FILE} ({size:,} bytes)")

    # 4. 摘要
    up = sum(1 for s in STOCKS if prices.get(s["code"], {}).get("change_pct", 0) >= 0)
    down = len(STOCKS) - up
    print(f"\n📊 今日小结: {up}涨 {down}跌")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
