"""
Time Tracker Desktop Launcher
This script launches the Time Tracker as a desktop application by:
1. Starting the Flask server in the background
2. Opening the system default web browser to access the interface
"""
import os
import sys
import threading
import webbrowser
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('TimeTracker')

# Add the current directory to the path so we can import from the app
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Ensure the uploads directory exists
uploads_dir = os.path.join(current_dir, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_flask_server():
    """Start the Flask server in a separate thread"""
    from app import app
    from waitress import serve
    
    # Set environment to desktop mode
    os.environ['DESKTOP_MODE'] = 'true'
    
    # Use a random available port
    port = 5050
    
    try:
        logger.info(f"Starting server on http://127.0.0.1:{port}")
        serve(app, host='127.0.0.1', port=port)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)

def ensure_tesseract_installed():
    """Check if Tesseract is installed and alert user if not"""
    import shutil
    
    tesseract_path = shutil.which('tesseract')
    
    if not tesseract_path:
        # Check common Windows installation paths
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                os.environ['TESSERACT_CMD'] = path
                logger.info(f"Found Tesseract at: {path}")
                return True
                
        logger.warning("Tesseract OCR not found on the system.")
        logger.warning("OCR functionality will use demo data instead.")
        logger.warning("Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    logger.info(f"Found Tesseract at: {tesseract_path}")
    return True

def main():
    """Main entry point for the desktop application"""
    logger.info("Starting Time Tracker Desktop Application")
    
    # Check for Tesseract OCR installation
    ensure_tesseract_installed()
    
    # Start the Flask server in a background thread
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(2)
    
    # Open the web browser to the application
    url = "http://127.0.0.1:5050"
    logger.info(f"Opening browser to: {url}")
    webbrowser.open(url)
    
    # Keep the application running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    
if __name__ == "__main__":
    main()
