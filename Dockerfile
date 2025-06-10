FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Tesseract OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    wkhtmltopdf \
    opencv-data \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
RUN pip install waitress

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Create a startup script to initialize the database at runtime
RUN echo '#!/bin/bash\npython -c "from app import db, create_default_admin; db.create_all(); create_default_admin()"\npython app.py' > /app/start.sh && \
    chmod +x /app/start.sh

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV RENDER=true
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# Expose the port the app will run on
EXPOSE 10000

# Command to run the startup script
CMD ["/bin/bash", "/app/start.sh"]
