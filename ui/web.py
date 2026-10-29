"""
Web interface for Hew.
Dual-view architecture:
  - /        -> Terminal (Conversational Cockpit)
  - /mirror  -> The Mirror (Goals, Commitments & Telemetry)
"""
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from engine import tools
from engine import db, llm

PORT = 8765

# --- SHARED STYLES ---
NAV_HTML = """
<header>
  <div class="logo">HEW</div>
  <nav>
    <a href="/" class="%ACTIVE_TERMINAL%">Terminal</a>
    <a href="/mirror" class="%ACTIVE_MIRROR%">The Mirror</a>
  </nav>
</header>
"""

BASE_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #0b0c10;
    color: #e0e2ec;
    max-width: 760px;
    margin: 0 auto;
    padding: 1.2rem 1rem;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #1a1d26;
  }
  .logo { font-size: 1.2rem; font-weight: 700; letter-spacing: 0.08em; color: #fff; }
  nav { display: flex; gap: 0.5rem; }
  nav a {
    color: #8b949e;
    text-decoration: none;
    font-size: 0.88rem;
    padding: 0.35rem 0.8rem;
    border-radius: 6px;
    font-weight: 500;
  }
  nav a:hover { color: #fff; background: #161b22; }
  nav a.active { color: #fff; background: #1f293d; border: 1px solid #2f3b52; }
"""

# --- VIEW 1: TERMINAL ---
TERMINAL_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hew | Terminal</title>
<style>
""" + BASE_CSS + """
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.2rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }
  .msg {
    padding: 0.85rem 1.15rem;
    border-radius: 12px;
    line-height: 1.5;
    font-size: 0.95rem;
    max-width: 85%;
    word-wrap: break-word;
  }
  .msg.user {
    align-self: flex-end;
    background: #1e293b;
    color: #f1f5f9;
    border-bottom-right-radius: 3px;
  }
  .msg.hew {
    align-self: flex-start;
    background: #131722;
    border: 1px solid #202637;
    color: #cbd5e1;
    border-bottom-left-radius: 3px;
  }
  .sender {
    font-size: 0.72rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .msg.user .sender { color: #94a3b8; text-align: right; }
  .msg.hew .sender { color: #60a5fa; }
  form.chat-input {
    display: flex;
    gap: 0.6rem;
    padding-top: 0.8rem;
    border-top: 1px solid #1a1d26;
  }
  input[type=text] {
    flex: 1;
    background: #141721;
    border: 1px solid #262c3e;
    color: #fff;
    padding: 0.85rem 1.1rem;
    border-radius: 10px;
    font-size: 1rem;
    outline: none;
  }
  input[type=text]:focus { border-color: #3b82f6; }
  button {
    background: #2563eb;
    color: #fff;
    border: none;
    padding: 0 1.5rem;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
  }
  button:hover { background: #1d4ed8; }
</style></head><body>
""" + NAV_HTML + """
  <div class="chat-container" id="chatbox">%CHAT%</div>
  <form class="chat-input" method="post" action="/chat">
    <input type="text" name="message" placeholder="Directive or query..." autocomplete="off" autofocus required>
    <button type="submit">Send</button>
  </form>
  <script>
    var chatbox = document.getElementById("chatbox");
    chatbox.scrollTop = chatbox.scrollHeight;
  </script>
</body></html>"""

# --- VIEW 2: THE MIRROR ---
MIRROR_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hew | The Mirror</title>
<style>
""" + BASE_CSS + """
  body { height: auto; min-height: 100vh; overflow-y: auto; }
  .mirror-content { padding: 1.5rem 0 3rem; display: flex; flex-direction: column; gap: 2rem; }
  h2 { font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 0.8rem; border-left: 3px solid #3b82f6; padding-left: 0.5rem; }
  .card-grid { display: grid; gap: 0.75rem; }
  .card {
    background: #141721;
    border: 1px solid #1f2537;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .card-title { font-size: 1rem; font-weight: 600; color: #f1f5f9; }
  .card-meta { font-size: 0.82rem; color: #8b949e; margin-top: 0.35rem; display: flex; gap: 0.8rem; flex-wrap: wrap; }
  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .p1 { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
  .p2 { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
  .p3 { background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
  .goal-link { color: #60a5fa; font-weight: 500; }
  .status-active { color: #34d399; }
  .status-completed { color: #60a5fa; text-decoration: line-through; opacity: 0.7; }
  .empty { color: #64748b; font-size: 0.9rem; font-style: italic; }
</style></head><body>
""" + NAV_HTML + """
  <div class="mirror-content">
    <section>
      <h2>Active Goals</h2>
      <div class="card-grid">%GOALS%</div>
    </section>

    <section>
      <h2>Scheduled Commitments</h2>
      <div class="card-grid">%COMMITMENTS%</div>
    </section>
  </div>
</body></html>"""


def render_terminal():
     # 1. Automatically stamp today's habits if any were just created or if it's a new day
    from engine.rules import spawn_daily_habits
    spawn_daily_habits()
    chat_html = ""
    for m in db.get_chat_history(30):
        is_user = m["role"] == "user"
        css_class = "user" if is_user else "hew"
        sender = "You" if is_user else "Hew"
        chat_html += (
            f"<div class='msg {css_class}'>"
            f"<div class='sender'>{sender}</div>"
            f"<div>{escape(m['content'])}</div>"
            f"</div>"
        )
    if not chat_html:
        chat_html = (
            "<div class='msg hew'>"
            "<div class='sender'>Hew</div>"
            "<div>Online and observing the Mirror. How may I assist you this evening, sir?</div>"
            "</div>"
        )

    # --- NEW: Fetch today's uncompleted habits and build the buttons ---
    today = datetime.now().strftime("%Y-%m-%d")
    with db.connect() as conn:
        todays_habits = conn.execute(
            "SELECT id, title FROM commitments WHERE habit_id IS NOT NULL AND scheduled_date = ? AND status = 'active'", 
            (today,)
        ).fetchall()
        
    habit_html = ""
    if todays_habits:
        habit_html = "<div style='display:flex; gap:0.5rem; padding-bottom:1rem; border-bottom:1px solid #1a1d26; overflow-x:auto;'>"
        for h in todays_habits:
            habit_html += f"""
            <form method="post" action="/complete_task" style="margin:0;">
                <input type="hidden" name="id" value="{h['id']}">
                <button type="submit" style="background:#1f293d; color:#e0e2ec; border-radius:20px; font-size:0.85rem; padding:0.4rem 0.8rem; white-space:nowrap; cursor:pointer;">
                    ✅ {escape(h['title'])}
                </button>
            </form>
            """
        habit_html += "</div>"

    return (
        TERMINAL_PAGE
        .replace("%ACTIVE_TERMINAL%", "active")
        .replace("%ACTIVE_MIRROR%", "")
        .replace("%CHAT%", chat_html)
        .replace('<div class="chat-container"', f"{habit_html}<div class=\"chat-container\"")
    )


def render_mirror():
    # 1. Render Goals
    goals = db.get_active_goals()
    goals_html = ""
    for g in goals:
        p_class = f"p{g['priority']}"
        deadline = f"Target: {g['deadline']}" if g['deadline'] else "No deadline"
        why = f" • <em>{escape(g['why'])}</em>" if g['why'] else ""
        goals_html += f"""
        <div class="card">
          <div>
            <div class="card-title">{escape(g['title'])}</div>
            <div class="card-meta">
              <span>{deadline}</span>{why}
            </div>
          </div>
          <span class="badge {p_class}">P{g['priority']}</span>
        </div>"""
    if not goals_html:
        goals_html = "<div class='empty'>No active goals recorded in the Mirror.</div>"

    # 2. Render Commitments (with linked goals)
    with db.connect() as conn:
        commitments = conn.execute(
            """SELECT c.*, g.title as goal_title 
               FROM commitments c 
               LEFT JOIN goals g ON c.goal_id = g.id 
               WHERE c.status != 'dropped'
               ORDER BY c.scheduled_date ASC, c.scheduled_time ASC"""
        ).fetchall()

    commitments_html = ""
    for c in commitments:
        time_display = f"at {c['scheduled_time']}" if c['scheduled_time'] else "anytime"
        duration = f"({c['duration_mins']} mins)" if c['duration_mins'] else ""
        goal_ref = f"<span class='goal-link'>↳ Serves: {escape(c['goal_title'])}</span>" if c['goal_title'] else "<span>Standalone</span>"
        status_class = f"status-{c['status']}"

        commitments_html += f"""
        <div class="card">
          <div>
            <div class="card-title {status_class}">{escape(c['title'])}</div>
            <div class="card-meta">
              <span>📅 {c['scheduled_date']} {time_display} {duration}</span>
              {goal_ref}
            </div>
          </div>
          <span class="badge" style="background:#1f293d; color:#94a3b8;">{c['status']}</span>
        </div>"""
    if not commitments_html:
        commitments_html = "<div class='empty'>No scheduled commitments found.</div>"

    return (
        MIRROR_PAGE
        .replace("%ACTIVE_TERMINAL%", "")
        .replace("%ACTIVE_MIRROR%", "active")
        .replace("%GOALS%", goals_html)
        .replace("%COMMITMENTS%", commitments_html)
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/terminal"):
            body = render_terminal().encode()
        elif self.path == "/mirror":
            body = render_mirror().encode()
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Import tools so the web app can trigger completions
        from engine import tools
        
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        user_msg = form.get("message", [""])[0]

        # 1. Handle Chat Messages
        if self.path == "/chat" and user_msg:
            db.log_message("user", user_msg)
            reply = llm.call_llm(user_msg)
            db.log_message("hew", reply)
            
        # 2. Handle the new Habit Quick-Check button
        elif self.path == "/complete_task" and form.get("id"):
            tools.complete_commitment(form.get("id")[0])

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *args):
        pass


def start_server():
    print(f"Hew running at http://localhost:{PORT}  (Ctrl+C to stop)")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    server.timeout = 0.5
    try:
        while True:
            server.handle_request()
    except KeyboardInterrupt:
        print("\nPowering down Hew...")
    finally:
        server.server_close()


if __name__ == "__main__":
    start_server()