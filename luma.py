"""Pull events from Luma's own iCal feeds.

Luma already publishes an .ics for every public calendar, so nothing needs
scraping here. This just downloads each feed listed in luma.txt, drops old
events and merges them, keeping one copy of events that show up on more
than one calendar.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from icalendar import Calendar

ROOT = Path(__file__).parent
LUMA_FILE = ROOT / "luma.txt"
API = "https://api.lu.ma"

session = requests.Session()
session.headers["User-Agent"] = "wygo-ical-feed/1.0 (personal calendar sync)"


def read_sources():
    """Lines can be a luma.com link, a bare slug, a cal-... id or a discplace-... id."""
    sources = []
    for line in LUMA_FILE.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        line = re.sub(r"^https?://(www\.)?(luma\.com|lu\.ma)/", "", line).strip("/")
        line = line.removeprefix("calendar/")
        sources.append(line)
    return sources


def feed_url(source):
    if source.startswith("cal-"):
        return f"{API}/ics/get?entity=calendar&id={source}"
    if source.startswith("discplace-"):
        return f"{API}/ics/get?entity=discover&id={source}"
    # a page slug like "communitech" or "waterloo_ca": ask Luma what it is
    info = session.get(f"{API}/url", params={"url": source}, timeout=30).json()
    data = info.get("data") or {}
    if info.get("kind") == "calendar" and data.get("calendar"):
        return feed_url(data["calendar"]["api_id"])
    if info.get("kind") == "discover-place" and data.get("place"):
        return feed_url(data["place"]["api_id"])
    raise ValueError(f"'{source}' isn't a Luma calendar or city page (got {info.get('kind')})")


def as_utc(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # all-day events come through as dates
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def collect(keep_past_days):
    """Return {uid: VEVENT} for every event that hasn't been over for too long."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_past_days)
    events, failures = {}, 0
    for source in read_sources():
        try:
            url = feed_url(source)
            cal = Calendar.from_ical(session.get(url, timeout=30).content)
        except Exception as exc:
            print(f"[warn] luma {source}: {exc}")
            failures += 1
            continue
        name = str(cal.get("x-wr-calname", source))
        kept = 0
        for ev in cal.walk("VEVENT"):
            start = ev.get("dtstart")
            end = ev.get("dtend") or start
            if not start or as_utc(end.dt) < cutoff:
                continue
            uid = str(ev.get("uid"))
            if uid not in events:
                events[uid] = ev
                kept += 1
        print(f"luma {name}: {kept} new events")
    return events, failures


def title_key(title, start):
    """Loose match for the same event posted on Wygo and Luma."""
    words = re.sub(r"[^a-z0-9 ]", "", str(title).lower()).split()
    return " ".join(words), as_utc(start).strftime("%Y%m%d%H")
