# Waterloo events calendar feed

Wygo (wygo.world) has no calendar subscribe option, and Luma splits things
across lots of separate calendars. This repo pulls both into iCal feeds you
can subscribe to once in Google Calendar.

A GitHub Action runs every 6 hours and publishes to GitHub Pages. It deploys
straight to Pages and never commits, so the repo stays quiet on your profile.

Setup: Settings → Pages → Source: **GitHub Actions**.

## Feeds
| Feed | What's in it |
|---|---|
| `https://isha-das-06.github.io/wygo-calendar/all.ics` | Everything, Wygo + Luma, duplicates removed |
| `https://isha-das-06.github.io/wygo-calendar/wygo.ics` | Wygo only |
| `https://isha-das-06.github.io/wygo-calendar/luma.ics` | Luma only |

Subscribe in Google Calendar: Other calendars → + → From URL.

## Adding sources
- **Wygo:** add the handle from `wygo.world/o/<handle>` to `organizers.txt`.
  For user pages (`wygo.world/u/<handle>`), write `u/<handle>`.
- **Luma:** paste the calendar's luma.com link (or the part after `luma.com/`)
  into `luma.txt`.

Commit the file and the Action runs straight away.

## How it works
- Wygo organizer page: takes the event links listed under "Upcoming Events",
  then reads the schema.org Event JSON-LD on each event page. Waits 2 seconds
  between requests and only checks upcoming events.
- Luma: downloads each calendar's official iCal feed (`api.lu.ma/ics/get`).
  Events on several calendars are kept once.
- `all.ics` skips a Luma event when Wygo has one with the same title and start time.
- Events stay on the calendar for 45 days after they end. `events.json`
  (published next to the feeds) remembers Wygo events between runs.
