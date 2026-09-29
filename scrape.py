"""Build an iCal feed from Wygo organizer pages.

Reads organizers.txt, grabs each organizer's upcoming events, pulls the
event details from the JSON-LD block on each event page, and writes
docs/wygo.ics. Events already seen are kept in docs/events.json so past
events stay on the calendar for a while after they happen.
"""

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event

BASE = "https://wygo.world"
ROOT = Path(__file__).parent
ORGS_FILE = ROOT / "organizers.txt"
OUT_DIR = ROOT / "docs"
ICS_FILE = OUT_DIR / "wygo.ics"
STATE_FILE = OUT_DIR / "events.json"
KEEP_PAST_DAYS = 45
DELAY_SECONDS = 2  # be polite between requests

session = requests.Session()
session.headers["User-Agent"] = "wygo-ical-feed/1.0 (personal calendar sync)"


def fetch(path):
    r = session.get(BASE + path, timeout=30)
    r.raise_for_status()
    time.sleep(DELAY_SECONDS)
    return r.text


def read_organizers():
    orgs = []
    for line in ORGS_FILE.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        # accept "socratica", "@socratica" or a full wygo.world/o/socratica URL
        line = line.rstrip("/").split("/o/")[-1].lstrip("@")
        orgs.append(line)
    return orgs


def upcoming_slugs(html):
    """Event links between the 'Upcoming Events' and 'Past Events' headings."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    body = str(soup.body or soup)
    start = body.find("Upcoming Events")
    if start == -1:
        return []
    end = body.find("Past Events", start)
    chunk = body[start:end if end != -1 else None]
    slugs = []
    for href in re.findall(r'href="([^"]+)"', chunk):
        href = href.replace(BASE, "")
        if re.fullmatch(r"/[A-Za-z0-9][A-Za-z0-9_\-]*", href) and href not in slugs:
            slugs.append(href)
    return slugs


def parse_event(html, slug):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Event":
                return event_from_ld(item, slug)
    return None


def event_from_ld(ld, slug):
    start = datetime.fromisoformat(ld["startDate"])
    end = datetime.fromisoformat(ld["endDate"]) if ld.get("endDate") else start + timedelta(hours=2)

    loc = ld.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address") or {}
    if isinstance(addr, dict):
        addr = ", ".join(
            addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion", "addressCountry") if addr.get(k)
        )
    location = ", ".join(p for p in (loc.get("name"), addr) if p)

    org = ld.get("organizer") or {}
    if isinstance(org, list):
        org = org[0] if org else {}

    url = ld.get("url") or BASE + slug
    return {
        "uid": f"wygo-{slug.strip('/')}@wygo-feed",
        "title": ld.get("name", slug.strip("/")),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "location": location,
        "description": (ld.get("description") or "").strip(),
        "organizer": org.get("name", ""),
        "url": url,
        "status": ld.get("eventStatus", ""),
    }


def build_ics(events):
    cal = Calendar()
    cal.add("prodid", "-//wygo-feed//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Wygo events")
    cal.add("x-wr-timezone", "America/Toronto")
    cal.add("refresh-interval;value=duration", "PT6H")
    now = datetime.now(timezone.utc)
    for e in sorted(events, key=lambda e: e["start"]):
        ev = Event()
        ev.add("uid", e["uid"])
        ev.add("dtstamp", now)
        ev.add("dtstart", datetime.fromisoformat(e["start"]).astimezone(timezone.utc))
        ev.add("dtend", datetime.fromisoformat(e["end"]).astimezone(timezone.utc))
        title = e["title"]
        if "Cancelled" in e.get("status", ""):
            title = "[CANCELLED] " + title
            ev.add("status", "CANCELLED")
        ev.add("summary", title)
        if e["location"]:
            ev.add("location", e["location"])
        desc = [d for d in (e["description"], f"Hosted by {e['organizer']}" if e["organizer"] else "", e["url"]) if d]
        ev.add("description", "\n\n".join(desc))
        ev.add("url", e["url"])
        cal.add_component(ev)
    return cal.to_ical()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    failures = 0

    for org in read_organizers():
        try:
            slugs = upcoming_slugs(fetch(f"/o/{org}"))
        except Exception as exc:
            print(f"[warn] couldn't load organizer {org}: {exc}")
            failures += 1
            continue
        print(f"{org}: {len(slugs)} upcoming")
        for slug in slugs:
            try:
                event = parse_event(fetch(slug), slug)
            except Exception as exc:
                print(f"  [warn] couldn't load {slug}: {exc}")
                failures += 1
                continue
            if event:
                state[event["uid"]] = event
                print(f"  + {event['start'][:16]}  {event['title']}")
            else:
                print(f"  [warn] no event data found on {slug}")

    # drop events that ended a while ago
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_PAST_DAYS)
    state = {k: v for k, v in state.items() if datetime.fromisoformat(v["end"]) > cutoff}

    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))
    ICS_FILE.write_bytes(build_ics(state.values()))
    print(f"wrote {len(state)} events to {ICS_FILE.relative_to(ROOT)}")
    return 1 if failures and not state else 0


if __name__ == "__main__":
    sys.exit(main())
