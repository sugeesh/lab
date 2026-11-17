---

description: "Task list for the URL Shortener feature"
---

# Tasks: URL Shortener

**Input**: Design documents from `/specs/001-url-shortener/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-routes.md, quickstart.md

**Tests**: REQUIRED. Constitution Principle I (TDD, non-negotiable): every test task is written
first and MUST be run and seen to FAIL before the implementation task that follows it.

**Organization**: Tasks are grouped by user story so each story can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: User story the task belongs to (US1–US4)

## Conventions used by every task

- Package root: `src/shortener/`; tests: `tests/`. Python 3.12.
- Business functions are plain functions taking a `sqlite3.Connection` as the first argument
  and, where time matters, an explicit `now: datetime` (timezone-aware UTC) argument so tests
  control the clock. Web handlers pass `datetime.now(timezone.utc)`.
- Timestamps are stored as UTC text `YYYY-MM-DDTHH:MM:SSZ`.
- Integration tests use FastAPI `TestClient` against an app built by `create_app(db_path,
  base_url)` with a temporary SQLite file (fixtures in `tests/conftest.py`).
- UI copy is plain and specific; no emoji, gradients, or marketing words (Constitution V).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization

- [X] T001 Create `pyproject.toml`: project `shortener`, `requires-python = ">=3.12"`, src
  layout (`src/shortener`), runtime deps `fastapi`, `uvicorn`, `jinja2`, `python-multipart`;
  optional `dev` deps `pytest`, `httpx`, `ruff`, `pytest-playwright`. Add `[tool.ruff]`
  (line-length 100, target py312, lint rules `E,F,W,I,B,UP,SIM`) and
  `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `pythonpath = ["src"]`, markers
  `perf: slow 1M-link latency test` and `browser: runs app.js in headless Chromium`, and
  `addopts = "-m 'not perf' --browser chromium"`.
- [X] T002 Create empty package and test skeleton: `src/shortener/__init__.py`,
  `src/shortener/web/__init__.py`, `src/shortener/templates/`, `src/shortener/static/`,
  `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`,
  `tests/perf/__init__.py`, `tests/browser/__init__.py`; add `.gitignore` entries `.venv/`, `*.db`, `__pycache__/`,
  `.pytest_cache/`, `.ruff_cache/`.
- [X] T003 Check `python3 --version` reports 3.12 or newer (3.12 is the minimum and the
  language level ruff targets; this machine has 3.14), then create the virtualenv and install
  (`python3 -m venv .venv && pip install -e
  ".[dev]" && playwright install chromium`); confirm `ruff check .` and `pytest` run (pytest
  reports no tests).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, database, accounts/sessions, app shell, base UI. Every story needs a
signed-in user.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests first (must FAIL before T010–T017)

- [X] T004 Write fixtures in `tests/conftest.py`: `db_path` (tmp_path file), `app`
  (`create_app(db_path=..., base_url="http://short.test")`), `client` (`TestClient(app,
  base_url="http://short.test")`), `signed_in_client` (signs up `alice@example.com` /
  `password123` with `time_zone=UTC` and returns the client), and `other_client` (a second
  client signed in as `bob@example.com`), plus `conn` (a connection from
  `shortener.db.connect(db_path)`).
- [X] T005 [P] Write `tests/unit/test_config.py`: `Settings.from_env()` reads `SHORTENER_DB`
  (default `./shortener.db`) and `SHORTENER_BASE_URL` (default `http://localhost:8000`);
  `settings.host` returns the base URL host; `settings.secure_cookies` is true only for
  `https` base URLs.
- [X] T006 [P] Write `tests/unit/test_db.py`: `connect()` sets `journal_mode=wal`,
  `foreign_keys=1`, `busy_timeout=5000`; `init_schema()` creates tables `users`, `sessions`,
  `issued_codes`, `links`, `daily_clicks` and is safe to run twice.
