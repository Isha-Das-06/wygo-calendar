# Wygo calendar feed

Wygo (wygo.world) has no calendar subscribe option, so this repo builds one.
A GitHub Action runs every 6 hours, reads the upcoming events for each
organizer in `organizers.txt`, and writes `docs/wygo.ics`. GitHub Pages
serves that file so Google Calendar can subscribe to it. The Action deploys
straight to Pages and never commits, so the repo stays quiet on your profile.

Setup: Settings → Pages → Source: **GitHub Actions**.

Subscribe URL (after Pages is on):
`https://isha-das-06.github.io/wygo-calendar/wygo.ics`

## Adding organizers
Add the handle from `wygo.world/o/<handle>` to `organizers.txt` and commit.
For user pages (`wygo.world/u/<handle>`), write `u/<handle>`.
The Action runs automatically when that file changes.

## How it works
- Organizer page: takes the event links listed under "Upcoming Events".
- Event page: reads the schema.org Event JSON-LD (start, end, venue, description).
- `events.json` (published next to the feed) remembers events so they stay on the calendar for 45 days
  after they end.
- Waits 2 seconds between requests and only checks upcoming events.
