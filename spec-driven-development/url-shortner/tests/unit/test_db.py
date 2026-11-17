from shortener import db

TABLES = {"users", "sessions", "issued_codes", "links", "daily_clicks"}


def table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def test_connect_sets_pragmas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))

    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_init_schema_creates_all_tables_and_is_idempotent(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))

    db.init_schema(conn)
    db.init_schema(conn)

    assert table_names(conn) >= TABLES