- [X] T007 [P] Write `tests/unit/test_accounts.py`:
  - `hash_password`/`verify_password` round-trip; wrong password fails; two hashes of the same
    password differ (random salt).
  - `create_user`: lower-cases email; rejects email without `@` or longer than 254 chars;
    rejects password shorter than 8 chars; rejects duplicate email (case-insensitive) — each
    with a distinct `AccountError` message.
  - `normalize_time_zone`: valid IANA name kept (`Asia/Colombo`); empty or unknown → `"UTC"`.
  - `authenticate` returns the user for correct credentials, `None` otherwise.
  - `create_session` returns a raw token; only its SHA-256 is stored; `user_for_session`
    returns the user while `expires_at` (created + 14 days) is in the future and `None`
    after; `delete_session` removes it.
- [X] T008 [P] Write `tests/integration/test_accounts_flow.py` per contracts/http-routes.md:
  - `POST /account/signup` valid → 303 to `/`, `session` cookie is HttpOnly and SameSite=Lax;
    invalid → 400 with the specific message in the HTML.
  - `POST /account/signin` correct → 303 to `next` (default `/`) and updates the user's
    `time_zone`; wrong → 400 containing "Email or password is incorrect".
  - `POST /account/signout` → 303 to `/account/signin`; the old cookie no longer signs in.
  - `GET /` signed out → 303 to `/account/signin?next=/`.
- [X] T009 [P] Write `tests/unit/test_timing.py`: every response from the app has a
  `Server-Timing` header matching `app;dur=<number>`.

### Implementation

- [X] T010 Implement `src/shortener/config.py`: frozen dataclass `Settings(db_path, base_url)`
  with `from_env()`, `host`, `secure_cookies` (makes T005 pass).
- [X] T011 Write `src/shortener/schema.sql` exactly per data-model.md using `CREATE TABLE IF
  NOT EXISTS`:
  - `users(id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
    time_zone TEXT NOT NULL DEFAULT 'UTC', created_at TEXT NOT NULL)`
  - `sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON
    DELETE CASCADE, expires_at TEXT NOT NULL)`
  - `issued_codes(code TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    issued_at TEXT NOT NULL)` + index `(user_id, issued_at)` — rows "are never deleted"
  - `links(code TEXT PRIMARY KEY REFERENCES issued_codes(code), user_id INTEGER NOT NULL
    REFERENCES users(id), target_url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT NULL, created_at TEXT NOT NULL)` + index `(user_id, created_at DESC)`
  - `daily_clicks(code TEXT NOT NULL REFERENCES links(code) ON DELETE CASCADE, day TEXT NOT
    NULL, count INTEGER NOT NULL, PRIMARY KEY (code, day))`
- [X] T012 Implement `src/shortener/db.py`: `connect(path)` (row factory `sqlite3.Row`,
  pragmas `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`)
  and `init_schema(conn)` loading `schema.sql` via `importlib.resources` (makes T006 pass).
- [X] T013 Implement `src/shortener/accounts.py`: `AccountError`, `hash_password` /
  `verify_password` with `hashlib.scrypt` (n=2**14, r=8, p=1, 16-byte salt, stored as
  `scrypt$<salt hex>$<hash hex>`, compared with `hmac.compare_digest`), `normalize_time_zone`
  (via `zoneinfo.ZoneInfo`), `create_user`, `authenticate`, `update_time_zone`,
  `create_session` (`secrets.token_urlsafe(32)`), `user_for_session`, `delete_session`
  (makes T007 pass).
- [X] T014 Implement `src/shortener/main.py`: `create_app(db_path=None, base_url=None)`
  building `Settings`, running `init_schema` once, mounting `/static`, configuring
  `Jinja2Templates` on `src/shortener/templates`, a middleware adding `Server-Timing:
  app;dur=<ms>`, dependencies `get_conn` (one connection per request, closed after) and
  `require_user` (when no valid session, raises a 303 redirect to
  `/account/signin?next=<path>` for `GET` requests and to `/account/signin?next=/` for any
  other method, so signing in never lands on a POST-only path), module-level `app = create_app()`, and `logging.basicConfig(level=INFO)`
  (makes T009 pass).
