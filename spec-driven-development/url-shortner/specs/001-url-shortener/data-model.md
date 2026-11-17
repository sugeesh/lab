# Data Model: URL Shortener

Storage: one SQLite database file. All timestamps are stored as UTC ISO-8601 text
(`YYYY-MM-DDTHH:MM:SSZ`). Connection pragmas: `journal_mode=WAL`, `synchronous=NORMAL`,
`foreign_keys=ON`, `busy_timeout=5000`.

## Entities

### users

| Field | Type | Rules |
|-------|------|-------|
| id | INTEGER PK | auto-assigned |
| email | TEXT | required, unique (case-insensitive: stored lower-cased), contains `@`, ≤ 254 chars |
| password_hash | TEXT | scrypt hash + salt; plain password ≥ 8 chars, never stored |
| time_zone | TEXT | IANA name (e.g. `Asia/Colombo`); must load with `zoneinfo`; default `UTC` |
| created_at | TEXT | UTC timestamp |

Updated: `time_zone` is overwritten at each successful sign-in when the browser reports a valid
zone (FR-019).

### sessions

| Field | Type | Rules |
|-------|------|-------|
| token_hash | TEXT PK | SHA-256 of the cookie token; raw token never stored |
| user_id | INTEGER FK → users.id | ON DELETE CASCADE |
| expires_at | TEXT | created + 14 days |

A session is valid while `expires_at` is in the future. Sign-out deletes the row.

### issued_codes

| Field | Type | Rules |
|-------|------|-------|
| code | TEXT PK | exactly 7 chars from `[A-Za-z0-9]`; case-sensitive |
| user_id | INTEGER FK → users.id | who caused the code to be issued |
| issued_at | TEXT | UTC timestamp |

Index: `(user_id, issued_at)` for the hourly creation limit (FR-007a).
Rows are **never deleted** — this is what guarantees codes are never reused (FR-006, SC-003).

### links

| Field | Type | Rules |
|-------|------|-------|
| code | TEXT PK, FK → issued_codes.code | one link per issued code |
| user_id | INTEGER FK → users.id | owner; every management query filters on it (FR-003) |
| target_url | TEXT | absolute http/https, ≤ 2,048 chars, host ≠ service host (FR-004) |
| enabled | INTEGER | 1 or 0; default 1 |
| expires_at | TEXT NULL | UTC timestamp; must be in the future when set (FR-008, FR-016) |
| created_at | TEXT | UTC timestamp |

Index: `(user_id, created_at DESC)` for the owner's list, newest first (FR-014).
Deleting a link removes the row (and its clicks by cascade); its `issued_codes` row stays.

### daily_clicks

| Field | Type | Rules |
|-------|------|-------|
| code | TEXT FK → links.code | ON DELETE CASCADE |
| day | TEXT | `YYYY-MM-DD` in the owner's time zone at the moment of the click |
| count | INTEGER | ≥ 1 |

Primary key `(code, day)`. Written by one upsert per successful redirect:
`INSERT INTO daily_clicks(code, day, count) VALUES (?, ?, 1)
 ON CONFLICT(code, day) DO UPDATE SET count = count + 1`.

## Relationships

```text
users 1 ──< sessions
users 1 ──< issued_codes 1 ──o| links 1 ──< daily_clicks
users 1 ──< links
```

## Derived values

- **Link status** (FR-014, edge case "disabled and expired"):
  `disabled` if `enabled = 0`; else `expired` if `expires_at` is set and `≤ now (UTC)`;
  else `active`.
- **Total clicks**: `SUM(count)` over the link's `daily_clicks` rows.
- **Last 30 days**: the dates `today − 29 … today` in the owner's time zone; read rows with
  `day BETWEEN start AND today`, fill missing dates with 0.

## State transitions (link)

```text
             create
               │
               ▼
   ┌──────► active ◄──────┐
   │   disable │  ▲ enable│ set future expiry /
   │           ▼  │       │ remove expiry
   │        disabled      │
   │                      │
   └──── expired ─────────┘
        (time passes expires_at)

 any state ── delete ──► (gone; code stays in issued_codes forever)
```

`disabled` takes precedence over `expired` when both apply.

## Redirect lookup (hot path)

```sql
SELECT l.target_url, l.enabled, l.expires_at, u.time_zone
FROM links l JOIN users u ON u.id = l.user_id
WHERE l.code = ?
```

Single primary-key lookup plus a primary-key join; no other query runs before the response.
