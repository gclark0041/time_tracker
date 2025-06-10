#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr
apt-get install -y python3-dev

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Print tesseract version for debugging
tesseract --version

# Print Python version for debugging
python --version
