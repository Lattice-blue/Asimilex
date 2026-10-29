"""
Root entry point for Hew.
Runs the server and automatically opens your browser.
"""
import threading
import webbrowser
from ui.web import start_server
from engine.rules import spawn_daily_habits

def open_browser():
    webbrowser.open("http://127.0.0.1:8765")

if __name__ == "__main__":
    # 1. Run the Cheap Loop to stamp today's habits
    spawn_daily_habits()
    
    # 2. Launch UI
    threading.Timer(0.6, open_browser).start()
    start_server()  