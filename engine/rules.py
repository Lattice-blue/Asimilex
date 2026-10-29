"""
Cheap rule-checking loop.
Runs continuously without calling the LLM; detects friction (e.g. sleep debt).
"""

def detect_friction():
    """Returns alerts if habits or deadlines conflict with current state."""
    return []


"""
The Cheap Loop for Hew.
Runs silently to enforce rules, detect friction, and spawn daily habits.
"""
from datetime import datetime
from engine import db

def spawn_daily_habits():
    """Materializes today's commitments from active habit rules."""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().astimezone().isoformat()
    
    with db.connect() as conn:
        habits = conn.execute("SELECT * FROM habits WHERE status = 'active'").fetchall()
        
        for h in habits:
            # Check if this habit was already stamped onto today's schedule
            exists = conn.execute(
                "SELECT id FROM commitments WHERE habit_id = ? AND scheduled_date = ?",
                (h["id"], today)
            ).fetchone()
            
            if not exists:
                conn.execute(
                    """INSERT INTO commitments 
                       (goal_id, habit_id, title, description, scheduled_date, scheduled_time, duration_mins, status, created_by, created_at)
                       VALUES (?, ?, ?, '', ?, ?, ?, 'active', 'system', ?)""",
                    (h["goal_id"], h["id"], h["title"], today, h["time_of_day"], h["duration_mins"], now)
                )