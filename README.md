# Time Tracker Pro

A modern web application for tracking employee time with image upload and OCR capabilities, comprehensive reporting, and a clean, intuitive interface.

## Features

- **Manual Time Entry**: Easy form-based time entry with multiple categories (Service Order, Vacation, Personal, Shop, Non-Billable, Drive Time)
- **Image Upload & OCR**: Upload images of time sheets and automatically extract time data
- **Real-time Search**: Filter and search through time entries instantly
- **Comprehensive Reports**: Generate PDF reports in multiple formats:
  - Summary Report: Overview of hours by employee and type
  - Detailed Report: Complete list of all time entries
  - Employee Report: Individual employee time breakdowns
  - Service Order Report: Time tracking by service order
- **Modern UI**: Responsive design that works on desktop and mobile devices
- **Data Persistence**: SQLite database for reliable data storage

## Prerequisites

- Python 3.8 or higher
- Node.js (for running the frontend)
- Tesseract OCR (for image text extraction)

## Installation

### 1. Install Python Dependencies

Navigate to the backend directory and install required packages:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Tesseract OCR

**Windows:**
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer and note the installation path
3. Add Tesseract to your PATH environment variable

**Mac:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Initialize the Database

The database will be automatically created when you first run the backend.

## Running the Application

### Option 1: Using the Batch File (Windows)

Simply double-click `run_app.bat` in the project root directory.

### Option 2: Manual Start

1. **Start the Backend Server:**
   ```bash
   cd backend
   python app.py
   ```
   The backend will run on http://localhost:5000

2. **Open the Frontend:**
   Open `index.html` in your web browser (Chrome, Firefox, or Edge recommended)

## Usage Guide

### Manual Time Entry

1. Click on the "Manual Entry" tab
2. Fill in the required fields:
   - Employee Name
   - Entry Type (Service Order requires an order number)
   - Start and End Date/Time
   - Optional notes
3. Click "Save Entry"

### Upload Time Sheet Image

1. Click on the "Upload Image" tab
2. Either drag and drop an image or click to browse
3. Review the extracted data
4. Click "Confirm & Save All" to save the entries

### View and Manage Entries

1. Click on the "View Entries" tab
2. Use the search bar to filter entries
3. Click the edit (✏️) button to modify an entry
4. Click the delete (🗑️) button to remove an entry

### Generate Reports

1. Click on the "Reports" tab
2. Select report type:
   - Summary: Overview by employee and time type
   - Detailed: All entries with full details
   - Employee: Breakdown by individual employee
   - Service Order: Time grouped by order number
3. Set date range and optional employee filter
4. Click "Generate PDF Report"
5. The report will download automatically

## Data Storage

- All time entries are stored in `backend/timetracker.db`
- The database is automatically backed up to localStorage for redundancy
- Images are processed but not stored (only extracted data is saved)

## Troubleshooting

### Backend Won't Start
- Ensure Python 3.8+ is installed: `python --version`
- Check if port 5000 is available
- Verify all dependencies are installed

### OCR Not Working
- Ensure Tesseract is installed and in PATH
- Check image quality (clear, well-lit images work best)
- Verify image format (JPG, PNG, GIF supported)

### PDF Reports Not Generating
- Check that ReportLab is installed: `pip install reportlab`
- Ensure the backend server is running
- Check browser console for errors

## API Documentation

### Endpoints

- `GET /api/entries` - Retrieve all time entries
- `POST /api/entries` - Create a new time entry
- `PUT /api/entries/<id>` - Update an existing entry
- `DELETE /api/entries/<id>` - Delete an entry
- `POST /api/ocr` - Process image and extract time data
- `POST /api/report` - Generate PDF report
- `GET /api/stats` - Get summary statistics

## Future Enhancements

- Real OCR integration with cloud services (Google Vision, AWS Textract)
- User authentication and multi-user support
- Email report scheduling
- Mobile app version
- Excel export functionality
- Time approval workflow
- Integration with payroll systems

## License

This project is provided as-is for personal and commercial use.

## Support

For issues or questions, please check the troubleshooting section or create an issue in the project repository.
