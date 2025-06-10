#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Print Python version for debugging
python --version

# Note: Tesseract is not installed during build
# The app will be configured to handle missing Tesseract
