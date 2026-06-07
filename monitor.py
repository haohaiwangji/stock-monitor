import feedparser
import requests
import json
import os
import hashlib
import urllib.parse
from datetime import datetime, timezone, timedelta

SERVERCHAN_KEYS = [k for k in [
    os.environ.get("SERVERCHAN_KEY", ""),
    os.environ.get("SERVERCHAN_KEY2", ""),
] if k]
CST = timezone(timedelta(hours=8))
STATE_FILE = "state.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

RSSHUB_INSTANCES = [
    "rsshub.app",
    "hub.slarker.me",
    "rsshub.rssforever.com",
    "rss.shab.fun",
    "rsshub.feeded.xyz",
]

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
    "nitter.cz",
    "notabird.site",
    "xcancel.com",
    "nitter.woodland.cafe",
    "nitter.sethforprivacy.com",
    "nitter.net",
    "nitter.fdn.fr",
]

TWITTER_ACCOUNTS = {
    "serenity": {"handle": "aleabitoreddit", "display": "Serenity",           "filter": None},
    "musk":     {"handle": "elonmusk",        "display": "马斯克 Elon Musk",   "filter": "china"},
    "jensen":   {"handle": "jensenhwang",     "display": "黄仁勋 Jensen Huang", "filter": "china"},
}

CHINA_KEYWORDS = [
    "china", "chinese", "beijing", "shanghai", "中国", "台湾", "taiwan",
    "huawei", "华为", "sanction", "制裁", "chip", "semiconductor", "芯片",
    "export control", "ccp", "prc", "smic", "yangtze",
]

BREAKING_KEYWORDS = {
    "🌍 全球政治": [
        "war", "military strike", "invasion", "coup", "ceasefire", "nuclear",
        "emergency declared", "assassination", "missile attack", "explosion",
        "战争", "军事打击", "入侵", "政变", "核武", "暗杀", "停火", "紧急状态",
    ],
    "🏦 央行政策": [
        "federal reserve", "fed rate", "fomc", "rate cut", "rate hike",
        "central bank", "jerome powell", "inflation report", "cpi data",
        "美联储", "加息", "降息", "货币政策", "通胀", "CPI", "央行", "鲍威尔",
        "ecb rate", "bank of england", "pboc",
    ],
    "💹 金融市场": [
        "market crash", "stock market plunge", "circuit breaker", "bank collapse",
        "financial crisis", "recession fears", "bankruptcy", "debt default",
        "市场崩溃", "暴跌", "暴涨", "熔断", "金融危机", "银行倒闭", "债务违约",
        "stocks fall", "stocks surge", "wall street",
    ],
    "📈 A股/美股": [
        "s&p 500", "nasdaq", "dow jones", "china stocks", "hang seng",
        "上证", "深证", "A股", "港股", "美股", "跌停", "涨停",
        "stock market today", "markets open", "markets close",
    ],
    "🇺🇸 特朗普": [
        "trump tariff", "trump signs", "trump announces", "trump threatens",
        "white house announces", "executive order", "trade war",
        "特朗普", "关税", "贸易战", "白宫宣布",
    ],
    "🚀 马斯克/Tesla": [
        "elon musk", "tesla earnings", "tesla stock", "spacex", "musk says",
        "musk warns", "doge department", "马斯克", "特斯拉财报", "特斯拉股价",
    ],
    "🤖 黄仁勋/NVIDIA": [
        "jensen huang", "nvidia earnings", "nvidia revenue", "nvidia chip",
        "blackwell", "h100", "h200", "gb200", "nvidia stock",
        "黄仁勋", "英伟达财报", "英伟达",
    ],
    "🇨🇳 中国要闻": [
        "china gdp", "china economy", "pboc rate", "china policy", "beijing announces",
        "china trade", "china sanctions", "china taiwan", "china us",
        "中国经济", "人民银行", "中美", "两岸", "政策出台", "国务院",
    ],
    "🇯🇵 日本": [
        "bank of japan", "boj rate", "nikkei", "japan economy", "yen falls", "yen rises",
        "japan gdp", "japan inflation", "kishida", "日本央行", "日元", "日经", "日本经济",
    ],
    "🇰🇷 韩国": [
        "korea gdp", "kospi", "samsung earnings", "bank of korea", "sk hynix",
        "korea economy", "韩国经济", "韩元", "三星财报", "韩国央行",
    ],
    "🌍 地缘政治": [
        "iran nuclear", "israel gaza", "russia ukraine", "north korea", "south china sea",
        "oil price surge", "oil price crash", "opec", "nato", "g7", "g20",
        "伊朗", "以色列", "俄乌", "朝鲜", "南海", "油价", "欧佩克",
    ],
}

