# Spec: Registration

## Overview
Turn the existing `/register` page from a display-only stub into a working
account-creation flow. The GET handler already renders `register.html`, but
there is no POST handler — submitting the form does nothing useful. This
step adds the POST handler that validates input, hashes the password with
`werkzeug`, inserts a new row into the `users` table, and redirects the user
to the login page on success. It is the first authentication step in the
Spendly roadmap and unblocks Step 3 (login/logout).

## Depends on
- Step 1 — Database setup. The `users` table and `get_db()` helper must
  already exist in `database/db.py`.

## Routes
- `POST /register` — accepts form submission, creates a new user, redirects
  to `/login` on success or re-renders `register.html` with an error
  message on failure — public.

The existing `GET /register` handler stays as-is (renders the template).
The single view function will handle both methods via `methods=["GET", "POST"]`.

## Database changes
No database changes. The existing `users` table (id, name, email,
password_hash, created_at) is sufficient. Verified in `database/db.py`.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/register.html` — change the form's `action="/register"` to
    `action="{{ url_for('register') }}"` so the URL is not hardcoded.
    The existing `{% if error %}` block already renders errors from context.

## Files to change
- `app.py` — replace the current GET-only `register()` view with a
  combined GET/POST view that handles form submission.
- `templates/register.html` — replace hardcoded `/register` in the form
  action with `url_for('register')`.

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already
imported in `database/db.py` and ships with Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()`.
- Parameterised queries only — use `?` placeholders, never f-strings in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash` before
  insertion. Never store plaintext.
- Use CSS variables — never hardcode hex values (no CSS changes expected,
  but if any are added, follow this rule).
- All templates extend `base.html` (`register.html` already does).
- DB logic stays in `database/db.py`. Add a helper such as
  `create_user(name, email, password)` there — do not run raw SQL inside
  the route function.
- Server-side validation:
  - `name`, `email`, `password` all required and non-empty (after strip).
  - `password` must be at least 8 characters.
  - `email` must be unique — catch `sqlite3.IntegrityError` from the
    UNIQUE constraint and show a friendly error rather than a 500.
- On validation failure, re-render `register.html` with an `error` string
  and preserve the entered `name` and `email` values (never the password).
- On success, `redirect(url_for('login'))`. No session/login is set here —
  auto-login belongs to Step 3.
- Do not add a flash-message system yet; use the existing `error` block
  in the template.

## Definition of done
- [ ] Visiting `/register` still shows the form (GET behaviour unchanged).
- [ ] Submitting a valid new account inserts a row into `users` with a
      hashed password (verifiable via `sqlite3 spendly.db "SELECT ..."`).
- [ ] After successful submission, browser is redirected to `/login`.
- [ ] Submitting an email that already exists re-renders the form with a
      visible error message and does not create a duplicate row.
- [ ] Submitting a password shorter than 8 characters re-renders the form
      with an error and does not insert anything.
- [ ] Submitting with any required field blank re-renders the form with
      an error.
- [ ] The `password_hash` column stores a `werkzeug`-style hash
      (starts with `scrypt:` or `pbkdf2:`), never plaintext.
- [ ] `register.html` uses `url_for('register')` in the form action — no
      hardcoded `/register` string remains in the template.
- [ ] Name and email values are preserved in the form after a failed
      submission; the password field is cleared.
- [ ] App still starts cleanly and existing routes (`/`, `/login`,
      `/terms`, `/privacy`) continue to work.
