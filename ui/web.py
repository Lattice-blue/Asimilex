"""
Web interface for Hew.
Minimalist, distraction-free conversational terminal.
"""
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from engine import db, llm

PORT = 8765

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hew</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #0b0c10;
    color: #e0e2ec;
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 720px;
    margin: 0 auto;
    padding: 1.5rem 1rem;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 1rem;
    border-bottom: 1px solid #1a1d26;
  }
  h1 { font-size: 1.25rem; font-weight: 600; letter-spacing: 0.05em; color: #fff; }
  .status { font-size: 0.8rem; color: #4ade80; display: flex; align-items: center; gap: 0.4rem; }
  .status::before { content: ""; width: 7px; height: 7px; background: #4ade80; border-radius: 50%; display: inline-block; }
  
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
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
    color: #64748b;
    margin-bottom: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .msg.user .sender { color: #94a3b8; text-align: right; }
  .msg.hew .sender { color: #60a5fa; }
  
  form.chat-input {
    display: flex;
    gap: 0.6rem;
    padding-top: 1rem;
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
</style>
</head>
<body>
  <header>
    <h1>HEW</h1>
    <span class="status">Mirror Synced</span>
  </header>

  <div class="chat-container" id="chatbox">
    %CHAT%
  </div>

  <form class="chat-input" method="post" action="/chat">
    <input type="text" name="message" placeholder="Directive or query..." autocomplete="off" autofocus required>
    <button type="submit">Send</button>
  </form>

  <script>
    var chatbox = document.getElementById("chatbox");
    chatbox.scrollTop = chatbox.scrollHeight;
  </script>
</body>
</html>"""


def render():
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

    return PAGE.replace("%CHAT%", chat_html)


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
        user_msg = form.get("message", [""])[0]

        if self.path == "/chat" and user_msg:
            db.log_message("user", user_msg)
            reply = llm.call_llm(user_msg)
            db.log_message("hew", reply)

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *args):
        pass


def start_server():
    print(f"Hew terminal running at http://localhost:{PORT}  (Ctrl+C to stop)")
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