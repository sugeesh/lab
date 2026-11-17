# Quickstart & Validation: URL Shortener

Use this guide to run the app and confirm each user story works. Routes are in
[contracts/http-routes.md](contracts/http-routes.md); tables in [data-model.md](data-model.md).

## Prerequisites

- Python 3.12 or newer (`python3 --version`)
- A Linux or macOS host with the system time-zone database (`/usr/share/zoneinfo`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium               # headless browser for tests/browser/
```

## Run the checks

```bash
ruff format --check . && ruff check .     # zero warnings (Constitution II)
pytest                                     # unit + integration + browser
pytest -m perf                             # 1M-link latency test (slow, on demand)
```

## Run the app

```bash
SHORTENER_DB=./shortener.db SHORTENER_BASE_URL=http://localhost:8000 \
  uvicorn shortener.main:create_app --factory --port 8000
```

Open <http://localhost:8000>.

## Manual validation

| # | Story | Steps | Expected |
|---|-------|-------|----------|
| 1 | US1 | Sign up, paste `https://example.com/some/long/path`, submit | Short link `http://localhost:8000/XXXXXXX` (7 chars) with a Copy button that confirms "Copied" |
| 2 | US1 | Open the short link in a private window | Lands on `https://example.com/some/long/path` |
| 3 | US1 | Submit `ftp://x`, then `http://localhost:8000/abcdefg` | Each refused with a specific message; no link created |
| 4 | US2 | Sign up a second account in another browser | Its list is empty; opening `/links/<first user's code>` shows "Link not found" |
| 5 | US2 | Disable the link, open the short link; enable it, open again | "This link is disabled" page, then a redirect |
| 6 | US2 | Delete the link, open the short link | "Link not found" |
| 7 | US3 | Create a link expiring 2 minutes from now; open before and after | Redirect, then "This link has expired" |
| 8 | US4 | Open an active link 3 times, view its detail page | Total = 3, today = 3, other 29 days = 0, time zone named |
| 9 | Keyboard | Repeat steps 1 and 5 using only the keyboard, at 320 px width | All actions reachable, no horizontal scroll |

## Performance check (SC-001)

`pytest -m perf` seeds 1,000,000 links into a temporary database, starts the server, sends
50 redirects/second for 30 seconds, and reads `Server-Timing` from each response.
Pass: p95 < 50 ms.
