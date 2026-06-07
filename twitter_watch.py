import feedparser
import requests
import os
import urllib.parse
from datetime import datetime, timezone, timedelta

SERVERCHAN_KEY = os.environ["SERVERCHAN_KEY"]
CST = timezone(timedelta(hours=8))
TWITTER_USER = "aleabitoreddit"
LAST_ID_FILE = "last_tweet.txt"

NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def translate(text):
    if not text:
        return ""
    try:
        encoded = urllib.parse.quote(text[:300])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={encoded}"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        parts = resp.json()[0]
        return "".join(p[0] for p in parts if p[0])
    except Exception:
        return ""


def fetch_tweets():
    for instance in NITTER_INSTANCES:
        try:
            resp = requests.get(f"https://{instance}/{TWITTER_USER}/rss", headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                if feed.entries:
                    print(f"Nitter 成功: {instance}")
                    return feed.entries
        except Exception:
            continue
    return []


def read_last_id():
    try:
        with open(LAST_ID_FILE) as f:
            return f.read().strip()
    except Exception:
        return ""


def save_last_id(tweet_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(tweet_id)


def push_wechat(title, content):
    resp = requests.post(
        "https://sctapi.ftqq.com/" + SERVERCHAN_KEY + ".send",
        data={"title": title, "desp": content},
        timeout=10,
    )
    return resp.status_code == 200


def main():
    entries = fetch_tweets()
    if not entries:
        print("所有 Nitter 实例均不可用，跳过")
        return

    last_id = read_last_id()
    latest_id = entries[0].get("id", entries[0].get("link", ""))

    if latest_id == last_id:
        print("无新推文")
        return

    # 找出所有新推文
    new_entries = []
    for entry in entries:
        eid = entry.get("id", entry.get("link", ""))
        if eid == last_id:
            break
        new_entries.append(entry)

    print(f"发现 {len(new_entries)} 条新推文")

    for entry in reversed(new_entries):
        title = entry.get("title", "").strip()[:300]
        now = datetime.now(tz=CST).strftime("%m-%d %H:%M")
        translation = translate(title)

        content = "**🐦 Serenity (@aleabitoreddit)**\n\n"
        content += title
        if translation and translation != title:
            content += "\n\n> **中文：** " + translation

        ok = push_wechat("⚡ Serenity 新推文 " + now, content)
        print(("推送成功" if ok else "推送失败") + ": " + title[:60])

    save_last_id(latest_id)


if __name__ == "__main__":
    main()