- [X] T015 [P] Create `src/shortener/static/style.css`: tokens on `:root` (neutral
  background/text/border, one accent, error and success colours, all WCAG AA on their
  backgrounds; system font stack; type scale 14/16/20/28 px; spacing 4/8/16/24/32 px);
  single-column layout max 720 px with 16 px side padding; visible `:focus-visible` outline;
  forms, buttons, tables, `.error` and `.notice` styles; no gradients, shadows limited to
  none, no emoji or icon fonts. Works at 320 px with no horizontal scroll.
- [X] T016 [P] Browser-test, then create, time-zone detection in `src/shortener/static/app.js`:
  1. **Test first** — create `tests/browser/conftest.py` with fixtures: `live_server` (starts
     `uvicorn` for `create_app(db_path=<tmp file>, base_url=<server URL>)` on a free port in a
     background thread, yields the base URL, stops it afterwards), `live_db` (connection to that
     temp DB), and `signed_in_page` (a Playwright `page` that has signed up
     `carol@example.com` / `password123` through the real form). Then write
     `tests/browser/test_time_zone.py` (marker `browser`): with a browser context created with
     `timezone_id="Asia/Colombo"`, open `/account/signup`; assert the hidden
     `input[name=time_zone]` has value `Asia/Colombo`; submit the form and assert the new
     `users.time_zone` row is `Asia/Colombo`. Run it and see it FAIL (empty value).
  2. **Implement** — create `src/shortener/static/app.js`: on `DOMContentLoaded`, set every
     `input[name=time_zone]` to `Intl.DateTimeFormat().resolvedOptions().timeZone`. The test
     goes green once T017 has added the sign-up page.
