# Spec: Date Filter For Profile Page

## Overview
Step 6 adds a date-range filter to the `/profile` page so a user can scope
their summary stats, recent transactions, and category breakdown to a chosen
window (e.g. "This month", "Last 30 days", or a custom `from`/`to` range).
Today every section shows the user's entire history — this becomes noisy as
data grows and makes it impossible to answer "how much did I spend last
month?". The filter is driven by GET query parameters so the URL is
shareable, refresh-safe, and requires no client-side state.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables exist)
- Step 2: Registration
- Step 3: Login / Logout (session sets `user_id`)
- Step 4: Profile page static UI
- Step 5: Backend connection (the four query helpers in `database/queries.py`
  already power the profile page)

## Routes
No new routes. The existing `GET /profile` route now accepts three optional
query parameters:

- `range` — one of `this_month` | `last_month` | `last_7_days` | `last_30_days` | `all` | `custom`
- `from` — inclusive start date, format `YYYY-MM-DD` (only used when `range=custom`)
- `to`   — inclusive end date, format `YYYY-MM-DD` (only used when `range=custom`)

If `range` is missing or invalid, default to `this_month`.
If `range=custom` but `from`/`to` are missing or malformed, fall back to
`this_month` and surface a friendly inline message on the page.

## Database changes
No database changes. The existing `expenses.date` column (TEXT, `YYYY-MM-DD`)
already supports range queries with lexicographic comparisons.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar directly above the summary stats section:
    - Preset chips: This month · Last month · Last 7 days · Last 30 days · All time · Custom
    - Custom range reveals two `<input type="date">` fields and an Apply button
  - The active preset chip gets an `is-active` CSS class based on the
    server-provided `active_range` context variable
  - Show a small caption under the stats grid that describes the current
    window, e.g. "Showing 1 Aug 2026 – 31 Aug 2026"
  - If the filtered range has no expenses, show an empty state row inside
    the transactions table and hide the category breakdown list with a
    placeholder message ("No expenses in this range yet.")

## Files to change
- `app.py` — parse the query params in the `profile()` view, resolve them
  into a `(from_date, to_date)` tuple, and pass both the tuple and the
  chosen `active_range` string down to the query helpers and template
- `database/queries.py` — extend the three data helpers to accept an
  optional `date_range=(from_date, to_date)` argument:
  - `get_summary_stats(user_id, date_range=None)`
  - `get_recent_transactions(user_id, limit=None, date_range=None)`
  - `get_category_breakdown(user_id, date_range=None)`
  When `date_range` is provided, add a `AND date BETWEEN ? AND ?` clause
  using parameterised placeholders. `get_user_by_id` is unchanged.
- `templates/profile.html` — filter bar UI + active-state + empty states
- `static/css/profile.css` — styles for the filter bar, chips, custom-range
  panel, and empty-state row (CSS variables only, no hex literals)

## Files to create
- `filters.py` (project root) — a tiny module with pure functions:
  - `resolve_range(range_key, from_str, to_str, today)` →
    `{"active_range": <key>, "from_date": <YYYY-MM-DD>, "to_date": <YYYY-MM-DD>, "label": <human-readable string>, "error": <str or None>}`
  Keeping this out of `app.py` and `database/queries.py` keeps the
  presets easy to unit-test without a Flask context or a database.

## New dependencies
No new dependencies. Standard-library `datetime` is sufficient for the
preset calculations.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL
- Passwords hashed with werkzeug (unchanged; no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles (the `style="width: X%"` already in `profile.html` for
  the category bar is the only exception and stays as-is)
- Query helpers must keep working when `date_range=None` — this preserves
  backwards compatibility for any test or caller that expects "all data"
- Date comparisons use `YYYY-MM-DD` string ordering — do NOT cast to
  `DATE()` in SQLite; the column is TEXT by design
- `resolve_range` must treat "today" as an injectable parameter so tests
  can pin a fixed date (never call `datetime.today()` inside SQL or the
  view logic directly — always pipe through `resolve_range`)
- Preset ranges are inclusive on both ends
- The filter bar must degrade gracefully without JS: the Custom panel is
  a normal `<form method="get" action="{{ url_for('profile') }}">` and
  the preset chips are `<a href="?range=...">` links
- Never trust query-param dates — validate with
  `datetime.strptime(value, "%Y-%m-%d")` inside `resolve_range` and fall
  back to `this_month` on any `ValueError`

## Definition of done
- [ ] Visiting `/profile` with no query params defaults to `this_month`
      and the "This month" chip is highlighted
- [ ] Clicking each preset chip updates the URL (`?range=last_month` etc.)
      and reloads the page with matching stats, transactions, and category
      breakdown
- [ ] Selecting Custom, picking `from=2026-08-01` and `to=2026-08-10`,
      and pressing Apply shows only the four seed expenses that fall in
      that window (Food ₹250, Transport ₹120, Bills ₹1,800, Health ₹450)
- [ ] The summary stats (`total_spent`, `transaction_count`, `top_category`)
      recompute correctly for every preset — verified against the seed
      dataset by hand
- [ ] The category breakdown percentages still sum to exactly 100 when a
      subset is selected
- [ ] A custom range with no expenses (`from=2020-01-01&to=2020-01-31`)
      shows "No expenses in this range yet." in both the transactions
      table and the category breakdown, with total ₹0.00 and 0
      transactions
- [ ] Passing malformed dates (`?range=custom&from=not-a-date`) falls back
      to `this_month` and shows a small inline error above the filter bar
- [ ] The URL is shareable — pasting `/profile?range=last_month` into a
      new tab (while logged in) reproduces the same view
- [ ] No hex colour values appear in the changes to `profile.css` — only
      CSS variables from `style.css`
