import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mirror" / "asimilex.db"


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 1. History data (append-only)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
             id INTEGER PRIMARY KEY,
             ts TEXT NOT NULL,           
             kind TEXT NOT NULL,         
             source TEXT NOT NULL DEFAULT 'ui',
             recorded_at TEXT NOT NULL   
           )"""
    )
    
    # 2. State data (updated in place)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS goals (
             id INTEGER PRIMARY KEY,
             title TEXT NOT NULL,
             why TEXT,
             deadline TEXT,
             priority INTEGER DEFAULT 3,      -- 1 = most important
             status TEXT DEFAULT 'active',    -- 'active', 'completed', 'dropped'
             created_at TEXT NOT NULL
           )"""
    )
    return conn


# --- EVENTS (History) ---

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


# --- GOALS (State) ---

def add_goal(title, why="", deadline="", priority=3):
    now = datetime.now().astimezone().isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO goals (title, why, deadline, priority, status, created_at) VALUES (?, ?, ?, ?, 'active', ?)",
            (title, why, deadline, priority, now),
        )

def get_active_goals():
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM goals WHERE status = 'active' ORDER BY priority ASC, created_at DESC"
        ).fetchall()

def update_goal_status(goal_id, status):
    # We update status rather than delete, so the engine can reflect on achieved goals later!
    with connect() as conn:
        conn.execute("UPDATE goals SET status = ? WHERE id = ?", (status, goal_id))