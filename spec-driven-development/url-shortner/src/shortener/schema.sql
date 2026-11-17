CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    time_zone TEXT NOT NULL DEFAULT 'UTC',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);

-- Rows are never deleted: this is what guarantees a code is never reused.
CREATE TABLE IF NOT EXISTS issued_codes (
    code TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    issued_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS issued_codes_by_user_time ON issued_codes (user_id, issued_at);

CREATE TABLE IF NOT EXISTS links (
    code TEXT PRIMARY KEY REFERENCES issued_codes(code),
    user_id INTEGER NOT NULL REFERENCES users(id),
    target_url TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS links_by_user_newest ON links (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS daily_clicks (
    code TEXT NOT NULL REFERENCES links(code) ON DELETE CASCADE,
    day TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (code, day)
);
