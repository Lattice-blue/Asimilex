import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mirror" / "asimilex.db"


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
             id INTEGER PRIMARY KEY,
             ts TEXT NOT NULL,           -- when it happened
             kind TEXT NOT NULL,         -- 'went_to_bed', 'woke_up'
             source TEXT NOT NULL DEFAULT 'ui',
             recorded_at TEXT NOT NULL   -- when the system heard about it
           )"""
    )
    return conn


def log_event(kind, ts=None, source="ui"):
    now = datetime.now().astimezone()
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (ts, kind, source, recorded_at) VALUES (?, ?, ?, ?)",
            ((ts or now).isoformat(), kind, source, now.isoformat()),
        )


def recent_events(limit=10):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()


def delete_event(event_id):
    with connect() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))