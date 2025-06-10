import os
import re
import logging
import cv2
import pytesseract
import numpy as np
import platform
from PIL import Image
import dateutil.parser
from datetime import datetime, timedelta
from dateutil import parser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Tesseract OCR path based on platform
if platform.system() == 'Windows':
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    logger.info(f"Set Tesseract OCR path to: {tesseract_path}")
else:
    # On Linux/Unix systems, use system PATH
    logger.info("Using system PATH for Tesseract OCR")

# Global flag to track Tesseract availability
tesseract_available = False

# Test if Tesseract is available
try:
    tesseract_version = pytesseract.get_tesseract_version()
    logger.info(f"Tesseract version: {tesseract_version}")
    print(f"\nUsing Tesseract OCR version: {tesseract_version}\n")
    tesseract_available = True
except Exception as e:
    logger.error(f"Error getting Tesseract version: {str(e)}")
    print(f"Error accessing Tesseract: {str(e)}")
    print("Note: OCR functionality will be limited without Tesseract installed")
    tesseract_available = False

def preprocess_image(image_path):
    """Preprocess an image to improve OCR results"""
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to load image from {image_path}")
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get a binary image
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Invert the image
        binary = 255 - binary
        
        return binary
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        return None

def extract_text_from_image(image_path):
    """Extract all text from an image using OCR"""
    try:
        # Load the image with PIL for simplest approach
        img = Image.open(image_path)
        
        # Perform OCR directly - simpler and often more reliable than preprocessing
        text = pytesseract.image_to_string(img)
        
        # Save the raw OCR text for debugging
        debug_file = os.path.dirname(image_path) + "/debug_ocr.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        logger.info(f"Extracted text from image: {len(text)} characters. Saved to {debug_file}")
        print(f"\nExtracted {len(text)} characters from image. Saved raw OCR to {debug_file}\n")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return None

