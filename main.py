import feedparser
import requests
from datetime import datetime, timezone, timedelta
import os
import urllib.parse

SERVERCHAN_KEY = os.environ["SERVERCHAN_KEY"]
CST = timezone(timedelta(hours=8))

INDICES = [
    ("道琼斯", "%5EDJI"),
    ("纳斯达克", "%5EIXIC"),
    ("标普500", "%5EGSPC"),
    ("上证指数", "000001.SS"),
    ("深证成指", "399001.SZ"),
]

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
]

RSS_FEEDS = [
    ("🌍 全球时政", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("🌍 路透社", "https://feeds.reuters.com/reuters/topNews"),
    ("📈 A股资讯", "http://feed.eastmoney.com/news/cjxw.xml"),
    ("🇺🇸 美股新闻", "https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1+%E7%BA%B3%E6%96%AF%E8%BE%BE%E5%85%8B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("💰 财经快讯", "https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F+%E8%82%A1%E5%B8%82&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def is_english(text):
    english_chars = sum(1 for c in text if ord(c) < 128 and c.isalpha())
    return english_chars > len(text) * 0.5


def translate_to_chinese(text):
    if not text or not is_english(text):
        return ""
    try:
        encoded = urllib.parse.quote(text[:300])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={encoded}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        result = resp.json()
        translated = "".join(part[0] for part in result[0] if part[0])
        return translated
    except Exception:
        return ""


def get_market_data():
    lines = []
    for name, symbol in INDICES:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            data = resp.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                prev, curr = closes[-2], closes[-1]
                pct = (curr - prev) / prev * 100
                arrow = "📈" if pct > 0 else "📉"
                lines.append(arrow + " **" + name + "**: " + f"{pct:+.2f}%")
        except Exception as e:
            print(f"{name} 获取失败: {e}")
    return "\n".join(lines)


def get_twitter_feed(username):
    for instance in NITTER_INSTANCES:
        try:
            url = f"https://{instance}/{username}/rss"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                if feed.entries:
                    return feed.entries[:3], instance
        except Exception:
            continue
    return [], None


def format_entry(label, title, link=""):
    translation = translate_to_chinese(title)
    text = "\n" + label + "\n"
    if link:
        text += "[" + title + "](" + link + ")"
    else:
        text += title
    if translation and translation != title:
        text += "\n> " + translation
    return text


def get_news():
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=6)
    items = []

    # Twitter: @aleabitoreddit (Serenity)
    tweets, source = get_twitter_feed("aleabitoreddit")
    if tweets:
        for entry in tweets:
            pub = entry.get("published_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            title = entry.get("title", "").strip()
            if title:
                items.append(format_entry("🐦 Serenity (@aleabitoreddit)", title[:200]))
    else:
        print("Twitter feed unavailable (Nitter instances all failed)")

    # RSS feeds
    for label, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= 3:
                    break
                pub = entry.get("published_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                if title:
                    items.append(format_entry(label, title, link))
                    count += 1
        except Exception as e:
            print(f"{label} 获取失败: {e}")

    return items


def main():
    now = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    market = get_market_data()
    news = get_news()

    parts = ["## 市场播报 " + now]

    if market:
        parts.append("\n### 指数行情\n" + market)
    else:
        parts.append("\n### 指数行情\n暂无数据（休市或数据源限制）")

    if news:
        parts.append("\n### 最新资讯" + "".join(news))
    else:
        parts.append("\n### 最新资讯\n暂无近6小时新闻")

    content = "\n".join(parts)
    resp = requests.post(
        "https://sctapi.ftqq.com/" + SERVERCHAN_KEY + ".send",
        data={"title": "市场播报 " + now, "desp": content},
        timeout=10,
    )
    print("推送成功" if resp.status_code == 200 else "推送失败: " + str(resp.status_code))
    print("内容预览:\n" + content[:1000])


if __name__ == "__main__":
    main()
