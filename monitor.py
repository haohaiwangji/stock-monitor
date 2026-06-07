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
}

BREAKING_RSS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feed.eastmoney.com/news/cjxw.xml",
    "https://www.cls.cn/nodeapi/updateTelegraph",
    "https://news.google.com/rss/search?q=%E8%B4%A2%E8%81%94%E7%A4%BE&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://news.google.com/rss/search?q=trump+OR+federal+reserve+OR+war+OR+nuclear&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=nvidia+OR+tesla+OR+stock+market+crash+OR+rate+cut&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%E7%BE%8E%E8%81%94%E5%82%A8+OR+%E7%89%B9%E6%9C%97%E6%99%AE+OR+%E4%B8%AD%E5%9B%BD%E7%BB%8F%E6%B5%8E+OR+A%E8%82%A1&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "https://news.google.com/rss/search?q=%E8%82%A1%E5%B8%82+OR+%E6%9A%B4%E8%B7%8C+OR+%E9%87%91%E8%9E%8D%E5%8D%B1%E6%9C%BA+OR+%E5%85%B3%E7%A8%8E&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
]

MARKET_RSS = [
    ("🌍 BBC 国际",   "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("🌍 半岛电视台",  "https://www.aljazeera.com/xml/rss/all.xml"),
    ("⚡ 财联社",     "https://news.google.com/rss/search?q=%E8%B4%A2%E8%81%94%E7%A4%BE&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("📈 A股资讯",    "http://feed.eastmoney.com/news/cjxw.xml"),
    ("🇺🇸 美股财经",  "https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1+%E7%BA%B3%E6%96%AF%E8%BE%BE%E5%85%8B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("💰 财经快讯",    "https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F+%E8%82%A1%E5%B8%82&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]

INDICES = [
    ("道琼斯",   "%5EDJI"),
    ("纳斯达克",  "%5EIXIC"),
    ("标普500",  "%5EGSPC"),
    ("上证指数",  "000001.SS"),
    ("深证成指",  "399001.SZ"),
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
                body = f"**🐦 {display}**\n\n🕐 发推时间：{tweet_time}（北京时间）\n\n{title}"
                if zh and zh != title:
                    body += f"\n\n> **中文：** {zh}"

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

def get_market_data():
    lines = []
    for name, symbol in INDICES:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
                   f"{symbol}?interval=1d&range=5d")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                arrow = "📈" if pct > 0 else "📉"
                lines.append(f"{arrow} **{name}**: {pct:+.2f}%")
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

    now_str = now.strftime("%m-%d %H:%M")
    market = get_market_data()

    # 抓新闻，先试6小时内，没有则取24小时内最新5条
    news_items = []
    for hours in [6, 24]:
        if news_items:
            break
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        for label, url in MARKET_RSS:
            if len(news_items) >= 8:
                break
            try:
                feed = feedparser.parse(url)
                count = 0
                for entry in feed.entries:
                    if count >= 2:
                        break
                    pub = entry.get("published_parsed")
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "")
                    if not title:
                        continue
                    event_time = ""
                    if pub:
                        event_time = datetime(*pub[:6], tzinfo=timezone.utc).astimezone(CST).strftime("%m-%d %H:%M")
                    zh = translate(title)
                    item = f"\n{label}"
                    if event_time:
                        item += f" · 🕐 {event_time}"
                    item += f"\n[{title}]({link})"
                    if zh and zh != title:
                        item += f"\n> {zh}"
                    news_items.append(item)
                    count += 1
            except Exception:
                pass

    parts = [f"## 市场播报 {now_str}"]
    parts.append("\n### 指数行情\n" + (market or "暂无数据（休市）"))
    if news_items:
        parts.append("\n### 最新资讯" + "".join(news_items))
    else:
        parts.append("\n### 最新资讯\n暂无新内容")

    push(f"市场播报 {now_str}", "\n".join(parts))


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