def extract_time_entries(text):
    """Extract structured time entry data from OCR text"""
    if not text:
        return []
    
    entries = []
    
    # Parse text for recognizable patterns of time entries
    lines = text.split('\n')
    
    # Enhanced patterns for Punch Clocks app format
    # Very flexible patterns to handle OCR variations
    order_number_pattern = r'(?:Order|Qrder|0rder)[\s\-]*(?:Number|Humber|Numher|Num|Hum)?[\s:]*([A-Z0-9]{1,4}[\-]?[0-9]{1,6}[\-]?[0-9]{1,6})'
    elapsed_time_pattern = r'(?:Elapsed|Elapsad|Ela psed)[\s\-]*(?:Time|Tima)?[\s:]*(\d{1,2})[\s:]*h[\s:]*(\d{1,2})[\s:]*m[\s:]*(\d{1,2})[\s:]*s'
    time_range_pattern = r'(\d{1,2}/\d{1,2}/\d{4})[\s]+(\d{1,2}:\d{2}(?::\d{2})?)[\s]*([APap][Mm])[\s\-]*(?:to|-)[\s]*(\d{1,2}/\d{1,2}/\d{4})[\s]+(\d{1,2}:\d{2}(?::\d{2})?)[\s]*([APap][Mm])'
    employee_pattern = r'(?:Employee|Name|User)?[\s:]*([A-Z][a-z]+[\s]+[A-Z][a-z]+)'
    
    current_entry = {}
    punch_clocks_format = False
    
    # Print entire text for debugging
    print("\n===== FULL OCR TEXT =====")
    print(text)
    print("===== END OCR TEXT =====\n")
    
    # First pass - try to determine if this is a Punch Clocks format
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if re.search(r'Punch[\s\-]*Clocks', line, re.IGNORECASE) or re.search(order_number_pattern, line, re.IGNORECASE):
            punch_clocks_format = True
            print(f"Detected Punch Clocks app format based on line: {line}")
            break
    
    if not punch_clocks_format:
        print("Not a Punch Clocks format, falling back to generic extraction")
        return extract_generic_time_entries(text)
    
    # Second pass - process line by line for Punch Clocks format
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        print(f"Processing line {i}: {line}")
        
        # Check for order number
        order_match = re.search(order_number_pattern, line, re.IGNORECASE)
        if order_match:
            # Start a new entry if we have an existing one
            if current_entry and 'order_number' in current_entry:
                entries.append(current_entry)
                print(f"Found completed entry: {current_entry}")
                current_entry = {}
            
            order_num = order_match.group(1)
            # Clean up order number if needed
            order_num = re.sub(r'[^A-Z0-9\-]', '', order_num)
            current_entry['order_number'] = order_num
            current_entry['entry_type'] = 'service_order'
            print(f"Found order number: {order_num}")
            continue
        
        # Try to match elapsed time - very flexible pattern
        elapsed_match = re.search(elapsed_time_pattern, line, re.IGNORECASE)
        if elapsed_match and current_entry:
            try:
                hours = int(elapsed_match.group(1))
                minutes = int(elapsed_match.group(2))
                seconds = int(elapsed_match.group(3))
                
                decimal_hours = hours + minutes/60 + seconds/3600
                # Round to 2 decimal places for consistent display
                current_entry['hours'] = round(decimal_hours, 2)
                print(f"Found hours: {current_entry['hours']} ({hours}h:{minutes}m:{seconds}s)")
            except Exception as e:
                print(f"Error parsing elapsed time: {e}")
            continue
        
        # Try to match time range with more flexible pattern
        time_range_match = re.search(time_range_pattern, line, re.IGNORECASE)
        if not time_range_match:
            # Try alternative pattern without seconds
            alt_pattern = r'(\d{1,2}/\d{1,2}/\d{4})[\s]+(\d{1,2}:\d{2})[\s]*([APap][Mm])[\s\-]*(?:to|-)[\s]*(\d{1,2}/\d{1,2}/\d{4})[\s]+(\d{1,2}:\d{2})[\s]*([APap][Mm])'
            time_range_match = re.search(alt_pattern, line, re.IGNORECASE)
        
        if time_range_match and current_entry:
            try:
                start_date = time_range_match.group(1)
                start_time = time_range_match.group(2)
                start_ampm = time_range_match.group(3).upper()
                end_date = time_range_match.group(4)
                end_time = time_range_match.group(5)
                end_ampm = time_range_match.group(6).upper()
                
                # Add seconds if not present
                if len(start_time.split(':')) == 2:
                    start_time += ":00"
                if len(end_time.split(':')) == 2:
                    end_time += ":00"
                    
                # Combine into full datetime strings
                start_datetime_str = f"{start_date} {start_time} {start_ampm}"
                end_datetime_str = f"{end_date} {end_time} {end_ampm}"
                
                # Parse datetime strings
                start_datetime = parser.parse(start_datetime_str)
                end_datetime = parser.parse(end_datetime_str)
                
                current_entry['start_time'] = start_datetime
                current_entry['end_time'] = end_datetime
                current_entry['date'] = start_datetime.date()
                # Also store the date as an ISO format string for template rendering
                current_entry['date_str'] = start_datetime.date().strftime('%Y-%m-%d')
                
                # Calculate hours from time range
                time_diff = end_datetime - start_datetime
                hours_from_time_range = time_diff.total_seconds() / 3600
                # Round to 2 decimal places for consistent display
                current_entry['hours'] = round(hours_from_time_range, 2)
                
                print(f"Found time range: {start_datetime} to {end_datetime}, hours: {current_entry['hours']}")
            except Exception as e:
                print(f"Error parsing time range: {e}")
            continue
        
        # Check for employee name
        employee_match = re.search(employee_pattern, line, re.IGNORECASE)
        if employee_match and current_entry:
            current_entry['employee_name'] = employee_match.group(1).strip()
            print(f"Found employee name: {current_entry['employee_name']}")
            continue
        
        # Also look for standalone names (First Last format)
        standalone_name = re.match(r'^([A-Z][a-z]+[\s]+[A-Z][a-z]+)$', line)
        if standalone_name and current_entry and 'employee_name' not in current_entry:
            current_entry['employee_name'] = standalone_name.group(1).strip()
            print(f"Found standalone employee name: {current_entry['employee_name']}")
    
    # Add the last entry if it exists
    if current_entry and 'order_number' in current_entry:
        entries.append(current_entry)
        print(f"Added final entry: {current_entry}")
    
    # Final check for required fields
    valid_entries = []
    for entry in entries:
        if 'order_number' in entry and ('hours' in entry or ('start_time' in entry and 'end_time' in entry)):
            if 'employee_name' not in entry:
                entry['employee_name'] = 'Unknown Employee'  # Default name if not found
            valid_entries.append(entry)
    
    print(f"Extracted {len(valid_entries)} valid time entries")
    return valid_entries

