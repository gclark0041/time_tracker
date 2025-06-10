import os
import sys
import atexit
import webbrowser
import threading
import time
from waitress import serve
from app import app

# Configuration
PORT = 5050
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"

def open_browser():
    """Open browser after a short delay"""
    time.sleep(1.5)  # Wait for server to start
    webbrowser.open(URL)

def cleanup():
    """Clean up resources on exit"""
    print("Shutting down application...")

if __name__ == "__main__":
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Start browser in a new thread
    threading.Thread(target=open_browser).start()
    
    # Display startup message
    print("=" * 60)
    print(f"Time Tracker is starting up!")
    print(f"Server running at: {URL}")
    print("=" * 60)
    
    # Run production server
    serve(app, host=HOST, port=PORT)
