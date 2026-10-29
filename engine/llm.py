"""
LLM abstraction layer for Hew.
Uses the official google.genai SDK directly with tool calling support.
"""
import os
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from engine import db
from engine.tools import HEW_TOOLS

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def get_api_key() -> str:
    """Reads GEMINI_API_KEY from environment or local .env file."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise ValueError("GEMINI_API_KEY not found! Please check your .env file.")


def get_client() -> genai.Client:
    return genai.Client(api_key=get_api_key())


def build_context_snapshot() -> str:
    """Extracts state from SQLite to give the AI eyes on reality."""
    now = datetime.now().astimezone().strftime("%A, %B %d, %Y at %I:%M %p")

    # Goals
    goals = db.get_active_goals()
    goals_text = "\n".join([f"- [ID:{g['id']} | P{g['priority']}] {g['title']}" for g in goals]) or "No active goals set."

   # Today's commitments (with linked Goals)
    today = datetime.now().strftime("%Y-%m-%d")
    with db.connect() as conn:
        commitments = conn.execute(
            """SELECT c.*, g.title as goal_title 
               FROM commitments c 
               LEFT JOIN goals g ON c.goal_id = g.id 
               WHERE c.scheduled_date = ? AND c.status != 'dropped'""", 
            (today,)
        ).fetchall()
    
    commitments_text = "\n".join([
        f"- [ID:{c['id']}] {c['title']} ({c['scheduled_time'] or 'anytime'})" + 
        (f" -> Serves Goal: '{c['goal_title']}'" if c['goal_title'] else " (Standalone task)")
        for c in commitments
    ]) or "None scheduled."
    
    # Recent Events
    events = db.recent_events(5)
    events_text = "\n".join([f"- {e['kind']} at {e['ts']}" for e in events]) or "No recent events recorded."

    return f"""CURRENT TIME: {now}

STATE OF THE MIRROR:
Active Goals:
{goals_text}

Today's Commitments ({today}):
{commitments_text}

Recent Activity:
{events_text}
"""


def call_llm(user_message: str) -> str:
    """Sends prompt, tools, and short-term memory to Gemini."""
    client = get_client()
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    # 1. Build the state of the Mirror
    context = build_context_snapshot()
    
    # 2. Build Short-Term Memory (The Transcript)
    # Fetch recent messages. (web.py logs the current user_message right before calling this, 
    # so we slice off the very last message to avoid echoing it to Hew twice).
    history_rows = db.get_chat_history(9)
    if history_rows and history_rows[-1]["content"] == user_message:
        history_rows = history_rows[:-1] 
        
    transcript = "\n".join([
        f"{'User' if m['role'] == 'user' else 'Hew'}: {m['content']}" 
        for m in history_rows
    ]) or "No prior conversation."

    # 3. Assemble the Master Prompt
    system_instruction = (
        "You are Hew, an executive personal intelligence system inspired by J.A.R.V.I.S.\n\n"
        "Persona & Tone:\n"
        "- Formal, articulate, composed, and unfailingly polite, reminiscent of a refined British butler.\n"
        "- Dry wit and subtle understatement are welcome, but maintain calm professionalism at all times.\n"
        "- Be concise and direct. Avoid excessive pleasantries, hype, or preachy speeches.\n"
        "- Present situational awareness grounded strictly in what you observe in the Mirror.\n"
        "- You have continuous conversational awareness. You can see recent dialogue under RECENT CONVERSATION HISTORY and should maintain context across turns.\n\n"
        "Capabilities & Tools:\n"
        "- You have tools to create goals, schedule commitments, and log sleep directly into the database.\n"
        "- Whenever the user indicates a new objective, deadline, task, or sleep cycle, invoke the relevant tool immediately.\n\n"
        f"{context}\n\n"
        "RECENT CONVERSATION HISTORY:\n"
        f"{transcript}"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=HEW_TOOLS,
                temperature=0.4,
                max_output_tokens=400,
            ),
        )
        return response.text.strip() if response.text else "Directive executed, sir."
    except Exception as e:
        return f"[Error connecting to Gemini]: {e}"