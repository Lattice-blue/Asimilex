"""
Tools (Hands) for Hew.
These functions are directly invoked by Gemini to alter the Mirror.
"""
from datetime import datetime
from engine import db


def create_goal(title: str, priority: int = 3, deadline: str = "", why: str = "") -> str:
    """Creates a new high-level objective or goal for the user."""
    try:
        db.add_goal(title=title, why=why, deadline=deadline, priority=int(priority))
        return f"[Success] Logged goal '{title}' under Priority {priority}."
    except Exception as e:
        return f"[Error] Failed to create goal: {e}"


def schedule_commitment(title: str, scheduled_date: str, scheduled_time: str = "", duration_mins: int = 60, notes: str = "") -> str:
    """Schedules an actionable task, study block, or event for a specific date/time."""
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            conn.execute(
                """INSERT INTO commitments 
                   (title, description, scheduled_date, scheduled_time, duration_mins, status, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, 'active', 'ai', ?)""",
                (title, notes, scheduled_date, scheduled_time or None, duration_mins, now)
            )
        time_str = f" at {scheduled_time}" if scheduled_time else ""
        return f"[Success] Scheduled commitment '{title}' for {scheduled_date}{time_str} ({duration_mins} mins)."
    except Exception as e:
        return f"[Error] Failed to schedule commitment: {e}"


def complete_commitment(task_name_or_id: str) -> str:
    """
    Marks an active commitment or task as completed when the user finishes it.
    
    Args:
        task_name_or_id: The ID of the task or keywords from the title (e.g. 'Calculus' or '3').
    """
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            # Check by ID first
            if str(task_name_or_id).isdigit():
                cur = conn.execute("UPDATE commitments SET status = 'completed' WHERE id = ?", (int(task_name_or_id),))
            else:
                # Search by title match
                cur = conn.execute(
                    "UPDATE commitments SET status = 'completed' WHERE title LIKE ? AND status = 'active'", 
                    (f"%{task_name_or_id}%",)
                )
            
            if cur.rowcount > 0:
                # Log completion to events history (Derived Adherence!)
                conn.execute(
                    "INSERT INTO events (ts, kind, source, recorded_at) VALUES (?, ?, 'ai', ?)",
                    (now, f"completed_task: {task_name_or_id}", now)
                )
                return f"[Success] Marked task '{task_name_or_id}' as completed."
            return f"[Notice] No active task matching '{task_name_or_id}' was found."
    except Exception as e:
        return f"[Error] Could not complete task: {e}"


def reschedule_commitment(task_name_or_id: str, new_date: str, new_time: str = "") -> str:
    """
    Moves an existing commitment to a new date or time when life gets delayed.
    
    Args:
        task_name_or_id: Task ID or keyword from the title.
        new_date: New date in YYYY-MM-DD format.
        new_time: Optional new 24-hr time in HH:MM format.
    """
    try:
        with db.connect() as conn:
            if str(task_name_or_id).isdigit():
                cur = conn.execute(
                    "UPDATE commitments SET scheduled_date = ?, scheduled_time = ? WHERE id = ?",
                    (new_date, new_time or None, int(task_name_or_id))
                )
            else:
                cur = conn.execute(
                    "UPDATE commitments SET scheduled_date = ?, scheduled_time = ? WHERE title LIKE ? AND status = 'active'",
                    (new_date, new_time or None, f"%{task_name_or_id}%")
                )
                
            if cur.rowcount > 0:
                time_str = f" at {new_time}" if new_time else ""
                return f"[Success] Rescheduled '{task_name_or_id}' to {new_date}{time_str}."
            return f"[Notice] No active task matching '{task_name_or_id}' found to reschedule."
    except Exception as e:
        return f"[Error] Could not reschedule task: {e}"


def log_sleep(went_to_bed: str, woke_up: str, note: str = "") -> str:
    """Logs a sleep session when the user reports their sleep cycle."""
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            conn.execute("INSERT INTO events (ts, kind, source, recorded_at) VALUES (?, 'went_to_bed', 'ai', ?)", (went_to_bed, now))
            conn.execute("INSERT INTO events (ts, kind, source, recorded_at) VALUES (?, 'woke_up', 'ai', ?)", (woke_up, now))
        return f"[Success] Recorded sleep cycle: {went_to_bed} to {woke_up}."
    except Exception as e:
        return f"[Error] Failed to log sleep: {e}"


# All tools given to Gemini
HEW_TOOLS = [
    create_goal,
    schedule_commitment,
    complete_commitment,
    reschedule_commitment,
    log_sleep,
]