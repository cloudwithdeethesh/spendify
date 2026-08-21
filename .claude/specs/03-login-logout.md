# Spec: Login and Logout

## Overview
Turn the existing `/login` page from a display-only stub into a working
sign-in flow, and replace the placeholder `/logout` route with real
session teardown. Registration (Step 2) can now create accounts, but
there is no way to actually sign in as one — this step closes that gap
by adding the POST handler for `/login`, wiring Flask sessions, and
implementing `/logout`. It is the first step that introduces the
concept of a logged-in user and unblocks Step 4 (`/profile`) and every
subsequent expense route, which all need to know who the current user
is.

## Depends on
- Step 1 — Database setup. The `users` table and `get_db()` helper
  must already exist.
- Step 2 — Registration. Users must be able to create accounts so that
  login has real credentials to validate against (the seeded
  `demo@spendly.com` / `demo123` account also works).

## Routes
- `POST /login` — accepts form submission, verifies email + password
  against the `users` table, stores the user id in the Flask session
  on success, and redirects to `/profile`. On failure, re-renders
  `login.html` with an error message — public.
- `GET /logout` — clears the session and redirects to `/` — logged-in
  (but safe to call when not logged in; simply no-ops the session
  clear and redirects).

The existing `GET /login` handler stays as-is (renders the template).
The single view function will handle both methods via
`methods=["GET", "POST"]`.

## Database changes
No database changes. The existing `users` table already stores
`email` and `password_hash`, which is everything login needs.
Verified against `database/db.py`.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/login.html` — replace the hardcoded
    `action="/login"` with `action="{{ url_for('login') }}"`. The
    existing `{% if error %}` block already renders errors from
    context; keep the `email` value across a failed submission by
    reading `value="{{ email or '' }}"` on the email input.
  - `templates/base.html` — update the nav so the visible links
    reflect login state: when a user is logged in, show the user's
    name (linking to `/profile`) and a "Sign out" link to
    `/logout`; when not, keep the current "Sign in" and
    "Get started" links. Use `session.get('user_id')` to branch
    inside the template.

## Files to change
- `app.py` — set `app.secret_key`, replace the current GET-only
  `login()` view with a combined GET/POST view, and replace the
  `logout()` stub with a real handler that clears the session.
- `database/db.py` — add a small helper such as
  `get_user_by_email(email)` that returns the row (or `None`) so
  the login route does not run raw SQL inline.
- `templates/login.html` — use `url_for('login')` in the form
  action, preserve the email value across failed submissions.
- `templates/base.html` — conditional nav links based on
  `session.get('user_id')`.

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` ships
with Flask and pairs with the `generate_password_hash` already used
by registration and seeding.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()`.
- Parameterised queries only — use `?` placeholders, never
  f-strings in SQL.
- Password verification must use
  `werkzeug.security.check_password_hash` against the stored
  `password_hash`. Never compare plaintext passwords or hashes with
  `==`.
- Use CSS variables — never hardcode hex values (no CSS changes
  expected, but if any are added, follow this rule).
- All templates extend `base.html` (`login.html` already does).
- DB logic stays in `database/db.py`. Add
  `get_user_by_email(email)` there — do not run raw SQL inside the
  route function.
- Server-side validation:
  - `email` and `password` both required and non-empty (after
    strip on email).
  - On unknown email OR wrong password, show the same generic
    error ("Invalid email or password.") — do not leak which
    field was wrong.
- On successful login, set `session["user_id"]` and
  `session["user_name"]`, then `redirect(url_for("profile"))`.
  `/profile` remains a stub until Step 4; that is expected.
- On login failure, re-render `login.html` with an `error` string
  and preserve the entered `email` value (never the password).
- `app.secret_key` must be set before any session use. Read it from
  the `SPENDLY_SECRET_KEY` environment variable if present, and
  fall back to a hardcoded dev-only string with a clear inline
  note that it must be overridden in production. Do not add a new
  dependency (e.g. `python-dotenv`) for this.
- `logout()` calls `session.clear()` and returns
  `redirect(url_for("landing"))`. It is a `GET` route (matches the
  existing stub signature and the nav link pattern) — do not
  require POST or CSRF for this step.
- Do not add a `@login_required` decorator or protect any routes
  yet — route protection belongs to a later step. This spec only
  wires the session in and out.
- Do not add a flash-message system yet; use the existing `error`
  block in the template.

## Definition of done
- [ ] Visiting `/login` still shows the form (GET behaviour
      unchanged).
- [ ] Submitting valid credentials (e.g. seeded
      `demo@spendly.com` / `demo123`, or any account created via
      `/register`) redirects the browser to `/profile` and the
      session contains `user_id` and `user_name`.
- [ ] Submitting an unknown email re-renders the form with the
      generic "Invalid email or password." error.
- [ ] Submitting a known email with the wrong password re-renders
      the form with the same generic error — never a
      field-specific one.
- [ ] Submitting with `email` or `password` blank re-renders the
      form with an error and does not query for a user.
- [ ] The email value is preserved in the form after a failed
      submission; the password field is cleared.
- [ ] `login.html` uses `url_for('login')` in the form action — no
      hardcoded `/login` string remains in the template.
- [ ] Visiting `/logout` clears the session and redirects to `/`;
      after logout, the nav shows "Sign in" / "Get started" again.
- [ ] While logged in, the base nav shows the user's name (link to
      `/profile`) and a "Sign out" link instead of "Sign in" /
      "Get started".
- [ ] `app.secret_key` is set; sessions survive across requests in
      the dev server.
- [ ] Password verification uses `check_password_hash` — grepping
      the codebase finds no `==` comparison against
      `password_hash`.
- [ ] App still starts cleanly and existing routes (`/`,
      `/register`, `/terms`, `/privacy`) continue to work.
