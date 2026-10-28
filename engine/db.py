import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mirror" / "asimilex.db"


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 1. History
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
             id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL,         
             source TEXT NOT NULL DEFAULT 'ui', recorded_at TEXT NOT NULL   
           )"""
    )
    
    # 2. Goals (The Targets)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS goals (
             id INTEGER PRIMARY KEY, title TEXT NOT NULL, why TEXT,
             deadline TEXT, priority INTEGER DEFAULT 3, status TEXT DEFAULT 'active',
             created_at TEXT NOT NULL
           )"""
    )

    # 3. Habits (The Engines)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS habits (
             id INTEGER PRIMARY KEY, goal_id INTEGER, title TEXT NOT NULL,
             frequency TEXT NOT NULL, time_of_day TEXT, duration_mins INTEGER,
             status TEXT DEFAULT 'active', created_by TEXT DEFAULT 'user',
             created_at TEXT NOT NULL, FOREIGN KEY(goal_id) REFERENCES goals(id)
           )"""
    )

    # 4. Commitments (The Stepping Stones)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS commitments (
             id INTEGER PRIMARY KEY, goal_id INTEGER, habit_id INTEGER,
             title TEXT NOT NULL, description TEXT, scheduled_date TEXT NOT NULL,
             scheduled_time TEXT, duration_mins INTEGER, status TEXT DEFAULT 'proposed',
             created_by TEXT DEFAULT 'user', ext_source TEXT, ext_id TEXT,
             created_at TEXT NOT NULL, FOREIGN KEY(goal_id) REFERENCES goals(id),
             FOREIGN KEY(habit_id) REFERENCES habits(id), UNIQUE(ext_source, ext_id)
           )"""
    )

    # 5. Chat History (The Steering Wheel)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS messages (
             id INTEGER PRIMARY KEY, role TEXT NOT NULL, -- 'user' or 'hew'
             content TEXT NOT NULL, timestamp TEXT NOT NULL
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

def log_message(role, content):
    now = datetime.now().astimezone().isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)", (role, content, now))

def get_chat_history(limit=20):
    with connect() as conn:
        # Get the latest X messages, but order them chronologically for the chat UI
        return conn.execute(
            "SELECT * FROM (SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?) ORDER BY timestamp ASC", 
            (limit,)
        ).fetchall()