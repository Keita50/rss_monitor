
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time, csv, hashlib, re, html, pathlib, datetime
import requests, feedparser

BASE = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
COLLECT_DIR = DATA_DIR / "collected"
STATE_FILE = DATA_DIR / "seen_state.json"

def load_sources():
    with open(BASE/"sources.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen": {}}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_text(s):
    if not s: return ""
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def hash_key(*parts):
    import hashlib
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
    return h.hexdigest()[:16]

def match_keywords(text, keywords_any):
    if not keywords_any:
        return True
    text_l = text.lower()
    for kw in keywords_any:
        if kw.lower() in text_l:
            return True
    return False

def fetch_rss(feed):
    d = feedparser.parse(feed["url"])
    items = []
    for e in d.entries:
        title = normalize_text(getattr(e, "title", ""))
        summary = normalize_text(getattr(e, "summary", ""))
        link = getattr(e, "link", "")
        published = getattr(e, "published", "") or getattr(e, "updated", "")
        items.append({
            "title": title or "(no title)",
            "summary": summary,
            "link": link,
            "published": published,
        })
    return items

def fetch_page(feed):
    r = requests.get(feed["url"], timeout=30)
    r.raise_for_status()
    content = r.text
    title = feed["name"]
    return [{"title": title, "summary": normalize_text(content[:2000]), "link": feed["url"], "published": ""}]

def notify_slack(webhook, message):
    try:
        requests.post(webhook, json={"text": message}, timeout=10)
    except Exception as e:
        print(f"[WARN] Slack notify failed: {e}", file=sys.stderr)

def main():
    tz = os.environ.get("TZ", "Asia/Tokyo")
    os.environ["TZ"] = tz
    try:
        time.tzset()
    except Exception:
        pass

    cfg = load_sources()
    feeds = cfg.get("feeds", [])
    state = load_state()
    seen = state.setdefault("seen", {})

    COLLECT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_csv = COLLECT_DIR / f"collected_{ts}.csv"

    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    notify_lines = []

    rows = []
    for feed in feeds:
        fkey = feed["name"]
        fseen = seen.setdefault(fkey, {})
        try:
            if feed["type"] == "rss":
                items = fetch_rss(feed)
            elif feed["type"] == "page":
                items = fetch_page(feed)
            else:
                print(f"[WARN] Unknown feed type: {feed['type']} for {fkey}", file=sys.stderr)
                continue

            for it in items:
                text = f"{it['title']} {it['summary']}"
                if not match_keywords(text, feed.get("keywords_any", [])):
                    continue
                link = it.get("link") or ""
                key = hash_key(link, it.get("title",""))
                if not link:
                    key = hash_key(it.get("title",""), it.get("summary","")[:500])
                if key in fseen:
                    continue
                fseen[key] = ts
                row = {
                    "timestamp": ts,
                    "feed_name": fkey,
                    "category": feed.get("category",""),
                    "title": it.get("title",""),
                    "link": link,
                    "published": it.get("published",""),
                }
                rows.append(row)
                notify_lines.append(f"• [{row['category']}] {row['feed_name']}：{row['title']}\n  {row['link']}")
        except Exception as e:
            print(f"[ERROR] Fetch failed for {fkey}: {e}", file=sys.stderr)
            continue

    if rows:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            import csv
            w = csv.DictWriter(f, fieldnames=["timestamp","feed_name","category","title","link","published"])
            w.writeheader()
            w.writerows(rows)

        (DATA_DIR / "latest.csv").write_text(open(out_csv, "r", encoding="utf-8").read(), encoding="utf-8")

        if slack_webhook:
            header = f":satellite: RSS/Alerts Monitor ({ts} JST) — {len(rows)}件の新着"
            notify_slack(slack_webhook, header + "\n" + "\n".join(notify_lines[:45]))
    else:
        print("[INFO] No new items matched.")

    save_state(state)

if __name__ == "__main__":
    main()
