from datetime import datetime, timedelta
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from engine import db

PORT = 8765
LABELS = {"went_to_bed": "Went to bed", "woke_up": "Woke up"}


def parse_time(at):
    """'HH:MM' -> that time today, or yesterday if it hasn't happened yet today."""
    now = datetime.now().astimezone()
    if not at:
        return now
    try:
        h, m = (int(x) for x in at.split(":")[:2])
        ts = now.replace(hour=h, minute=m, second=0, microsecond=0)
    except ValueError:
        return now
    return ts - timedelta(days=1) if ts > now else ts


def last_sleep():
    """Derived, never stored: time between the latest bedtime and the wake-up after it."""
    events = sorted(db.recent_events(20), key=lambda e: e["ts"])
    wake = next((e for e in reversed(events) if e["kind"] == "woke_up"), None)
    if not wake:
        return None
    bed = next(
        (e for e in reversed(events) if e["kind"] == "went_to_bed" and e["ts"] < wake["ts"]),
        None,
    )
    if not bed:
        return None
    secs = (datetime.fromisoformat(wake["ts"]) - datetime.fromisoformat(bed["ts"])).total_seconds()
    if secs > 16 * 3600:  # probably a missed log, don't show nonsense
        return None
    return f"{int(secs // 3600)}h {int(secs % 3600 // 60)}m"


PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asimilex</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:420px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}
 h1, h2{font-weight:600}
 h2{margin-top:2.5rem; font-size:1.4rem; border-bottom:1px solid #333; padding-bottom:0.5rem;}
 form.big{display:grid;gap:.75rem}
 button.big{font-size:1.4rem;padding:1.2rem;border:0;border-radius:14px;cursor:pointer;color:#fff}
 .bed{background:#4b3fa0}.wake{background:#d98e04}
 label{color:#aaa;font-size:.9rem}
 input[type=time], input[type=text], input[type=date], select {font-size:1.1rem;padding:.4rem;border-radius:8px;border:0;width:100%;box-sizing:border-box;background:#222;color:#eee}
 input::placeholder {color: #666;}
 table{width:100%;border-collapse:collapse;margin-top:1rem}
 td{padding:.5rem 0;border-bottom:1px solid #333;vertical-align:top;}
 .del{background:none;border:0;color:#888;cursor:pointer;font-size:1.2rem;padding:0 .5rem;}
 .complete{background:#2a6a42;border:0;color:#fff;cursor:pointer;font-size:.9rem;padding:.3rem .6rem;border-radius:6px;}
 .sleep{margin:1rem 0 1.5rem;font-size:1.1rem;color:#9fd}
 .goal-meta {font-size:.8rem; color:#aaa; margin-top:0.2rem;}
 .goal-p1 {color: #ff6b6b;}
 .goal-p2 {color: #fca311;}
 .goal-p3 {color: #888;}
</style></head><body>
<h1>Asimilex</h1>

%SLEEP%
<form class="big" method="post" action="/log">
 <label>Forgot to press it earlier? Set when it happened (optional)</label>
 <input type="time" name="at">
 <button class="big bed" name="kind" value="went_to_bed">Went to bed</button>
 <button class="big wake" name="kind" value="woke_up">Woke up</button>
</form>
<table>%ROWS%</table>

<h2>Goals</h2>
<form class="big" method="post" action="/add_goal">
 <input type="text" name="title" placeholder="New goal (e.g., Run a 5k)" required>
 <input type="text" name="why" placeholder="Why? (optional)">
 <div style="display:flex;gap:.5rem">
  <input type="date" name="deadline" title="Deadline">
  <select name="priority">
   <option value="1">P1 (High)</option>
   <option value="2">P2 (Med)</option>
   <option value="3" selected>P3 (Low)</option>
  </select>
  <button style="background:#3a86ff;color:#fff;border:none;border-radius:8px;padding:0 1rem;">Add</button>
 </div>
</form>
<table>%GOALS%</table>

</body></html>"""


def render():
    # 1. Render Sleep/Events
    sleep = last_sleep()
    sleep_html = f'<div class="sleep">Last sleep: {sleep}</div>' if sleep else ""
    rows = ""
    for e in db.recent_events(10):
        when = datetime.fromisoformat(e["ts"]).strftime("%a %d %b, %H:%M")
        rows += (
            f"<tr><td>{when}</td><td>{escape(LABELS.get(e['kind'], e['kind']))}</td>"
            f'<td style="text-align:right"><form method="post" action="/delete_event">'
            f'<input type="hidden" name="id" value="{e["id"]}">'
            f'<button class="del" title="Delete">✕</button></form></td></tr>'
        )
    
    # 2. Render Goals
    goals_html = ""
    for g in db.get_active_goals():
        priority_class = f"goal-p{g['priority']}"
        deadline_str = f" • Due {g['deadline']}" if g['deadline'] else ""
        why_str = f"<div class='goal-meta'>↳ {escape(g['why'])}</div>" if g['why'] else ""
        
        goals_html += (
            f"<tr><td>"
            f"<strong class='{priority_class}'>P{g['priority']}</strong> {escape(g['title'])}"
            f"<span class='goal-meta'>{deadline_str}</span>"
            f"{why_str}</td>"
            f'<td style="text-align:right; width:70px"><form method="post" action="/complete_goal">'
            f'<input type="hidden" name="id" value="{g["id"]}">'
            f'<button class="complete" title="Mark Completed">✔</button></form></td></tr>'
        )

    return PAGE.replace("%SLEEP%", sleep_html).replace("%ROWS%", rows).replace("%GOALS%", goals_html)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        body = render().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        get = lambda k: form.get(k, [""])[0]
        
        # Routing POST requests
        if self.path == "/log" and get("kind") in LABELS:
            db.log_event(get("kind"), ts=parse_time(get("at")))
        elif self.path == "/delete_event" and get("id").isdigit():
            db.delete_event(int(get("id")))
        elif self.path == "/add_goal" and get("title"):
            db.add_goal(get("title"), get("why"), get("deadline"), int(get("priority") or 3))
        elif self.path == "/complete_goal" and get("id").isdigit():
            # We mark as 'completed' instead of deleting, matching the "History matters" principle
            db.update_goal_status(int(get("id")), "completed")
            
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"Asimilex running at http://localhost:{PORT}  (Ctrl+C to stop)")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    
    # Set a 0.5s timeout so Python periodically wakes up to catch KeyboardInterrupt (Ctrl+C)
    server.timeout = 0.5

    try:
        while True:
            server.handle_request()
    except KeyboardInterrupt:
        print("\nStopping Asimilex...")
    finally:
        server.server_close()