BREAKING_RSS = [
    # 英文全球
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.dw.com/rdf/rss-en-all",                  # 德国之声
    "https://www.france24.com/en/rss",                     # 法国24
    # 日本
    "https://www3.nhk.or.jp/nhkworld/en/news/feeds/news.xml",  # NHK World 英文
    "https://news.google.com/rss/search?q=bank+of+japan+OR+nikkei+OR+japan+economy+OR+boj+rate&hl=en-US&gl=US&ceid=US:en",
    # 韩国
    "https://en.yna.co.kr/RSS/news.xml",                   # 韩联社英文
    "https://news.google.com/rss/search?q=kospi+OR+bank+of+korea+OR+samsung+earnings+OR+korea+economy&hl=en-US&gl=US&ceid=US:en",
    # 中文
    "http://feed.eastmoney.com/news/cjxw.xml",
    "https://www.cls.cn/nodeapi/updateTelegraph",
    "https://news.google.com/rss/search?q=%E8%B4%A2%E8%81%94%E7%A4%BE&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://news.google.com/rss/search?q=%E6%97%A5%E6%9C%AC%E7%BB%8F%E6%B5%8E+OR+%E6%97%A5%E5%85%83+OR+%E9%9F%A9%E5%9B%BD%E7%BB%8F%E6%B5%8E+OR+%E4%B8%89%E6%98%9F&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    # 英文综合关键词搜索
    "https://news.google.com/rss/search?q=trump+OR+federal+reserve+OR+war+OR+nuclear&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=nvidia+OR+tesla+OR+stock+market+crash+OR+rate+cut&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%E7%BE%8E%E8%81%94%E5%82%A8+OR+%E7%89%B9%E6%9C%97%E6%99%AE+OR+%E4%B8%AD%E5%9B%BD%E7%BB%8F%E6%B5%8E+OR+A%E8%82%A1&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://news.google.com/rss/search?q=%E8%82%A1%E5%B8%82+OR+%E6%9A%B4%E8%B7%8C+OR+%E9%87%91%E8%9E%8D%E5%8D%B1%E6%9C%BA+OR+%E5%85%B3%E7%A8%8E&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
]

