import feedparser
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta
import os

SERVERCHAN_KEY = os.environ["SERVERCHAN_KEY"]
CST = timezone(timedelta(hours=8))

INDICES = {
    "道琼斯": "^DJI",
    "纳斯达克": "^IXIC",
    "标普500": "^GSPC",
    "上证指数": "000001.SS",
    "深证成指": "399001.SZ",
}

RSS_FEEDS = [
    ("🌍 全球要闻", "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("📈 A股资讯", "http://feed.eastmoney.com/news/cjxw.xml"),
    ("🇺🇸 美股新闻", "https://news.google.com/rss/search?q=美股+纳斯达克+道琼斯&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("💰 财经快讯", "https://news.google.com/rss/search?q=财经+股市+经济&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
]

def get_market_data():
    lines = []
    for name, ticker in INDICES.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                curr = hist["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                arrow = "📈" if pct > 0 else "📉"
                lines.append(f"{arrow} **{name}**: {pct:+.2f}%")
        except:
            pass
    return "
".join(lines)

def get_news():
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    items = []
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
                    items.append(f"
{label}
[{title}]({link})")
                    count += 1
        except:
            pass
    return items

def main():
    now = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    market = get_market_data()
    news = get_news()

    if not market and not news:
        print("无新内容")
        return

    parts = [f"## 市场播报 {now}"]
    if market:
        parts.append(f"
### 指数行情
{market}")
    if news:
        parts.append("
### 最新资讯" + "".join(news))

    content = "
".join(parts)
    resp = requests.post(
        f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send",
        data={"title": f"市场播报 {now}", "desp": content},
        timeout=10
    )
    print(f"推送{chr(39)}成功{chr(39) if resp.status_code == 200 else chr(39)}失败{chr(39)}")

if __name__ == "__main__":
    main()
