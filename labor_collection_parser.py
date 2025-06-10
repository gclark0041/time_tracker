"""
Labor Collection Report Parser Module
Handles extraction of time entries from labor collection reports
"""
import re
from datetime import datetime, timedelta
from dateutil import parser

def extract_labor_collection_entries(text):
    """
    Extract time entries from Labor Collection report format
    
    Sample format:
    Order Number    Labor Type      Start Time           End Time            Hours
    SO24-02365-21800 RegularTime    6/6/2025 10:23:00 AM 6/6/2025 2:33:00 PM 4 Hours 10 Minutes
    """
    if not text:
        return []
        
    entries = []
    lines = text.split('\n')
    
    # Extract employee name from greeting (e.g., "Dear Greg Clark")
    employee_name = "Current User"  # Default name
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        name_match = re.search(r'Dear\s+([A-Za-z]+\s+[A-Za-z]+)', line)
        if name_match:
            employee_name = name_match.group(1)
            print(f"Found employee name: {employee_name}")
            break
            
    # Look for the table header that indicates a Labor Collection report
    header_pattern = r'Order\s+Number\s+Labor\s+Type\s+Start\s+Time\s+End\s+Time\s+Hours'
    header_found = False
    
    for i, line in enumerate(lines):
        if re.search(header_pattern, line, re.IGNORECASE):
            header_found = True
            print(f"Found Labor Collection report header at line {i}: {line}")
            continue
            
        if not header_found:
            continue
            
        # Skip lines that don't contain actual entries
        if 'Total Hours' in line or not line.strip():
            continue
            
        # Pattern for labor collection entries
        # Order Number, Labor Type, Start Time, End Time, Hours
        entry_pattern = r'(S[O0][\dO0]{2}-[\dO0]{5}-[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d+)\s+Hours\s+(\d+)\s+Minutes'
        entry_match = re.search(entry_pattern, line)
        
        if entry_match:
            try:
                order_number = entry_match.group(1).strip()
                labor_type = entry_match.group(2).strip()
                start_time_str = entry_match.group(3).strip()
                end_time_str = entry_match.group(4).strip()
                hours = int(entry_match.group(5))
                minutes = int(entry_match.group(6))
                
                # Parse start and end times
                start_time = parser.parse(start_time_str)
                end_time = parser.parse(end_time_str)
                
                # Calculate decimal hours
                decimal_hours = hours + (minutes / 60)
                
                entry = {
                    'order_number': order_number,
                    'labor_type': labor_type,
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'date': start_time.date(),
                    'date_str': start_time.date().strftime('%Y-%m-%d'),
                    'hours': round(decimal_hours, 2),
                    'entry_type': 'service_order',
                    'employee_name': employee_name,
                    'format_type': 'labor_collection'
                }
                
                entries.append(entry)
                print(f"Extracted entry: {entry}")
                
            except Exception as e:
                print(f"Error parsing labor collection entry: {e} in line: {line}")
                
        else:
            # Try alternative format with different spacing
            alt_pattern = r'(S[O0][\dO0]{2}-[\dO0]{5}-[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2}).*?(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2}).*?(\d+)\s+Hours\s+(\d+)\s+Minutes'
            alt_match = re.search(alt_pattern, line)
            
            if alt_match:
                try:
                    order_number = alt_match.group(1).strip()
                    labor_type = alt_match.group(2).strip()
                    start_time_str = alt_match.group(3).strip()
                    end_time_str = alt_match.group(4).strip()
                    hours = int(alt_match.group(5))
                    minutes = int(alt_match.group(6))
                    
                    # Parse start and end times
                    start_time = parser.parse(start_time_str)
                    end_time = parser.parse(end_time_str)
                    
                    # Calculate decimal hours
                    decimal_hours = hours + (minutes / 60)
                    
                    entry = {
                        'order_number': order_number,
                        'labor_type': labor_type,
                        'start_time': start_time_str,
                        'end_time': end_time_str,
                        'date': start_time.date(),
                        'date_str': start_time.date().strftime('%Y-%m-%d'),
                        'hours': round(decimal_hours, 2),
                        'entry_type': 'service_order',
                        'employee_name': employee_name,
                        'format_type': 'labor_collection'
                    }
                    
                    entries.append(entry)
                    print(f"Extracted entry with alternative pattern: {entry}")
                    
                except Exception as e:
                    print(f"Error parsing labor collection entry with alternative pattern: {e} in line: {line}")
    
    return entries