MARKET_RSS = [
    ("🌍 BBC 国际",   "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("🌍 半岛电视台",  "https://www.aljazeera.com/xml/rss/all.xml"),
    ("🌍 德国之声",    "https://rss.dw.com/rdf/rss-en-business"),
    ("⚡ 财联社",     "https://news.google.com/rss/search?q=%E8%B4%A2%E8%81%94%E7%A4%BE&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("📈 A股资讯",    "http://feed.eastmoney.com/news/cjxw.xml"),
    ("🇺🇸 美股财经",  "https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1+%E7%BA%B3%E6%96%AF%E8%BE%BE%E5%85%8B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("🇯🇵 日本财经",  "https://www3.nhk.or.jp/nhkworld/en/news/feeds/news.xml"),
    ("🇰🇷 韩国财经",  "https://en.yna.co.kr/RSS/news.xml"),
    ("💰 财经快讯",    "https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F+%E8%82%A1%E5%B8%82&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]

INDICES = [
    ("道琼斯",   "%5EDJI"),
    ("纳斯达克",  "%5EIXIC"),
    ("标普500",  "%5EGSPC"),
    ("上证指数",  "000001.SS"),
    ("深证成指",  "399001.SZ"),
    ("日经225",  "%5EN225"),
    ("韩国KOSPI", "%5EKS11"),
]


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_ids": {}, "seen_news": [], "last_market_block": -1}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def translate(text):
    if not text:
        return ""
    try:
        encoded = urllib.parse.quote(text[:300])
        url = (f"https://translate.googleapis.com/translate_a/single"
               f"?client=gtx&sl=auto&tl=zh-CN&dt=t&q={encoded}")
        resp = requests.get(url, headers=HEADERS, timeout=8)
        parts = resp.json()[0]
        return "".join(p[0] for p in parts if p[0])
    except Exception:
        return ""


def is_china_related(text):
    return any(kw in text.lower() for kw in CHINA_KEYWORDS)


def trading_signal(title):
    """Keyword-based: list mentioned assets/sectors and market-relevant topics, no sentiment."""
    t = title.lower()

    STOCK_MAP = {
        "nvidia": "英伟达(NVDA)", "nvda": "英伟达(NVDA)",
        "tsla": "特斯拉(TSLA)", "tesla": "特斯拉(TSLA)",
        "apple": "苹果(AAPL)", "aapl": "苹果(AAPL)",
        "microsoft": "微软(MSFT)", "msft": "微软(MSFT)",
        "google": "谷歌(GOOGL)", "alphabet": "谷歌(GOOGL)",
        "amazon": "亚马逊(AMZN)", "amzn": "亚马逊(AMZN)",
        "meta": "Meta(META)",
        "semiconductor": "半导体板块", "chip ban": "芯片出口管制",
        "chip": "芯片概念",
        "artificial intelligence": "AI概念",
        "federal reserve": "美联储政策", "fomc": "美联储政策",
        "rate cut": "降息相关", "rate hike": "加息相关", "interest rate": "利率政策",
        "tariff": "关税政策", "trade war": "贸易摩擦",
        "china": "中国/中概股", "huawei": "华为/芯片",
        "smic": "中芯国际", "export control": "出口管制",
        "oil price": "油价/石油板块", "opec": "石油板块",
        "nasdaq": "纳斯达克", "s&p 500": "标普500",
        "nikkei": "日经225", "kospi": "韩国股市",
        "a股": "A股市场", "上证": "A股市场", "港股": "港股市场",
        "earnings": "财报季", "ipo": "IPO",
        "recession": "衰退风险", "inflation": "通胀数据", "cpi": "CPI数据",
        "bank of japan": "日本央行政策", "boj": "日本央行政策",
    }

    found = list(dict.fromkeys(v for k, v in STOCK_MAP.items() if k in t))
    if not found:
        return "无直接股市影响"
    return "涉及：" + "、".join(found[:4])


def push(title, content):
    ok_all = True
    for key in SERVERCHAN_KEYS:
        try:
            resp = requests.post(
                f"https://sctapi.ftqq.com/{key}.send",
                data={"title": title, "desp": content},
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                ok_all = False
        except Exception:
            ok_all = False
    print(f"  推送{'成功' if ok_all else '部分失败'} ({len(SERVERCHAN_KEYS)}个微信): {title[:50]}")
    return ok_all


def url_hash(s):
    return hashlib.md5(s.encode()).hexdigest()[:12]


def fetch_twitter_rss(handle):
    # 先试 RSSHub（更稳定）
    for instance in RSSHUB_INSTANCES:
        try:
            url = f"https://{instance}/twitter/user/{handle}"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200 and len(resp.content) > 200:
                feed = feedparser.parse(resp.content)
                if feed.entries:
                    print(f"  RSSHub OK: {instance}")
                    return feed.entries
        except Exception:
            continue

    # RSSHub 全失败，fallback 到 Nitter
    for instance in NITTER_INSTANCES:
        try:
            url = f"https://{instance}/{handle}/rss"
            resp = requests.get(url, headers=HEADERS, timeout=6)
            if resp.status_code == 200 and len(resp.content) > 200:
                feed = feedparser.parse(resp.content)
                if feed.entries:
                    print(f"  Nitter OK: {instance}")
                    return feed.entries
        except Exception:
            continue

    return []


# ── 推特监控 ─────────────────────────────────────────

def check_twitter(state):
    now_str = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    last_ids = state.setdefault("last_ids", {})

    for key, acct in TWITTER_ACCOUNTS.items():
        handle = acct["handle"]
        display = acct["display"]
        china_only = acct["filter"] == "china"

        print(f"检查 @{handle} ...")
        entries = fetch_twitter_rss(handle)
        if not entries:
            print(f"  {display}: 所有 Nitter 实例不可用，跳过")
            continue

        latest_id = entries[0].get("id", entries[0].get("link", ""))
        last_id = last_ids.get(key, "")

        new_entries = []
        for entry in entries:
            eid = entry.get("id", entry.get("link", ""))
            if eid == last_id:
                break
            new_entries.append(entry)

        if not new_entries:
            print(f"  {display}: 无新推文")
        else:
            for entry in reversed(new_entries):
                title = entry.get("title", "").strip()[:300]
                if not title:
                    continue
                if china_only and not is_china_related(title):
                    print(f"  {display}: 跳过非涉华内容")
                    continue

                # 推文发送时间（北京时间）
                pub = entry.get("published_parsed")
                if pub:
                    tweet_time = datetime(*pub[:6], tzinfo=timezone.utc).astimezone(CST).strftime("%m-%d %H:%M")
                else:
                    tweet_time = now_str

                zh = translate(title)
                signal = trading_signal(title + " " + (zh or ""))
                body = f"**🐦 {display}**\n\n🕒 发推时间：{tweet_time}（北京时间）\n\n📝 **中文翻译：**\n{zh if zh and zh != title else title}\n\n💡 **交易信号解读：** {signal}"
                if zh and zh != title:
                    body += f"\n\n---\n*原文：{title}*"

                tag = "🇨🇳 涉华 · " if china_only else ""
                push(f"⚡ {tag}{display} {tweet_time}", body)

        last_ids[key] = latest_id


# ── 突发新闻 ──────────────────────────────────────────

def check_breaking_news(state):
    now_str = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    seen = set(state.get("seen_news", []))
    new_seen = []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=12)

    # 按类别收集新内容，同一次运行合并推送
    collected = {}  # {category: [(title, link, zh, event_time), ...]}

    for feed_url in BREAKING_RSS:
        try:
            feed = feedparser.parse(feed_url)
            print(f"  突发RSS: {len(feed.entries)} 条 from {feed_url[:50]}")
            for entry in feed.entries[:30]:
                pub = entry.get("published_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    event_time = pub_dt.astimezone(CST).strftime("%m-%d %H:%M")
                else:
                    event_time = now_str
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                h = url_hash(link or title)
                if h in seen or h in new_seen:
                    continue
                title_lower = title.lower()
                for category, keywords in BREAKING_KEYWORDS.items():
                    if any(kw in title_lower for kw in keywords):
                        zh = translate(title)
                        collected.setdefault(category, []).append((title, link, zh, event_time))
                        new_seen.append(h)
                        break
        except Exception as e:
            print(f"  突发RSS失败: {e}")

    if not collected:
        print("  无新突发新闻")
        state["seen_news"] = (list(seen) + new_seen)[-300:]
        return

    # 同一次检查的所有突发新闻合并成一条，立即推送
    lines = [f"## 🔴 突发快讯 {now_str}\n"]
    for category, items in collected.items():
        lines.append(f"\n### 🔴 {category}")
        for title, link, zh, event_time in items:
            lines.append(f"\n🕐 {event_time}（北京时间）\n[{title}]({link})")
            if zh and zh != title:
                lines.append(f"> {zh}")

    push(f"🔴 突发快讯 {now_str}", "\n".join(lines))
    print(f"  合并推送 {len(collected)} 个类别，共 {sum(len(v) for v in collected.values())} 条")

    state["seen_news"] = (list(seen) + new_seen)[-300:]


# ── 市场播报（每30分钟）──────────────────────────────

MARKET_IMPACT_KEYWORDS = [
    "federal reserve", "fed rate", "fomc", "rate cut", "rate hike", "inflation", "cpi",
    "earnings", "gdp", "recession", "bank", "tariff", "trade war", "sanctions",
    "trump", "powell", "nvidia", "tesla", "apple", "microsoft",
    "oil price", "opec", "gold", "bitcoin", "crypto",
    "war", "crisis", "collapse", "default", "bankruptcy",
    "美联储", "加息", "降息", "通胀", "CPI", "财报", "GDP", "衰退",
    "关税", "贸易战", "制裁", "特朗普", "英伟达", "特斯拉",
    "战争", "危机", "违约", "破产", "暴跌", "暴涨", "熔断",
    "上证", "深证", "纳斯达克", "标普", "日经", "港股",
]


def has_market_impact(title):
    t = title.lower()
    return any(kw in t for kw in MARKET_IMPACT_KEYWORDS)


def get_market_data():
    lines = []
    for name, symbol in INDICES:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
                   f"{symbol}?interval=1d&range=5d")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            data = resp.json()["chart"]["result"][0]
            closes = data["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                curr = closes[-1]
                pct = (curr - closes[-2]) / closes[-2] * 100
                arrow = "📈" if pct > 0 else "📉"
                lines.append(f"- {arrow} **{name}**: {curr:,.2f}（{pct:+.2f}%）")
        except Exception as e:
            print(f"  行情失败 {name}: {e}")
    return "\n".join(lines)


def check_market_report(state):
    now = datetime.now(tz=CST)
    block = (now.hour * 60 + now.minute) // 30
    if block == state.get("last_market_block", -1):
        print("  市场播报：距上次不足30分钟，跳过")
        return
    state["last_market_block"] = block

    now_str = now.strftime("%H:%M")
    market = get_market_data()

    # 抓有市场影响的新闻，先试1小时内，再扩展到6小时
    news_items = []
    seen_titles = set()
    for hours in [1, 6, 24]:
        if len(news_items) >= 8:
            break
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        for label, url in MARKET_RSS:
            if len(news_items) >= 8:
                break
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:20]:
                    if len(news_items) >= 8:
                        break
                    pub = entry.get("published_parsed")
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                        event_time = pub_dt.astimezone(CST).strftime("%H:%M")
                    else:
                        event_time = now_str
                    title = entry.get("title", "").strip()
                    if not title or title in seen_titles:
                        continue
                    if not has_market_impact(title):
                        continue
                    seen_titles.add(title)
                    zh = translate(title)
                    display_text = zh if zh and zh != title else title
                    link = entry.get("link", "")
                    if link:
                        news_items.append(f"🕐 {event_time}（北京时间）\n[{display_text}]({link})\n")
                    else:
                        news_items.append(f"🕐 {event_time}（北京时间）\n{display_text}\n")
            except Exception:
                pass

    parts = [
        f"## 🌐 全球市场播报 {now_str}",
        "",
        "### 📊 【实时行情速递】",
        "",
        market or "暂无数据（休市或数据源限制）",
        "",
        "### 📰 【新闻汇总】",
        "",
    ]
    if news_items:
        parts.extend(news_items)
    else:
        parts.append("暂无对股市有实质性影响的新闻")

    push(f"🌐 市场播报 {now_str}", "\n".join(parts))


# ── 主入口 ───────────────────────────────────────────

def main():
    state = load_state()
    print("=== Twitter 监控 ===")
    check_twitter(state)
    print("=== 突发新闻监控 ===")
    check_breaking_news(state)
    print("=== 市场播报 ===")
    check_market_report(state)
    save_state(state)
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
