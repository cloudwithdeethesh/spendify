# Spec: Add Expense

## Overview
Step 7 turns the `/expenses/add` stub into a real feature so a logged-in user
can record a new expense (amount, category, date, description) and see it
appear immediately on their `/profile` page. Until now the profile is
populated only from seed data; this is the first user-driven write to the
`expenses` table and is the foundation for edit (Step 8) and delete
(Step 9). The form is a plain HTML `POST` — no JavaScript required — with
server-side validation and inline error messages.

## Depends on
- Step 1: Database setup (`expenses` table exists with `user_id`, `amount`,
  `category`, `date`, `description` columns)
- Step 2: Registration (users can exist)
- Step 3: Login / Logout (`session['user_id']` is available)
- Step 4: Profile page static UI (destination after successful add)
- Step 5: Backend routes for profile page (query helpers render the new row)
- Step 6: Date filter on profile (new expense must slot into the current
  filter window correctly)

## Routes
- `GET  /expenses/add` — render the empty add-expense form — logged-in only
- `POST /expenses/add` — validate, insert, redirect to `/profile` — logged-in only

Both routes replace the current stub at `app.py:207`. Unauthenticated
requests redirect to `/login` (same guard pattern as `profile()`).

## Database changes
No schema changes. The existing `expenses` table already has every column
needed. A new helper `create_expense(user_id, amount, category, date,
description)` is added to `database/db.py`.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Card-style form with fields:
    - **Amount** — `<input type="number" step="0.01" min="0.01" required>` with `₹` prefix
    - **Category** — `<select required>` populated from the seven canonical
      categories (Food, Transport, Bills, Health, Entertainment, Shopping,
      Other) — the values must match `CATEGORY_SLUGS` keys in
      `database/queries.py` exactly, since profile grouping is
      case-sensitive
    - **Date** — `<input type="date" required>` defaulting to today
      (`value="{{ today }}"` from the view)
    - **Description** — `<input type="text" maxlength="120">` (optional)
  - Primary "Save expense" button and a secondary "Cancel" link back to
    `/profile`
  - Repopulates all four fields on validation error (`request.form` echoed
    back so the user doesn't retype)
  - Renders an inline error banner above the form when `error` is set
- **Modify:** `templates/profile.html`
  - The existing "Add expense" call-to-action (if any) must point to
    `url_for('add_expense')` — verify the current href and update if
    hardcoded

## Files to change
- `app.py` — replace the `add_expense` stub with a real view that handles
  both `GET` and `POST`, validates input, calls `create_expense`, and
  redirects to `/profile` on success. Import `create_expense` from
  `database.db` and `CATEGORY_SLUGS` from `database.queries`.
- `database/db.py` — add `create_expense(user_id, amount, category, date,
  description)` that runs a single parameterised `INSERT` and commits.
- `templates/profile.html` — point any existing "Add expense" link at
  `url_for('add_expense')` (no visual change).

## Files to create
- `templates/add_expense.html` — the form template described above.
- `static/css/add_expense.css` — scoped styles for the form card, input
  rows, currency prefix, and the inline error banner. Loaded via a
  `{% block head %}` link in the template (same pattern as
  `profile.css` and `analytics.css`).

## New dependencies
No new dependencies. `werkzeug` (already used for password hashing) is not
needed here; standard-library `datetime` covers date defaults and
validation.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never f-string user input into SQL
- Passwords hashed with werkzeug (unchanged; no auth changes in this step)
- Use CSS variables — never hardcode hex values in `add_expense.css`
- All templates extend `base.html`
- Currency is INR — display `₹` in the amount field prefix and any
  confirmation copy (never `$`)
- Reject amounts `<= 0` server-side even though the input has `min="0.01"`
  — the HTML attribute is a hint, not a guarantee
- Category must be validated against `CATEGORY_SLUGS.keys()` — reject
  anything else with an inline error rather than trusting the `<select>`
- Date must parse with `datetime.strptime(value, "%Y-%m-%d")` — reject
  malformed input and reject dates in the future (an expense you haven't
  spent yet is almost always a typo)
- Description is optional; strip whitespace and store `NULL` if empty so
  the profile table shows a clean dash instead of a blank cell
- Never log the raw form dict — it may contain PII in the description
- The `POST` handler must guard on `session['user_id']` first, before
  reading `request.form`, and redirect to `/login` if missing
- On success, `redirect(url_for('profile'))` — do not render the form
  again with a "success" flash (out of scope for this step)
- The form is a plain `<form method="POST">` — no `fetch()`, no JS
  submission handler

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders the form with the
      date field pre-filled to today
- [ ] Submitting a valid expense (e.g. ₹99.50, Food, today, "Coffee")
      inserts one row into `expenses` for the current `user_id` and
      redirects to `/profile`
- [ ] The new expense appears in the "Recent transactions" list on
      `/profile` and is included in the summary stats
- [ ] The new expense respects the profile date filter — adding one dated
      inside `?range=this_month` shows immediately; adding one dated last
      year does not appear until the range is widened
- [ ] Submitting an empty amount, a non-numeric amount, or `0` re-renders
      the form with an inline error and the other fields still populated
- [ ] Submitting a category that isn't one of the seven canonical values
      (e.g. by tampering with the form) is rejected with an inline error
- [ ] Submitting a future date is rejected with an inline error
- [ ] Submitting with an empty description succeeds and the profile row
      shows a dash (not "None" or an empty string)
- [ ] `POST /expenses/add` without a session redirects to `/login` and
      does not insert a row
- [ ] `add_expense.css` contains zero hex literals — only `var(--…)`
      references from `style.css`