def extract_punch_clocks_entries(text):
    """
    Extract time entries from Punch Clocks app format
    
    Sample format:
    Order Number: SO24-02365-21800
    Elapsed Time: 04h:10m:00s
    6/6/2025 11:23:00 AM - 6/6/2025 3:33:00 PM
    Greg Clark
    """
    if not text:
        return []
        
    entries = []
    lines = text.split('\n')
    
    # Check if this looks like a Punch Clocks format
    if not (re.search(r'Punch\s+Clocks', text, re.IGNORECASE) or 
            re.search(r'Order\s+Number.*?Elapsed\s+Time', text, re.IGNORECASE)):
        return []
        
    # Processing variables
    current_entry = {}
    
    # Patterns for Punch Clocks format
    order_pattern = r'Order\s+Number:?\s+(S[O0][\dO0]{2}-[\dO0]{5}-[\dO0]{5})'
    elapsed_pattern = r'Elapsed\s+Time:?\s+(\d{2})h:?(\d{2})m:?(\d{2})s'
    time_range_pattern = r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+-\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[APM]{2})'
    name_pattern = r'^([A-Z][a-z]+\s+[A-Z][a-z]+)$'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract order number
        order_match = re.search(order_pattern, line)
        if order_match:
            if current_entry and 'order_number' in current_entry:
                entries.append(current_entry)
                current_entry = {}
                
            current_entry['order_number'] = order_match.group(1)
            current_entry['entry_type'] = 'service_order'
            continue
            
        # Extract elapsed time
        elapsed_match = re.search(elapsed_pattern, line)
        if elapsed_match and current_entry:
            hours = int(elapsed_match.group(1))
            minutes = int(elapsed_match.group(2))
            seconds = int(elapsed_match.group(3))
            
            decimal_hours = hours + minutes/60 + seconds/3600
            current_entry['hours'] = round(decimal_hours, 2)
            continue
            
        # Extract time range
        time_match = re.search(time_range_pattern, line)
        if time_match and current_entry:
            start_date = time_match.group(1)
            start_time = time_match.group(2)
            end_date = time_match.group(3)
            end_time = time_match.group(4)
            
            start_datetime_str = f"{start_date} {start_time}"
            end_datetime_str = f"{end_date} {end_time}"
            
            try:
                # Parse datetime strings
                start_datetime = parser.parse(start_datetime_str)
                end_datetime = parser.parse(end_datetime_str)
                
                # Store values
                current_entry['start_time'] = start_time
                current_entry['end_time'] = end_time
                current_entry['date'] = start_datetime.date()
                current_entry['date_str'] = start_datetime.date().strftime('%Y-%m-%d')
                
                # Calculate hours if not already set
                if 'hours' not in current_entry:
                    time_diff = end_datetime - start_datetime
                    hours = time_diff.total_seconds() / 3600
                    current_entry['hours'] = round(hours, 2)
            except Exception as e:
                print(f"Error parsing datetime: {e}")
            continue
            
        # Extract name
        name_match = re.search(name_pattern, line)
        if name_match and current_entry:
            current_entry['employee_name'] = name_match.group(1)
            continue
    
    # Add the last entry if it exists
    if current_entry and 'order_number' in current_entry and 'date' in current_entry:
        if 'employee_name' not in current_entry:
            current_entry['employee_name'] = 'Current User'
            
        current_entry['format_type'] = 'punch_clocks'
        entries.append(current_entry)
    
    return entries
