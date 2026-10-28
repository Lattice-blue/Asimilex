"""
Root entry point for Hew.
Runs the server and automatically opens your browser.
"""
import threading
import webbrowser
from ui.web import start_server

def open_browser():
    webbrowser.open("http://127.0.0.1:8765")

if __name__ == "__main__":
    # Automatically launches Edge/default browser after 0.6 seconds
    threading.Timer(0.6, open_browser).start()
    start_server()