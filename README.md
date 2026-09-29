# Wygo calendar feed

Wygo (wygo.world) has no calendar subscribe option, so this repo builds one.
A GitHub Action runs every 6 hours, reads the upcoming events for each
organizer in `organizers.txt`, and writes `docs/wygo.ics`. GitHub Pages
serves that file so Google Calendar can subscribe to it.

Subscribe URL (after Pages is on):
`https://isha-das-06.github.io/wygo-calendar/wygo.ics`

## Adding organizers
Add the handle from `wygo.world/o/<handle>` to `organizers.txt` and commit.
The Action runs automatically when that file changes.

## How it works
- Organizer page: takes the event links listed under "Upcoming Events".
- Event page: reads the schema.org Event JSON-LD (start, end, venue, description).
- `docs/events.json` remembers events so they stay on the calendar for 45 days
  after they end.
- Waits 2 seconds between requests and only checks upcoming events.
