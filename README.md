# Time Tracker Application

A web-based application for tracking work time on orders and generating reports.

## Features

- **Order Time Tracking**: Track start and end times for work orders
- **Real-time Duration Display**: See elapsed time for active orders updated in real-time
- **Employee Productivity Reports**: Analyze work patterns and efficiency
- **Order Processing Time Reports**: Visualize how long orders take to complete
- **Data Export**: Export time tracking data to Excel for further analysis

## Installation

1. Clone this repository to your local machine
2. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:

```bash
python app.py
```

2. Open your web browser and navigate to: `http://127.0.0.1:5000/`

## Using the Application

### Tracking Time

1. Click "New Order" to start tracking time for a new order
2. Enter the order number and employee name
3. When work is complete, click "Complete" to stop tracking

### Generating Reports

1. Click "Reports" in the navigation menu
2. Choose the type of report you want to generate:
   - Order Processing Times
   - Employee Productivity
3. Select date range and click "Generate Report"
4. View visualizations and data tables of your time tracking information
5. Export data to Excel for further analysis

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, Flask-Login
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Visualization**: Plotly
- **Database**: SQLite
- **OCR**: Tesseract OCR, OpenCV, pytesseract

## Deployment on Render

This application is ready to be deployed on Render, which supports Python web applications and system dependencies like Tesseract OCR.

### Deployment Steps:

1. Create a free account on [Render](https://render.com/)
2. From your dashboard, click on "New" and select "Web Service"
3. Connect your GitHub repository or use the option to deploy from an existing repository
4. Configure the following settings:
   - **Name**: time-tracker (or your preferred name)
   - **Environment**: Python 3
   - **Region**: Choose the closest region to your users
   - **Branch**: main (or your default branch)
   - **Build Command**: `chmod +x build.sh && ./build.sh`
   - **Start Command**: `python app.py`
   - **Plan**: Free

5. Add the following environment variables:
   - `RENDER=true`
   - `PYTHON_VERSION=3.10.4`

6. Click "Create Web Service"

The build will take a few minutes to complete. Once finished, your Time Tracker application will be available at the URL provided by Render.

### Important Notes:

- The free plan on Render will spin down after periods of inactivity and spin up when receiving new requests
- The database is stored on the filesystem, so data will persist between deployments but not indefinitely
- For production use, consider upgrading to a paid plan or implementing a persistent database solution