def extract_generic_time_entries(text):
    """Extract time entry data from generic OCR text"""
    entries = []
    
    # Log attempt
    logger.info("Attempting generic time entry extraction")
    print("Attempting generic time entry extraction")
    
    # Parse text for recognizable patterns of time entries
    lines = text.split('\n')
    
    # Generic patterns for dates, times, durations, and names
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
        r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'  # Month DD, YYYY
    ]
    
    time_patterns = [
        r'(\d{1,2}:\d{2}(?::\d{2})?\s*[APap][Mm])',  # 12-hour format
        r'(\d{1,2}:\d{2}(?::\d{2})?)(?!\s*[APap][Mm])'  # 24-hour format
    ]
    
    duration_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:hour|hr|h)s?',  # X hours, X hrs, X h
        r'(\d+)\s*(?:min|m)\s',  # X min, X m
        r'(\d+):(\d{2})'  # X:XX format
    ]
    
    # Process each line
    current_entry = None
    current_date = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for dates
        date_found = False
        for pattern in date_patterns:
            date_match = re.search(pattern, line)
            if date_match:
                date_str = date_match.group(1)
                try:
                    date_obj = parser.parse(date_str).date()
                    current_date = date_obj
                    date_found = True
                    
                    # Start a new entry if needed
                    if current_entry and 'date' in current_entry:
                        entries.append(current_entry)
                        current_entry = None
                        
                    if not current_entry:
                        current_entry = {
                            'date': current_date,
                            'date_str': current_date.strftime('%Y-%m-%d')
                        }
                    break
                except Exception as e:
                    logger.error(f"Error parsing date: {e}")
        
        # Look for time ranges
        times = []
        for pattern in time_patterns:
            for match in re.finditer(pattern, line):
                times.append(match.group(1))
        
        if len(times) == 2 and current_entry:
            current_entry['start_time'] = times[0]
            current_entry['end_time'] = times[1]
            
            # Try to calculate hours
            try:
                start_time = parser.parse(times[0])
                end_time = parser.parse(times[1])
                diff_hours = (end_time - start_time).total_seconds() / 3600
                current_entry['hours'] = round(diff_hours, 2)
            except Exception as e:
                print(f"Could not calculate hours from time range: {e}")
        
        # Look for durations
        for pattern in duration_patterns:
            duration_match = re.search(pattern, line)
            if duration_match and current_entry and 'hours' not in current_entry:
                if ':' in pattern:
                    hours = int(duration_match.group(1))
                    minutes = int(duration_match.group(2))
                    current_entry['hours'] = round(hours + minutes / 60, 2)
                else:
                    current_entry['hours'] = float(duration_match.group(1))
        
        # Look for potential employee names (capitalized words)
        name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$', line)
        if name_match and current_entry and 'employee_name' not in current_entry:
            current_entry['employee_name'] = name_match.group(1)
        
        # Look for potential order numbers or job codes
        order_match = re.search(r'(?:job|order|code)[\s:#]*(\w{2,}[-\d]*\d+)', line, re.IGNORECASE)
        if order_match and current_entry and 'order_number' not in current_entry:
            current_entry['order_number'] = order_match.group(1)
            current_entry['entry_type'] = 'service_order'
    
    # Add the final entry if it exists
    if current_entry:
        entries.append(current_entry)
    
    # Ensure all entries have the minimum required fields
    valid_entries = []
    for entry in entries:
        # Make sure we have at least a date and hours or time range
        if 'date' in entry and ('hours' in entry or ('start_time' in entry and 'end_time' in entry)):
            # Set defaults for missing fields
            if 'employee_name' not in entry:
                entry['employee_name'] = 'Unknown Employee'
            if 'order_number' not in entry:
                entry['order_number'] = f"OTHER-{len(valid_entries)+1}"
                entry['entry_type'] = 'other_time'
            
            valid_entries.append(entry)
    
    print(f"Generic extraction found {len(valid_entries)} possible time entries")
    return valid_entries

