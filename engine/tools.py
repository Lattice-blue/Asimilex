"""
Tools Registry for Hew.
Combines Database Hands with Sight Optics.
"""
from datetime import datetime
from engine import db
from engine.sight import SIGHT_TOOLS


# =============================================================================
# DATABASE TOOLS (HANDS)
# =============================================================================

def create_goal(title: str, priority: int = 3, deadline: str = "", why: str = "") -> str:
    """Creates a new high-level objective or goal for the user."""
    try:
        db.add_goal(title=title, why=why, deadline=deadline, priority=int(priority))
        return f"[Success] Logged goal '{title}' under Priority {priority}."
    except Exception as e:
        return f"[Error] Failed to create goal: {e}"


def schedule_commitment(title: str, scheduled_date: str, scheduled_time: str = "", duration_mins: int = 60, notes: str = "", goal_id: int = None) -> str:
    """Schedules an actionable task, study block, or event for a specific date/time."""
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            conn.execute(
                """INSERT INTO commitments 
                   (goal_id, title, description, scheduled_date, scheduled_time, duration_mins, status, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', 'ai', ?)""",
                (goal_id or None, title, notes, scheduled_date, scheduled_time or None, duration_mins, now)
            )
        time_str = f" at {scheduled_time}" if scheduled_time else ""
        goal_str = f" [Linked to Goal #{goal_id}]" if goal_id else ""
        return f"[Success] Scheduled commitment '{title}' for {scheduled_date}{time_str} ({duration_mins} mins){goal_str}."
    except Exception as e:
        return f"[Error] Failed to schedule commitment: {e}"


def complete_commitment(task_name_or_id: str) -> str:
    """Marks an active commitment or task as completed when finished."""
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            if str(task_name_or_id).isdigit():
                cur = conn.execute("UPDATE commitments SET status = 'completed' WHERE id = ?", (int(task_name_or_id),))
            else:
                cur = conn.execute(
                    "UPDATE commitments SET status = 'completed' WHERE title LIKE ? AND status = 'active'", 
                    (f"%{task_name_or_id}%",)
                )
            
            if cur.rowcount > 0:
                conn.execute(
                    "INSERT INTO events (ts, kind, source, recorded_at) VALUES (?, ?, 'ai', ?)",
                    (now, f"completed_task: {task_name_or_id}", now)
                )
                return f"[Success] Marked task '{task_name_or_id}' as completed."
            return f"[Notice] No active task matching '{task_name_or_id}' was found."
    except Exception as e:
        return f"[Error] Could not complete task: {e}"


def reschedule_commitment(task_name_or_id: str, new_date: str, new_time: str = "") -> str:
    """Moves an existing commitment to a new date or time."""
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


def create_habit(title: str, frequency: str = "daily", time_of_day: str = "", duration_mins: int = 5, goal_id: int = None) -> str:
    """Creates a recurring habit rule."""
    try:
        now = datetime.now().astimezone().isoformat()
        with db.connect() as conn:
            conn.execute(
                """INSERT INTO habits (goal_id, title, frequency, time_of_day, duration_mins, status, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, 'active', 'ai', ?)""",
                (goal_id or None, title, frequency, time_of_day or None, duration_mins, now)
            )
        return f"[Success] Created {frequency} habit: '{title}'."
    except Exception as e:
        return f"[Error] Failed to create habit: {e}"

# Combined tool registry (Hands + Sight)
HEW_TOOLS = [
    create_goal,
    schedule_commitment,
    complete_commitment,
    reschedule_commitment,
    log_sleep,
    create_habit,
    *SIGHT_TOOLS,  # Injects get_file_tree and read_text
]