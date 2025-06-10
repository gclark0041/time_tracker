from flask import Flask
from waitress import serve
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import app from app.py
from app import app

def handler(event, context):
    """
    Netlify Function handler to serve the Flask app
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html",
        },
        "body": "Time Tracker app is running. Please use the API endpoints."
    }

# For local development
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)
