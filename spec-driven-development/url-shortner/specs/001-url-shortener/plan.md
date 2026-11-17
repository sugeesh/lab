# Implementation Plan: URL Shortener

**Branch**: `001-url-shortener` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-url-shortener/spec.md`

## Summary

Signed-in users shorten http/https addresses into 7-character random codes that are never
reused; anyone opening a short link is redirected unless it is disabled, expired, or deleted.
Owners manage only their own links and see total clicks plus clicks per day for 30 days.

Technical approach: a single FastAPI service rendering HTML with Jinja2, SQLite via the
standard-library `sqlite3`, tests in pytest. Codes come from `secrets` and are retried on
collision against a permanent `issued_codes` table. Clicks are one row per link per day,
upserted after the redirect response is sent, with days in the owner's saved time zone.
The redirect path is one primary-key lookup, which keeps p95 far below 50 ms at 50 requests/s
with 1M links. Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 minimum (`requires-python >=3.12`, ruff targets py312);
runs on newer versions such as the 3.14 installed on the development machine

**Primary Dependencies**: FastAPI, uvicorn, Jinja2, python-multipart. Dev: pytest, httpx, ruff

**Storage**: SQLite (single file, WAL mode) via standard-library `sqlite3`; no ORM

**Testing**: pytest with FastAPI `TestClient`; pytest-playwright (headless Chromium) for the
browser script `app.js` (`browser` marker); `perf` marker for the 1M-link latency test

**Target Platform**: Linux server (system tz database for `zoneinfo`)

**Project Type**: Web service with server-rendered pages (single project)

**Performance Goals**: 95% of redirects < 50 ms server time at 50 redirects/s sustained (SC-001)

**Constraints**: Click recording never delays or blocks a redirect (FR-018a); codes never
reused (FR-006); max 100 link creations per user per rolling hour (FR-007a)

**Scale/Scope**: 1M stored links; ~8 HTML pages; 5 tables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|-----------|------|------------|-------------|
| I. TDD | Every behavior has a failing test first; tasks order tests before code; regression tests for bugs | ✅ pytest + `TestClient` lets every FR be tested via HTTP; `/speckit-tasks` will put test tasks first | ✅ Contract lists exact status codes and pages per FR — each maps to a test |
| II. Clean Code | Formatter + linter with zero warnings; small single-purpose modules | ✅ ruff for both | ✅ One module per concern (codes, urls, accounts, links, clicks, web) |
| III. Usability | Few steps, specific errors, keyboard, WCAG AA, 320 px | ✅ Shorten = paste + Enter; copy button | ✅ Every error case in the contract has a specific message; quickstart step 9 checks keyboard and 320 px |
| IV. YAGNI | Only spec'd features; no speculative abstractions; deps justified | ✅ No ORM, no SPA, no cache, no migrations tool | ✅ 4 runtime deps, each with a current need (research §12); no repository/interface layers. One extra dev tool (pytest-playwright) justified in Complexity Tracking |
| V. Human-Crafted UI | No gradients/emoji/sparkles/filler copy; one token set | ✅ Plain forms and tables | ✅ research §13 defines tokens; stats chart is a plain table with CSS bars |

**Result**: Pass. One justified addition recorded in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-url-shortener/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and rationale
├── data-model.md        # Phase 1: tables, rules, state transitions
├── quickstart.md        # Phase 1: run + validation guide
├── contracts/
│   └── http-routes.md   # Phase 1: routes, form fields, status codes
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
pyproject.toml
src/shortener/
├── main.py            # create_app() factory, Server-Timing middleware, error pages, routes
├── config.py          # settings from env: DB path, base URL
├── db.py              # connection with pragmas, schema bootstrap
├── schema.sql         # CREATE TABLE IF NOT EXISTS ... (data-model.md)
├── codes.py           # random 7-char code generation + collision retry
├── urls.py            # target URL validation (FR-004)
├── accounts.py        # sign-up, password hashing, sessions, current user
├── links.py           # create, list, enable/disable, expiry, delete, status, rate limit
├── clicks.py          # record click (upsert), totals, 30-day series
├── web/
│   ├── deps.py        # per-request connection, current user, render(); kept out of main.py
│   │                  # so route modules can import it without a circular import
│   ├── redirect.py    # GET /{code}
│   ├── account.py     # /account/*
│   └── links.py       # /, /links/*
├── templates/         # Jinja2 pages: base, signin, signup, home, link, delete, visitor pages
└── static/
    ├── style.css      # design tokens + layout
    └── app.js         # copy button, time-zone detection

tests/
├── conftest.py        # temp DB, app + TestClient, signed-in client fixtures
├── unit/              # codes, urls, status, passwords, day bucketing, route-collision rule
├── integration/       # one file per user story, via HTTP
├── browser/           # app.js in headless Chromium: time-zone detection, copy button
└── perf/
    └── test_redirect_latency.py   # 1M links, 50 req/s, p95 < 50 ms (marker: perf)
```

**Run command**: `uvicorn shortener.main:create_app --factory`. There is no module-level `app`,
so importing `shortener.main` (as the tests do) never creates a database file.

**Structure Decision**: Single project. The service renders its own pages, so there is no
separate frontend. Business logic lives in plain functions under `src/shortener/` taking a
`sqlite3.Connection`. `web/` only parses requests and renders templates. Integration tests go
through HTTP so they check the contract in
[contracts/http-routes.md](contracts/http-routes.md).

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| pytest-playwright + headless Chromium (dev only) for `tests/browser/` | `app.js` holds production behavior (time-zone detection for FR-019, copy button for FR-007). Constitution I requires a test that fails if that code breaks; `TestClient` does not run JavaScript. | Asserting markup only (e.g. `data-copy-target` present) passes even if `app.js` is deleted. A Node + jsdom runner adds a second language toolchain and has no real clipboard or time-zone emulation. Removing the script would drop the one-click copy that FR-007 requires. |
