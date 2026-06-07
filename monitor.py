import feedparser
import requests
import json
import os
import hashlib
import urllib.parse
from datetime import datetime, timezone, timedelta

SERVERCHAN_KEY = os.environ["SERVERCHAN_KEY"]
CST = timezone(timedelta(hours=8))
STATE_FILE = "state.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
    "nitter.cz",
    "notabird.site",
    "nitter.net",
    "nitter.it",
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
    "🏦 美联储": ["federal reserve", "fed rate", "fomc", "jerome powell",
                  "interest rate", "美联储", "加息", "降息", "鲍威尔"],
    "🇺🇸 特朗普": ["trump tariff", "trump signs", "white house", "executive order",
                   "特朗普", "关税", "贸易战", "trade war"],
    "🚀 马斯克": ["elon musk says", "musk warns", "tesla earnings", "tesla stock",
                  "spacex launch", "马斯克", "特斯拉"],
    "🤖 黄仁勋/NVIDIA": ["jensen huang", "nvidia earnings", "nvidia announces",
                         "blackwell", "h100", "h200", "黄仁勋", "英伟达"],
}

BREAKING_RSS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://news.google.com/rss/search?q=federal+reserve+OR+trump+tariff+OR+nvidia&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=elon+musk+OR+jensen+huang+OR+fomc&hl=en-US&gl=US&ceid=US:en",
]

MARKET_RSS = [
    ("🌍 BBC 国际",  "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("🌍 路透社",    "https://feeds.reuters.com/reuters/topNews"),
    ("📈 A股资讯",   "http://feed.eastmoney.com/news/cjxw.xml"),
    ("🇺🇸 美股",    "https://feeds.reuters.com/reuters/businessNews"),
    ("💰 财经",      "https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F+%E8%82%A1%E5%B8%82&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
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
    resp = requests.post(
        "https://sctapi.ftqq.com/" + SERVERCHAN_KEY + ".send",
        data={"title": title, "desp": content},
        timeout=10,
    )
    ok = resp.status_code == 200
    print(f"  推送{'成功' if ok else '失败'}: {title[:60]}")
    return ok


def url_hash(s):
    return hashlib.md5(s.encode()).hexdigest()[:12]


def fetch_nitter(handle):
    for instance in NITTER_INSTANCES:
        try:
            resp = requests.get(
                f"https://{instance}/{handle}/rss",
                headers=HEADERS, timeout=6
            )
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
        entries = fetch_nitter(handle)
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
                zh = translate(title)
                body = f"**🐦 {display}**\n\n{title}"
                if zh and zh != title:
                    body += f"\n\n> **中文：** {zh}"
                tag = "🇨🇳 涉华 · " if china_only else ""
                push(f"⚡ {tag}{display} 新推文 {now_str}", body)

        last_ids[key] = latest_id


# ── 突发新闻 ──────────────────────────────────────────

def check_breaking_news(state):
    now_str = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    seen = set(state.get("seen_news", []))
    new_seen = []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=12)

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
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                h = url_hash(link or title)
                if h in seen or h in new_seen:
                    continue
                title_lower = title.lower()
                for category, keywords in BREAKING_KEYWORDS.items():
                    if any(kw in title_lower for kw in keywords):
                        zh = translate(title)
                        body = f"**{category} 突发快讯**\n\n[{title}]({link})"
                        if zh and zh != title:
                            body += f"\n\n> **中文：** {zh}"
                        push(f"🔴 突发 · {category} {now_str}", body)
                        new_seen.append(h)
                        break
        except Exception as e:
            print(f"  突发RSS失败: {e}")

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
                    zh = translate(title)
                    item = f"\n{label}\n[{title}]({link})"
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