def parse_image_for_time_entries(image_path, format_type='standard'):
    """Process an image and extract time entry data based on the specified format
    
    Args:
        image_path (str): Path to the image file
        format_type (str): Type of time entry format - 'standard' or 'generic'
    """
    print(f"\nProcessing image: {image_path} with format: {format_type}\n")
    
    try:
        # Verify image exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at path: {image_path}")
            print(f"ERROR: Image file not found at path: {image_path}")
            # Return demo data in production
            if os.environ.get('RENDER', '') == 'true':
                print("Returning demo data since file not found")
                return get_demo_entries('Missing File', format_type)
            return []

        # Check if Tesseract is available
        if not tesseract_available:
            logger.warning("Tesseract OCR is not available. Cannot process image.")
            print("WARNING: Tesseract OCR is not available. Using demo data instead.")
            # Return a sample entry for demo purposes when deployed without Tesseract
            if os.environ.get('RENDER', '') == 'true':
                logger.info("Running on Render: returning demo data instead of OCR")
                return get_demo_entries('No Tesseract', format_type)
            return []
        
        # Extract text using OCR
        try:
            text = extract_text_from_image(image_path)
            print(f"Extracted text length: {len(text) if text else 0} characters")
            
            if not text:
                logger.error("Could not extract text from image")
                print("ERROR: Could not extract text from image")
                # Return a sample entry on error in production environment
                if os.environ.get('RENDER', '') == 'true':
                    return get_demo_entries('No Text', format_type)
                return []
                
        except Exception as e:
            logger.error(f"Error in OCR text extraction: {str(e)}")
            print(f"ERROR in OCR text extraction: {str(e)}")
            if os.environ.get('RENDER', '') == 'true':
                return get_demo_entries('OCR Error', format_type)
            return []
        
        # Try to extract time entries based on format type
        try:
            # Choose extraction method based on format type
            if format_type == 'generic':
                print("Using generic format extraction method")
                entries = extract_generic_time_entries(text)
            else:  # default to standard
                print("Using standard format extraction method")
                entries = extract_time_entries(text)
            
            # Log results
            if entries:
                logger.info(f"Successfully extracted {len(entries)} time entries using {format_type} format")
                print(f"Successfully extracted {len(entries)} time entries using {format_type} format")
                print(f"First entry: {entries[0]}")
                
                # Add format type to each entry
                for entry in entries:
                    entry['format_type'] = format_type
                    
                return entries
            else:
                logger.warning(f"No time entries could be extracted using {format_type} format")
                print(f"WARNING: No time entries could be extracted using {format_type} format")
                
                # Try alternative format if first one fails
                if format_type == 'standard':
                    print("Trying generic format as fallback...")
                    fallback_entries = extract_generic_time_entries(text)
                    if fallback_entries:
                        logger.info(f"Fallback successful: extracted {len(fallback_entries)} entries using generic format")
                        print(f"Fallback successful: extracted {len(fallback_entries)} entries using generic format")
                        # Add format type to each entry
                        for entry in fallback_entries:
                            entry['format_type'] = 'generic (fallback)'
                        return fallback_entries
                
                # Return demo data in production if no entries extracted
                if os.environ.get('RENDER', '') == 'true':
                    return get_demo_entries('No Entries', format_type)
                return []
                
        except Exception as e:
            logger.error(f"Error extracting time entries with {format_type} format: {str(e)}")
            print(f"ERROR extracting time entries with {format_type} format: {str(e)}")
            if os.environ.get('RENDER', '') == 'true':
                return get_demo_entries('Parse Error', format_type)
            return []
            
    except Exception as e:
        logger.error(f"Unexpected error in parse_image_for_time_entries: {str(e)}")
        print(f"UNEXPECTED ERROR in parse_image_for_time_entries: {str(e)}")
        # Return demo data in production
        if os.environ.get('RENDER', '') == 'true':
            return get_demo_entries('Unknown Error', format_type)
        return []

def get_demo_entries(error_type, format_type='standard'):
    """Generate demo time entries for testing/demo purposes
    
    Args:
        error_type (str): Type of error that triggered demo entry generation
        format_type (str): Format type being used ('standard' or 'generic')
    """
    print(f"Generating demo entries due to: {error_type} with format: {format_type}")
    
    if format_type == 'generic':
        # Generate a more generic demo entry without order number
        return [{
            'employee_name': 'Jane Smith',
            'task_description': f'Demo Task ({error_type})',
            'date': datetime.now().date(),
            'date_str': datetime.now().strftime('%Y-%m-%d'),
            'entry_type': 'time_entry',
            'hours': 3.5,
            'start_time': '09:30 AM',
            'end_time': '01:00 PM',
            'from_demo': True,
            'format_type': format_type
        }]
    else:
        # Standard format demo entry with order number
        return [{
            'employee_name': 'John Doe',
            'order_number': f'DEMO-{error_type}',
            'date': datetime.now().date(),
            'date_str': datetime.now().strftime('%Y-%m-%d'),
            'entry_type': 'service_order',
            'hours': 4.25,
            'start_time': '08:00 AM',
            'end_time': '12:15 PM',
            'from_demo': True,
            'format_type': format_type
        }]
