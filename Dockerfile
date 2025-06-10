FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install wkhtmltopdf for PDF generation
RUN apt-get update && \
    apt-get install -y wkhtmltopdf && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY . .

# Run migrations and create database
RUN python -c "from app import db; db.create_all()"

# Expose port
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Start the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"]
