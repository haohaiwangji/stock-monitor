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
    ("🇺🇸 美股新闻", "https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1+%E7%BA%B3%E6%96%AF%E8%BE%BE%E5%85%8B+%E9%81%93%E7%90%BC%E6%96%AF&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("💰 财经快讯", "https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F+%E8%82%A1%E5%B8%82+%E7%BB%8F%E6%B5%8E&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
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
                lines.append(arrow + " **" + name + "**: " + f"{pct:+.2f}%")
        except Exception:
            pass
    return "\n".join(lines)


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
                    items.append("\n" + label + "\n[" + title + "](" + link + ")")
                    count += 1
        except Exception:
            pass
    return items


def main():
    now = datetime.now(tz=CST).strftime("%m-%d %H:%M")
    market = get_market_data()
    news = get_news()

    if not market and not news:
        print("无新内容，跳过推送")
        return

    parts = ["## 市场播报 " + now]
    if market:
        parts.append("\n### 指数行情\n" + market)
    if news:
        parts.append("\n### 最新资讯" + "".join(news))

    content = "\n".join(parts)
    resp = requests.post(
        "https://sctapi.ftqq.com/" + SERVERCHAN_KEY + ".send",
        data={"title": "市场播报 " + now, "desp": content},
        timeout=10,
    )
    if resp.status_code == 200:
        print("推送成功")
    else:
        print("推送失败，状态码: " + str(resp.status_code))


if __name__ == "__main__":
    main()
