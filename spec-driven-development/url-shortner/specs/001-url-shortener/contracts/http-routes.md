# HTTP Contract: URL Shortener

All pages are server-rendered HTML. Forms post `application/x-www-form-urlencoded`.
"Signed in" means a valid `session` cookie. When a signed-in route is hit without one, the
response is `303 See Other` to `/account/signin?next=<original path>` for `GET` requests, and
to `/account/signin?next=/` for any other method, since POST-only paths have no page to
return to (edge case: session ends mid-task). Any `{code}` that does not exist **or belongs to another user** returns `404` with
the "link not found" page (FR-003).

Every response carries `Server-Timing: app;dur=<ms>` (used by the performance test).

## Public — short links

| Method | Path | Result |
|--------|------|--------|
| GET | `/{code}` (`[A-Za-z0-9]{7}`) | **302** `Location: <target_url>`, `Cache-Control: no-store`; one click recorded after the response (FR-009, FR-013, FR-018, FR-018a) |
| | | **403** "This link is disabled" page — no click (FR-011) |
| | | **410** "This link has expired" page — no click (FR-010) |
| | | **404** "Link not found" page — unknown or deleted code (FR-012) |

Codes are case-sensitive; `/abcDEF1` and `/ABCdef1` are different links.

## Accounts

| Method | Path | Form fields | Result |
|--------|------|-------------|--------|
| GET | `/account/signup` | — | 200 sign-up form |
| POST | `/account/signup` | `email`, `password`, `time_zone` (from browser) | **303** → `/` with session cookie; **400** form re-shown with specific message (invalid email, password < 8 chars, email already registered) |
| GET | `/account/signin` | — | 200 sign-in form |
| POST | `/account/signin` | `email`, `password`, `time_zone`, `next` | **303** → `next` or `/`, session cookie set, saved time zone updated; **400** "Email or password is incorrect" |
| POST | `/account/signout` | — | **303** → `/account/signin`; session deleted, cookie cleared |

Invalid or missing `time_zone` is stored as `UTC`.

## Links (signed in)

| Method | Path | Form fields | Result |
|--------|------|-------------|--------|
| GET | `/` | — | Signed out: 303 → `/account/signin`. Signed in: 200 page with the shorten form and the user's link list, newest first (FR-014) |
| POST | `/links` | `url`, `expires_at` (optional, `YYYY-MM-DDTHH:MM` in the owner's saved time zone) | **303** → `/links/{code}` showing the new short link and copy button (FR-007); **400** form re-shown with message (invalid URL, too long, points to this service, expiry in the past or in year 9999 or later); **429** "You've created 100 links in the last hour. You can create more at HH:MM." (FR-007a); **503** "We couldn't create a short link just now. Please try again." when no unused code is found after 5 tries |
| GET | `/links/{code}` | — | 200 link detail: short link + copy button, target, status, expiry form, enable/disable, delete, total clicks, 30-day table with stated time zone (FR-019) |
| POST | `/links/{code}/disable` | — | **303** → `/links/{code}` (FR-015) |
| POST | `/links/{code}/enable` | — | **303** → `/links/{code}` (FR-015) |
| POST | `/links/{code}/expiry` | `expires_at` (empty = remove) | **303** → `/links/{code}`; **400** if in the past or in year 9999 or later (FR-016) |
| GET | `/links/{code}/delete` | — | 200 confirmation page (FR-017) |
| POST | `/links/{code}/delete` | — | **303** → `/`; link and its clicks removed, code never reissued (FR-006, FR-017) |

`expires_at` is interpreted in the owner's saved time zone (the zone every date on the page is
shown in, and named next to the field) and stored as UTC.

## Error pages

Every error is a plain HTML page, never JSON (Constitution III): any unmatched path → **404**
"Link not found"; a wrong method → **405** "This page can't be used that way."; an unexpected
failure → **500** "a problem on our side" page, with the exception logged at `ERROR`.

## Static

| Method | Path | Result |
|--------|------|--------|
| GET | `/static/style.css`, `/static/app.js` | 200 |

## Route-collision rule

No app route may consist of a single path segment of exactly 7 alphanumeric characters, so a
generated code can never shadow an app page. Enforced by a unit test over the route table.
