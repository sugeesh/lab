# Research: URL Shortener

All Technical Context items are resolved. Each entry records the decision, why it was chosen,
and what else was considered. Choices favour the standard library and the fewest moving parts
(Constitution IV, YAGNI).

## 1. Web stack and rendering

- **Decision**: FastAPI app serving server-rendered HTML pages with Jinja2 templates and HTML
  forms. A single small vanilla-JS file handles only the copy button and time-zone detection.
- **Rationale**: Every flow (sign up, shorten, list, toggle, delete, stats) is a form post or a
  page view. Server rendering needs no build step, no client state, and is easy to test with
  FastAPI's `TestClient` by asserting on HTML.
- **Alternatives considered**: JSON API + SPA (React/Vue) — a second project and build chain
  for no user-visible benefit; HTMX — nice, but not needed for these flows.

## 2. Storage access

- **Decision**: SQLite through the standard-library `sqlite3` module with hand-written SQL in
  one schema file. WAL journal mode, `synchronous=NORMAL`, `foreign_keys=ON`,
  `busy_timeout=5000`. One connection per request.
- **Rationale**: Five small tables and a handful of queries; an ORM would add a dependency and
  hide the queries that the 50 ms target depends on. WAL lets reads proceed during writes.
- **Alternatives considered**: SQLAlchemy / SQLModel (extra dependency, abstraction without a
  second backend); migrations tool such as Alembic (one schema version for now; `CREATE TABLE
  IF NOT EXISTS` is enough).

## 3. Short-code generation and uniqueness

- **Decision**: `secrets.choice` over the 62-character alphabet `A–Z a–z 0–9`, 7 characters.
  The code is inserted into `issued_codes` (primary key `code`); on a unique-constraint
  failure a new code is generated, up to 5 attempts, then the request fails with a logged
  error. `issued_codes` rows are never deleted.
- **Rationale**: Cryptographically secure source as requested; the database constraint is the
  single source of truth for "never reused", including deleted links (FR-006). With 62⁷ ≈
  3.5 × 10¹² codes and 10⁶ issued, a collision has ~3 × 10⁻⁷ probability per attempt, so 5
  attempts never realistically fail.
- **Alternatives considered**: Pre-generated code pool (extra job, YAGNI); counter + encoding
  (not random, guessable); soft-deleting links instead of a separate table (mixes live and dead
  rows in the hot redirect lookup).

## 4. Click storage and the time-zone decision

- **Decision**: `daily_clicks(code, day, count)` with primary key `(code, day)`. Each redirect
  runs `INSERT … ON CONFLICT(code, day) DO UPDATE SET count = count + 1`. `day` is the
  calendar date in the **owner's saved time zone** at the moment of the click. The owner's
  IANA time zone is sent by the browser on sign-up/sign-in forms and stored on `users`.
- **Rationale**: User requirement — one row per link per day, so the 30-day view is a direct
  range read with no aggregation beyond filling zero days. Using the owner's zone (agreed
  during planning; spec updated) keeps day boundaries meaningful to the owner. A row per day
  means at most 30 rows read for the chart and one upsert per click.
- **Alternatives considered**: UTC days (shifts days for users far from UTC); 15-minute
  buckets regrouped per viewer (honours viewer time zone but ~2,900 rows per stats query and
  contradicts the requested design); one row per click (grows unbounded, needs aggregation).

## 5. Recording clicks without delaying redirects (FR-018a)

- **Decision**: The redirect handler returns the 302 response and schedules the upsert with
  FastAPI `BackgroundTasks`. The task catches every exception, logs it at `ERROR` with the
  code, and swallows it.
- **Rationale**: The visitor's response is sent before the write, so a slow or failed write
  never delays or blocks a redirect, and every miss is logged (SC-004).
- **Alternatives considered**: Inline write in a `try` block (adds write latency to every
  redirect); in-memory queue with retry (option B in clarification, rejected).

## 6. Meeting the 50 ms p95 target (SC-001)

- **Decision**: The redirect path does exactly one indexed read —
  `links` joined to `users` on the `code` primary key — returning URL, enabled flag, expiry,
  and owner time zone. Single uvicorn worker process.