- [X] T017 Create templates and routes for accounts:
  `src/shortener/templates/base.html` (title block, header with product name and, when signed
  in, the user's email and a sign-out form button; loads `style.css` and `app.js`),
  `src/shortener/templates/signup.html`, `src/shortener/templates/signin.html` (labelled
  inputs, hidden `time_zone`, hidden `next`, error message area), and
  `src/shortener/web/account.py` implementing `GET/POST /account/signup`,
  `GET/POST /account/signin`, `POST /account/signout` with cookie `session` (HttpOnly,
  SameSite=Lax, Secure when `settings.secure_cookies`, max-age 14 days). Register the router
  in `main.py`. Temporary `GET /` placeholder behind `require_user` so T008 passes (replaced
  in T027).

**Checkpoint**: `pytest` green; a person can sign up, sign in, and sign out.

---

## Phase 3: User Story 1 - Shorten a link and share it (Priority: P1) 🎯 MVP

**Goal**: A signed-in user submits a long address, gets a 7-character short link with a copy
button; anyone opening it is redirected.

**Independent Test**: Sign in, submit a long address, open the short link in a fresh client,
confirm a 302 to the original address.

### Tests for User Story 1 (write first, must FAIL) ⚠️

- [X] T018 [P] [US1] Write `tests/unit/test_codes.py`: `generate_code()` returns exactly 7
  characters, all in `string.ascii_letters + string.digits`; `issue_code(conn, user_id, now,
  generate=...)` inserts into `issued_codes` and returns the code; when `generate` first
  yields an already-issued code it retries and returns the next one; after 5 collisions it
  raises `CodeExhaustedError`.
- [X] T019 [P] [US1] Write `tests/unit/test_urls.py` for `validate_target_url(url,
  service_host)`: accepts `https://example.com/a?x=1` and `http://example.com`; rejects
  empty, `ftp://x`, `example.com` (no scheme), `http://` (no host), any URL longer than
  2,048 characters, and URLs whose host equals `service_host` — each raising `UrlError` with
  a specific plain-language message.
- [X] T020 [P] [US1] Write `tests/unit/test_routes.py`: iterate `app.routes`; no path made of
  one segment matches `^/[A-Za-z0-9]{7}$` except the short-link route `/{code}`.
- [X] T021 [P] [US1] Write `tests/unit/test_rate_limit.py` for `links.check_creation_allowed(
  conn, user_id, now)`: 99 `issued_codes` rows in the last 60 minutes → allowed; 100 →
  raises `RateLimitError` whose `retry_at` equals the oldest of those 100 `issued_at` + 60
  minutes; rows older than 60 minutes are not counted.
- [X] T022 [P] [US1] Write `tests/integration/test_us1_shorten.py` covering spec US1
  scenarios:
  1. `POST /links url=https://example.com/a/very/long/path?x=1` → 303 to `/links/{code}`; the
     page shows `http://short.test/{code}` with a 7-char code and a button labelled "Copy".
  2. A new unauthenticated client `GET /{code}` → 302, `Location` equals the original URL,
     `Cache-Control: no-store`.
  3. Invalid URL (`ftp://x`) and self-referencing URL (`http://short.test/abcdefg`) → 400 with
     the message; no row added to `links`.
  4. Signed-out `POST /links` → 303 to `/account/signin?next=/` (not `next=/links`, which has
     no GET page); signing in from there lands on `/` with the shorten form.
  5. Same URL submitted twice → two different codes.
  6. `GET /ZZZZZZZ` (never issued) → 404 page containing "Link not found".
  7. With 100 `issued_codes` rows for the user in the last hour, `POST /links` → 429 and the
     page states the time they can try again; no link created.
  8. Codes are case-sensitive: swapping the case of a real code returns 404.

### Implementation for User Story 1

- [X] T023 [P] [US1] Implement `src/shortener/codes.py`: `ALPHABET`, `CODE_LENGTH = 7`,
  `MAX_ATTEMPTS = 5`, `generate_code()` with `secrets.choice`, `CodeExhaustedError`,
  `issue_code(conn, user_id, now, generate=generate_code)` inserting into `issued_codes` and
  retrying on `sqlite3.IntegrityError` (makes T018 pass).
- [X] T024 [P] [US1] Implement `src/shortener/urls.py`: `UrlError`, `MAX_URL_LENGTH = 2048`,
  `validate_target_url(url, service_host)` using `urllib.parse.urlsplit`; accept only
  `http`/`https`, non-empty host, ≤ 2,048 chars, host ≠ service host (case-insensitive)
  (makes T019 pass).
- [X] T025 [US1] Implement in `src/shortener/links.py`: `RateLimitError(retry_at)`,
  `CREATION_LIMIT = 100`, `check_creation_allowed(conn, user_id, now)`, `create_link(conn,
  user_id, target_url, service_host, now, expires_at=None)` (validate → rate-limit → issue
  code → insert `links` row, all in one transaction, returns the code), `get_owned_link(conn,
  user_id, code)` (returns `None` for other users' links — FR-003), and
  `find_for_redirect(conn, code)` running the single join in data-model.md "Redirect lookup"
  (makes T021 pass).
- [X] T026 [US1] Implement `src/shortener/web/redirect.py`: `GET /{code:str}` (validate
  `^[A-Za-z0-9]{7}$`, else 404) → 302 to `target_url` with `Cache-Control: no-store`, or 404
  rendering `templates/visitor_not_found.html` ("Link not found" + one sentence on what that
  means). Register this router **last** in `main.py`.
- [X] T027 [US1] Implement `src/shortener/web/links.py` routes `GET /` (replace the
  placeholder: shorten form with labelled URL field, autofocus, submit on Enter, hidden
  `time_zone`) and `POST /links` (400 re-renders the form with the entered URL and the error;
  429 renders the limit message with the retry time formatted `HH:MM` in the user's time
  zone; success 303 to `/links/{code}`), plus `GET /links/{code}` (404 via
  `visitor_not_found.html` when not owned) rendering `templates/link.html` with the full short
  link in a read-only input and a "Copy" button. Templates: `src/shortener/templates/home.html`,
  `src/shortener/templates/link.html`, `src/shortener/templates/visitor_not_found.html`
  (makes T020 and T022 pass).
- [X] T028 [US1] Browser-test, then add, the copy button in `src/shortener/static/app.js`:
  1. **Test first** — write `tests/browser/test_copy_button.py` (marker `browser`) using
     `signed_in_page` from `tests/browser/conftest.py`:
     - Grant the context `clipboard-read` and `clipboard-write`, call `page.clock.install()`,
       submit `https://example.com/a/very/long/path` on `/`, click the "Copy" button. Assert
       `navigator.clipboard.readText()` equals the short link shown in the read-only input,
       the button text is "Copied", and the `aria-live="polite"` region contains "Copied".
       `page.clock.fast_forward(2000)`; assert the button text is "Copy" again.
     - With `page.add_init_script` making `navigator.clipboard.writeText` return a rejected
       promise, click "Copy"; assert the short-link input is focused with all its text
       selected (`selectionStart == 0`, `selectionEnd == value.length`) and the page shows
       "Press Ctrl+C to copy".
     Run them and see them FAIL.
  2. **Implement** — extend `src/shortener/static/app.js`: buttons with `data-copy-target`
     copy the target input's value via `navigator.clipboard.writeText` and change their text
     to "Copied" for 2 seconds, announced through an `aria-live="polite"` region; if the
     clipboard API fails, focus and select the input text and show "Press Ctrl+C to copy".

**Checkpoint**: MVP — shorten, copy, redirect all work; `pytest` green.

---

## Phase 4: User Story 2 - Manage my own links (Priority: P2)

**Goal**: List own links newest first, disable/enable, delete with confirmation, strict
ownership isolation.

**Independent Test**: With two accounts, each sees only its own links; disable/enable/delete
change redirect behaviour as specified.

### Tests for User Story 2 (write first, must FAIL) ⚠️

- [X] T029 [P] [US2] Write `tests/unit/test_link_status.py` for `links.status(enabled,
  expires_at, now)`: `enabled=0` → `"disabled"` (even when expired); `expires_at ≤ now` →
  `"expired"`; otherwise `"active"`; `expires_at=None` and enabled → `"active"`.
- [X] T030 [P] [US2] Write `tests/integration/test_us2_manage.py` covering spec US2
  scenarios:
  1. Three links created → `GET /` lists exactly those three, newest first, each row showing
     original address, short link, status, expiry ("No expiry" when none), created date,
     total clicks.
  2. `POST /links/{code}/disable` → 303; a visitor `GET /{code}` → 403 page containing
     "This link is disabled".
  3. `POST /links/{code}/enable` → visitor gets 302 again.
  4. `GET /links/{code}/delete` shows a confirmation; `POST /links/{code}/delete` → 303 to
     `/`; link gone from list; visitor gets 404; the code's `issued_codes` row still exists;
     creating more links never returns that code (force with a stub `generate` in a unit
     call to `issue_code`).
  5. `other_client` gets 404 for `GET /links/{code}`, `POST /links/{code}/disable`,
     `/enable`, `/expiry`, `/delete` on alice's link, and alice's link is unchanged.
  6. A user with no links sees a plain empty state ("No links yet") on `/`.

### Implementation for User Story 2

- [X] T031 [US2] Add to `src/shortener/links.py`: `status(enabled, expires_at, now)`,
  `list_links(conn, user_id)` (newest first, using the `(user_id, created_at DESC)` index;
  total clicks via `LEFT JOIN` + `SUM(daily_clicks.count)` defaulting to 0), `set_enabled(conn,
  user_id, code, enabled)`, `delete_link(conn, user_id, code)` (deletes the `links` row;
  `daily_clicks` go by cascade; `issued_codes` untouched). Each mutator returns `False` when
  the link is not owned (makes T029 pass).
- [X] T032 [US2] Extend `src/shortener/web/redirect.py`: when `status` is `"disabled"`
  render `templates/visitor_disabled.html` with 403. Create
  `src/shortener/templates/visitor_disabled.html` ("This link is disabled" + "The owner has
  turned this link off.").
- [X] T033 [US2] Extend `src/shortener/web/links.py` and templates: link table on
  `home.html` (semantic `<table>`, collapses to stacked rows under 480 px), status shown as
  text; on `link.html` add a Disable/Enable form button and a "Delete link" link; add
  `GET /links/{code}/delete` with `src/shortener/templates/delete.html` (states the code will
  never be reused and its click history is removed; "Delete" and "Cancel" buttons) and
  `POST /links/{code}/disable`, `/enable`, `/delete`; every handler returns 404 via
  `visitor_not_found.html` when the link is not owned (makes T030 pass).

**Checkpoint**: US1 + US2 work independently; `pytest` green.

---

## Phase 5: User Story 3 - Set an expiry date (Priority: P3)

**Goal**: Optional expiry on create and later; expired links show "link expired".

**Independent Test**: A link with expiry in the past (set via the clock or DB) gives 410; a
future expiry still redirects; removing expiry restores redirects.

### Tests for User Story 3 (write first, must FAIL) ⚠️

- [X] T034 [P] [US3] Write `tests/unit/test_expiry.py` for `links.parse_local_expiry(value,
  time_zone, now)`: `""` → `None`; `"2026-12-01T09:30"` in `Asia/Colombo` →
  `2026-12-01T04:00:00Z`; a value ≤ `now` raises `ExpiryError("Choose a time in the
  future.")`; malformed text raises `ExpiryError` with a plain message.
- [X] T035 [P] [US3] Write `tests/integration/test_us3_expiry.py` covering spec US3
  scenarios:
  1. Create with a future `expires_at` → visitor gets 302.
  2. A link whose stored `expires_at` is in the past → visitor gets 410 page containing
     "This link has expired"; no redirect.
  3. Setting a past expiry on create or via `POST /links/{code}/expiry` → 400 with "Choose a
     time in the future."; nothing changed.
  4. On an expired link, `POST /links/{code}/expiry` with a future value, or with an empty
     value (remove), → visitor gets 302 again.
  5. A link both disabled and expired → visitor gets 403 "This link is disabled".
  6. The link list and detail page show status "Expired" and the expiry in the user's time
     zone.

### Implementation for User Story 3

- [X] T036 [US3] Add to `src/shortener/links.py`: `ExpiryError`, `parse_local_expiry(value,
  time_zone, now)` (parse `YYYY-MM-DDTHH:MM`, attach `ZoneInfo(time_zone)`, convert to UTC,
  must be > now), `set_expiry(conn, user_id, code, expires_at)`; make `create_link` accept and
  store `expires_at` (makes T034 pass).
- [X] T037 [US3] Extend `src/shortener/web/redirect.py`: when `status` is `"expired"` render
  `src/shortener/templates/visitor_expired.html` ("This link has expired" + "The owner set it
  to stop working on <date>.") with 410. Disabled check stays first.
- [X] T038 [US3] Extend `src/shortener/web/links.py` and templates: optional "Expires"
  `datetime-local` field on `home.html` with a hint "Leave empty to keep the link working";
  expiry form on `link.html` (set/change/remove) posting to `POST /links/{code}/expiry`;
  show expiry dates in the user's time zone with the zone name (makes T035 pass).

**Checkpoint**: US1–US3 work independently; `pytest` green.

---

## Phase 6: User Story 4 - See how my links perform (Priority: P4)

**Goal**: Each redirect counts once; owners see total clicks and a 30-day per-day table in
their saved time zone.

**Independent Test**: Open a link N times; total and today increase by exactly N; other days
show 0.

### Tests for User Story 4 (write first, must FAIL) ⚠️

- [X] T039 [P] [US4] Write `tests/unit/test_clicks.py`:
  - `record_click(conn, code, owner_time_zone, now)` creates `(code, day, 1)` then increments
    to 2 on the same day; `day` is the date in the owner's zone (e.g. `now =
    2026-11-17T20:00:00Z`, zone `Asia/Colombo` → day `2026-11-18`).
  - `total_clicks(conn, code)` sums all rows; 0 when none.
  - `last_30_days(conn, code, owner_time_zone, now)` returns exactly 30 `(date, count)` pairs
    from today−29 to today in the owner's zone, oldest first, zeros filled, including days
    before the link existed.
- [X] T040 [P] [US4] Write `tests/integration/test_us4_stats.py` covering spec US4
  scenarios:
  1. 5 visitor redirects today and 3 rows for yesterday inserted directly → detail page shows
     total 8, today 5, yesterday 3, the other 28 days 0, and names the time zone ("Days shown
     in Asia/Colombo").
  2. Visits to a disabled, an expired, and an unknown code add no clicks.
  3. Deleting a link removes its `daily_clicks` rows.
  4. When `record_click` raises (monkeypatched), `GET /{code}` still returns 302 and an
     `ERROR` log record containing the code is emitted (FR-018a; use `caplog`).
  5. Signing in with a new `time_zone` updates the owner's zone; the next click is stored
     under that zone's date.

### Implementation for User Story 4

- [X] T041 [US4] Implement `src/shortener/clicks.py`: `record_click` (single upsert from
  data-model.md), `total_clicks`, `last_30_days` (one range query `day BETWEEN start AND
  today`, then fill missing dates) (makes T039 pass).
- [X] T042 [US4] Extend `src/shortener/web/redirect.py`: on the 302 path only, add a
  `BackgroundTasks` task `_record_click_safely(db_path, code, time_zone, now)` that opens
  its own connection, calls `record_click`, and on any exception logs
  `logger.exception("click not recorded for code %s", code)` without re-raising.
- [X] T043 [US4] Extend `src/shortener/web/links.py` and `src/shortener/templates/link.html`:
  show "Total clicks" and a 30-row table (date, count, a CSS bar whose width is count ÷ the
  30-day max, with the number always visible as text), caption "Clicks per day, last 30 days.
  Days shown in <zone>." (makes T040 pass).

**Checkpoint**: All four stories work independently; `pytest` green.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 [P] Write `tests/perf/test_redirect_latency.py` (marker `perf`): seed 1,000,000
  links into a temp DB with `executemany` in one transaction (one user; codes from
  `generate_code` collected into a `set` until it holds exactly 1,000,000 distinct codes, so
  a random duplicate can never break the insert; matching `issued_codes` rows); start `uvicorn` for `create_app` on a
  free port in a subprocess; with `httpx` send 50 requests/second for 30 seconds to random
  existing codes (`follow_redirects=False`); parse `Server-Timing` durations; assert p95 <
  50 ms and every response is 302 (SC-001).
- [X] T045 Run `pytest -m perf`; if p95 ≥ 50 ms, profile and fix within the redirect path
  only, then re-run.
- [X] T046 [P] Review all templates in `src/shortener/templates/` against Constitution V:
  remove any decorative element, emoji, gradient, or filler copy; confirm every error message
  says what went wrong and how to fix it (Constitution III).
- [X] T047 [P] Accessibility check of `src/shortener/templates/` and
  `src/shortener/static/style.css`: every input has a `<label>`; focus order follows reading
  order; `:focus-visible` visible; text contrast ≥ 4.5:1; no horizontal scroll at 320 px.
- [X] T048 Run `ruff format . && ruff check .` with zero warnings and remove any dead or
  commented-out code (Constitution II).
- [X] T049 Execute every step in `specs/001-url-shortener/quickstart.md` "Manual
  validation" and record pass/fail in the PR description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup; blocks all stories.
- **US1 (Phase 3)**: after Foundational.
- **US2 (Phase 4)**, **US3 (Phase 5)**, **US4 (Phase 6)**: after Foundational and US1, because
  they extend `links.py`, `web/links.py`, `web/redirect.py`, and the templates created in US1.
  Between themselves they are independent and can be done in any order, but they touch the
  same files, so do them one at a time.
- **Polish (Phase 7)**: after the stories you intend to ship.

### Within Each Phase

- Test tasks first; run them and see them FAIL (Constitution I).
- Then implementation in the listed order; each implementation task names the tests it makes
  pass.
- Commit after each green step.

### Task-level dependencies worth noting

- T004 before every other test task (shared fixtures). Browser tests use their own
  fixtures in `tests/browser/conftest.py`, created in T016.
- T016's browser test can be written early but only passes after T017 (sign-up page);
  T028's browser test needs T016's fixtures and T027's pages.
- T011 → T012 → T013 → T014 → T017.
- T023 and T024 → T025 → T026 → T027 → T028.
- T026 must register the `/{code}` router last so app routes win.
- T031 before T032/T033; T036 before T037/T038; T041 before T042/T043.

## Parallel Opportunities

- Phase 2 tests T005–T009 in parallel; T015 and T016 in parallel with T010–T014.
- US1 tests T018–T022 in parallel; then T023 and T024 in parallel.
- US2 tests T029–T030, US3 tests T034–T035, US4 tests T039–T040 each in parallel.
- Polish T044, T046, T047 in parallel.

### Parallel Example: User Story 1

```bash
# Write all US1 tests together (all must fail):
Task: "Write tests/unit/test_codes.py"          # T018
Task: "Write tests/unit/test_urls.py"           # T019
Task: "Write tests/unit/test_routes.py"         # T020
Task: "Write tests/unit/test_rate_limit.py"     # T021
Task: "Write tests/integration/test_us1_shorten.py"  # T022

# Then the two independent modules together:
Task: "Implement src/shortener/codes.py"        # T023
Task: "Implement src/shortener/urls.py"         # T024
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 3 (US1).
3. **Stop and validate**: quickstart steps 1–3; `pytest` green. This is a usable shortener.

### Incremental Delivery

1. MVP (US1).
2. US2 → manage and isolate links → validate quickstart steps 4–6.
3. US3 → expiry → validate step 7.
4. US4 → clicks → validate step 8.
5. Polish → performance (SC-001), accessibility, quickstart step 9.

## Notes

- [P] = different files, no dependency on unfinished tasks.
- Never mark a test task done until it has been seen failing for the right reason.
- Do not add features, options, or abstractions not listed here (Constitution IV).

---

## Phase 8: Convergence

- [X] T050 CRITICAL: Write a failing test in `tests/integration/test_error_pages.py` asserting `GET /links/abc/xyz` and `GET /account/nope` return 404 HTML containing "Link not found" (not JSON) and `PUT /` returns 405 HTML with a plain sentence such as "This page can't be used that way."; then add `StarletteHTTPException` handling in `src/shortener/main.py` that renders `templates/visitor_not_found.html` for 404 and a new `src/shortener/templates/error.html` for other statuses per Constitution III / FR-021 (contradicts)
- [X] T051 CRITICAL: Write failing tests that (a) force `codes.issue_code` to raise `CodeExhaustedError` and assert `POST /links` re-renders the form with HTTP 503 and "We couldn't create a short link just now. Please try again." with nothing stored, and (b) assert an unexpected exception in a route returns a 500 HTML page with a plain message and is logged at ERROR; then catch `CodeExhaustedError` in `src/shortener/web/links.py` and add a 500 handler rendering `src/shortener/templates/error.html` in `src/shortener/main.py` per Constitution III (contradicts)
- [X] T052 Record the actual structure in `specs/001-url-shortener/plan.md`: add `web/deps.py` (connection, current-user and render helpers, separate from `main.py` to avoid a circular import) to the Project Structure tree, and state that the app starts with `uvicorn shortener.main:create_app --factory` (no module-level `app`) per plan: Project Structure / T014 (contradicts)

---

## Phase 9: Convergence

- [X] T053 CRITICAL: Add a failing case to `tests/unit/test_expiry.py` asserting `parse_local_expiry("9999-12-31T23:59", "Pacific/Pago_Pago", now)` raises `ExpiryError("Choose a date before the year 9999.")` (it currently raises `OverflowError`, which shows the generic 500 page), plus an integration case in `tests/integration/test_us3_expiry.py` asserting `POST /links/{code}/expiry` with that value returns 400 with the message; then catch `OverflowError` in `parse_local_expiry` in `src/shortener/links.py` per Constitution III / FR-016 (contradicts)

---

## Phase 10: Convergence

- [X] T054 CRITICAL: Add failing tests — unit: `parse_local_expiry("9999-06-01T00:00", "UTC", now)` raises `ExpiryError("Choose a date before the year 9999.")`; integration in `tests/integration/test_us3_expiry.py`: a UTC owner's link with `expires_at = '9999-12-31T23:59:00Z'` stored directly, owner then signs in with `time_zone=Pacific/Kiritimati`, and `GET /` and `GET /links/{code}` must return 200 (they currently return 500 because converting to UTC+14 passes year 9999) — then make `parse_local_expiry` in `src/shortener/links.py` reject any local year ≥ 9999 (matching the existing message), and clamp display of stored expiries in `src/shortener/web/links.py` and `src/shortener/web/redirect.py` so a conversion overflow falls back to showing the UTC value with "UTC" named, per Constitution III / FR-014 / FR-016 (contradicts)