- **Rationale**: A primary-key lookup in a 1M-row SQLite table takes well under 1 ms; at 50
  requests/second a single process has large headroom. Multiple workers would add SQLite
  write contention without need.
- **Verification**: `tests/perf/test_redirect_latency.py` seeds 1,000,000 links into a temp
  database, then drives 50 requests/second for 30 s against a running server and asserts p95
  < 50 ms server time (measured by a timing middleware header). Marked `perf`, run on demand.
- **Alternatives considered**: In-memory cache of hot links (not needed at this load, adds
  invalidation on disable/expire/delete); PostgreSQL (operational overhead beyond need).

## 7. Accounts, passwords, sessions

- **Decision**: Passwords hashed with standard-library `hashlib.scrypt` (n=2¹⁴, r=8, p=1,
  16-byte random salt), compared with `hmac.compare_digest`. Minimum 8 characters. Sessions
  are random 32-byte tokens (`secrets.token_urlsafe`) stored hashed (SHA-256) in a `sessions`
  table, sent as an `HttpOnly`, `SameSite=Lax` cookie (`Secure` when the base URL is https),
  valid 14 days. Sign-out deletes the row.
- **Rationale**: No third-party crypto dependency; server-side sessions make sign-out real.
  `SameSite=Lax` blocks cross-site form posts carrying the cookie, which covers CSRF for an
  app whose state changes are all POSTs.
- **Alternatives considered**: passlib/bcrypt/argon2 (extra dependency, scrypt is adequate);
  signed-cookie sessions via itsdangerous (cannot revoke on sign-out); CSRF tokens (redundant
  with SameSite=Lax for v1).

## 8. Creation limit (FR-007a)

- **Decision**: Before creating, count `issued_codes` rows for the user with `issued_at` in the
  last 60 minutes (index on `(user_id, issued_at)`). At 100, refuse with HTTP 429 and a message
  naming the time the oldest of those 100 drops out of the window.
- **Rationale**: Reuses the permanent `issued_codes` record, so deleting links does not free
  allowance. No extra table or in-memory state.
- **Alternatives considered**: Token bucket in memory (lost on restart, extra code).

## 9. URL validation (FR-004)

- **Decision**: `urllib.parse.urlsplit`; accept only `http`/`https` with a non-empty host,
  total length ≤ 2,048, and host not equal to the configured service host.
- **Rationale**: Standard library, exactly the rules in the spec.

## 10. Route layout and code collisions

- **Decision**: Short links live at `/{code}` matching `^[A-Za-z0-9]{7}$`. All app pages live
  under multi-segment or non-7-character paths (`/`, `/account/...`, `/links...`, `/static/...`).
  A unit test asserts no single-segment app route is 7 alphanumeric characters.
- **Rationale**: Keeps short links as short as possible without any generated code ever
  shadowing an app page.

## 11. Status codes for visitor pages

- **Decision**: Redirect `302 Found`; expired `410 Gone`; disabled `403 Forbidden`;
  not found / deleted `404 Not Found`. All three non-redirect cases render a plain HTML page.
- **Rationale**: 302 satisfies FR-013 (temporary, not cached permanently). Distinct codes make
  each case simple to test and correct for clients and crawlers.

## 12. Tooling

- **Decision**: `pyproject.toml` with runtime deps `fastapi`, `uvicorn`, `jinja2`,
  `python-multipart`; dev deps `pytest`, `httpx` (needed by `TestClient` and the perf test),
  `ruff` (format + lint, Constitution II). Time zones via standard-library `zoneinfo` using the
  system tz database.
- **Rationale**: Smallest set that covers the request; each dependency has a current need.
- **Alternatives considered**: `tzdata` package (only needed where the OS lacks a tz database;
  add if deploying to such a host).

## 13. Interface style (Constitution V)

- **Decision**: One stylesheet with tokens on `:root` (neutral palette, one accent colour,
  system font stack, 4-step type scale, 4-px spacing scale). Pages are plain forms and tables;
  the 30-day chart is a table with CSS-width bars. No gradients, emoji, icon fonts, or
  marketing copy.
- **Rationale**: Meets Usability (III) and Human-Crafted Interface (V) with no UI library.
