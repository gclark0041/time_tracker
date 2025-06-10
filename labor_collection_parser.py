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
    
    # Print the full text for debugging
    print("="*80)
    print("FULL LABOR COLLECTION OCR TEXT:")
    print("="*80)
    print(text)
    print("="*80)
        
    entries = []
    lines = text.split('\n')
    
    # Extract employee name from greeting (e.g., "Dear Greg Clark")
    employee_name = "Current User"  # Default name
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        # More flexible name patterns
        name_patterns = [
            r'Dear\s+([A-Za-z]+\s+[A-Za-z]+)',  # "Dear Greg Clark"
            r'Dear ([A-Za-z\.]+\s+[A-Za-z\.]+)',  # With possible periods
            r'[Dd][Ee][Aa][Rr]\s+([A-Za-z]+\s+[A-Za-z]+)', # Case insensitive
            r'To:\s*([A-Za-z]+\s+[A-Za-z]+)'  # "To: Greg Clark"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, line)
            if name_match:
                employee_name = name_match.group(1)
                print(f"Found employee name: {employee_name} using pattern: {pattern}")
                break
        
        # If name found, break the outer loop too
        if employee_name != "Current User":
            break
            
    print(f"Using employee name: {employee_name}")
            
    # Look for the table header that indicates a Labor Collection report - multiple patterns for OCR variations
    header_patterns = [
        r'Order\s+Number\s+Labor\s+Type\s+Start\s+Time\s+End\s+Time\s+Hours',
        r'[Oo]rder\s+[Nn]umber\s+[Ll]abor\s+[Tt]ype\s+[Ss]tart\s+[Tt]ime\s+[Ee]nd\s+[Tt]ime\s+[Hh]ours',
        r'Order.?Number.?Labor.?Type.?Start.?Time.?End.?Time.?Hours'
    ]
    header_found = False
    
    for i, line in enumerate(lines):
        for header_pattern in header_patterns:
            if re.search(header_pattern, line, re.IGNORECASE):
                header_found = True
                print(f"Found Labor Collection report header at line {i}: {line}")
                print(f"Matched pattern: {header_pattern}")
                break
        
        if header_found:
            # Save this as the header line index for later
            header_line_index = i
            continue
            
        if not header_found:
            continue
            
        # Skip lines that don't contain actual entries
        if 'Total Hours' in line or not line.strip():
            continue
            
        # Print the line for debugging
        print(f"Processing line {i}: {line[:50]}{'...' if len(line) > 50 else ''}")
        
        # Enhanced patterns for labor collection entries with variations for OCR errors
        # Order Number, Labor Type, Start Time, End Time, Hours
        # Updated to handle $ being read instead of S
        entry_patterns = [
            # Standard format with exact spacing (handles $ and S)
            r'([$S][O0$][\dO0]{2}-[\dO0]{5}-[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d+)\s+Hours\s+(\d+)\s+Minutes',
            
            # Flexible spacing and punctuation
            r'([$S][O0$][\dO0]{2}.?[\dO0]{5}.?[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}.+?(?:AM|PM))\s+(\d{1,2}/\d{1,2}/\d{4}.+?(?:AM|PM))\s+(\d+).?Hours.?(\d+).?Minutes',
            
            # Very loose pattern for poor OCR
            r'([$S][O0$]\S+)\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}.+?(?:AM|PM))\s+(\d{1,2}/\d{1,2}/\d{4}.+?(?:AM|PM))\s+(\d+)\s+H\w+\s+(\d+)\s+M\w+',
            
            # Split across multiple lines pattern (for table rows that span lines)
            r'([$S][O0$][\dO0]{2}[-.][\dO0]{5}[-.][\dO0]{5})\s+(Regular[Tt]ime|Overtime)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d+)\s+Hours\s+(\d+)\s+Minutes',
            
            # Handle OCR errors in order numbers (0 vs O, $ vs S, etc.)
            r'([SO$][O0$][\dO0]{2}[\-\.][\dO0]{5}[\-\.][\dO0]{5})\s+([\w\s]*Time[\w\s]*)\s+(\d{1,2}/\d{1,2}/\d{4}[\s\d:APM]+)\s+(\d{1,2}/\d{1,2}/\d{4}[\s\d:APM]+)\s+(\d+)[\s\w]*(\d+)[\s\w]*',
            
            # Tab-separated format (in case table columns are preserved)
            r'([$S][O0$][\dO0]{2}[-.][\dO0]{5}[-.][\dO0]{5})\t+([\w\s]+)\t+(\d{1,2}/\d{1,2}/\d{4}[^\t]+)\t+(\d{1,2}/\d{1,2}/\d{4}[^\t]+)\t+(\d+)[^\d]*(\d+)',
            
            # Handle underscores and spacing issues in times/hours
            r'([$S][O0$][\dO0]{2}[-.][\dO0]{5}[-.][\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})_?\s*(\d+)\s+Hours\s+(\d+)\s+Minutes'
        ]
        # Try each pattern until we find a match
        entry_match = None
        matched_pattern = None
        
        for idx, pattern in enumerate(entry_patterns):
            match = re.search(pattern, line)
            if match:
                entry_match = match
                matched_pattern = pattern
                print(f"Matched entry pattern #{idx+1}")
                break
                
        if entry_match:
            try:
                order_number = entry_match.group(1).strip()
                # Clean up order number (replace common OCR errors)
                order_number = re.sub(r'[^A-Z0-9\-]', '', order_number.upper())
                order_number = order_number.replace('$', 'S')  # $ often read as S
                order_number = order_number.replace('O', '0')  # O often read as 0
                
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
            # If we still have no matches, try direct parsing
            if header_found and i > header_line_index and 'SO' in line and ('AM' in line or 'PM' in line):
                print("Attempting direct parsing of line containing order number and times")
                
                # Try to extract order number directly (handle $ as S)
                order_match = re.search(r'([$S][O0$][\dO0]{2}[\-\.][\dO0]{5}[\-\.][\dO0]{5})', line)
                
                # Try to extract times directly
                time_matches = re.findall(r'(\d{1,2}/\d{1,2}/\d{4}[^\d]+?\d{1,2}:\d{2}:\d{2}\s*[APM]{2})', line)
                
                # Try to extract hours directly
                hours_match = re.search(r'(\d+)\s*[Hh]ours?\s+(\d+)\s*[Mm]inutes?', line)
                
                if order_match and len(time_matches) >= 2 and hours_match:
                    print("Direct parsing succeeded!")
                    try:
                        # Create a manual match object
                        order_number = order_match.group(1)
                        # Clean up order number (replace common OCR errors)
                        order_number = re.sub(r'[^A-Z0-9\-]', '', order_number.upper())
                        order_number = order_number.replace('$', 'S')  # $ often read as S
                        order_number = order_number.replace('O', '0')  # O often read as 0
                        
                        start_time_str = time_matches[0]
                        end_time_str = time_matches[1]
                        hours = int(hours_match.group(1))
                        minutes = int(hours_match.group(2))
                        
                        # Parse times
                        start_time = parser.parse(start_time_str)
                        end_time = parser.parse(end_time_str)
                        
                        # Calculate decimal hours
                        decimal_hours = hours + (minutes / 60)
                        
                        entry = {
                            'order_number': order_number,
                            'labor_type': 'RegularTime',  # Default
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
                        print(f"Added entry through direct parsing: {entry}")
                        continue
                    except Exception as e:
                        print(f"Error in direct parsing: {str(e)}")
            
            # Try alternative formats as a last resort
            alt_patterns = [
                r'([$S][O0$][\dO0]{2}-[\dO0]{5}-[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2}).*?(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2}).*?(\d+)\s+Hours\s+(\d+)\s+Minutes',
                r'([$S][O0$][\dO0]{2}[\-\.][\dO0]{5}[\-\.][\dO0]{5}).*?(\d{1,2}/\d{1,2}/\d{4}).*?(\d{1,2}/\d{1,2}/\d{4}).*?(\d+)\s+[Hh]ours?.*?(\d+)\s+[Mm]inutes'
            ]
            
            alt_match = None
            matched_alt_pattern = None
            
            for idx, pattern in enumerate(alt_patterns):
                match = re.search(pattern, line)
                if match:
                    alt_match = match
                    matched_alt_pattern = pattern
                    print(f"Matched alternative pattern #{idx+1}")
                    break
            
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
    
    # If no entries found with standard patterns, try advanced table extraction
    if not entries:
        print("\n⚠️  Standard patterns failed, trying advanced table extraction...")
        entries = extract_table_structure(text)
        
        # Set employee name for all entries if we found it earlier
        if entries and employee_name != "Current User":
            for entry in entries:
                entry['employee_name'] = employee_name
    
    # Log final results
    print(f"\nFinal results: {len(entries)} labor collection entries extracted")
    for i, entry in enumerate(entries, 1):
        print(f"Entry {i}: {entry.get('order_number', 'NO ORDER')} - {entry.get('hours', 0)} hours")
    
    return entries

def extract_table_structure(text):
    """
    Extract table structure from OCR text using advanced pattern matching
    Specifically designed for labor collection reports with tabular data
    """
    if not text:
        return []
    
    print("\n" + "="*50)
    print("ADVANCED TABLE STRUCTURE EXTRACTION")
    print("="*50)
    
    lines = text.split('\n')
    entries = []
    
    # Find table data using column-based approach
    # Look for lines that contain all the key elements: Order number, dates, times, hours
    # Handle common OCR errors: $ instead of S, O vs 0, etc.
    order_pattern = r'([$S][O0$][\dO0]{2}[-.\s]*[\dO0]{5}[-.\s]*[\dO0]{5})'
    date_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
    time_pattern = r'(\d{1,2}:\d{2}(?::\d{2})?\s*[APap][Mm])'
    hours_pattern = r'(\d+)\s*[Hh]ours?\s*(\d+)\s*[Mm]inutes?'
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
            
        print(f"Analyzing line {i}: {line[:80]}{'...' if len(line) > 80 else ''}")
        
        # Check if this line contains the key components of a time entry
        order_match = re.search(order_pattern, line, re.IGNORECASE)
        dates = re.findall(date_pattern, line)
        times = re.findall(time_pattern, line)
        hours_match = re.search(hours_pattern, line, re.IGNORECASE)
        
        if order_match and len(dates) >= 2 and len(times) >= 2 and hours_match:
            print(f"  ✓ Found complete entry on line {i}")
            
            try:
                order_number = order_match.group(1).strip()
                # Clean up order number (replace common OCR errors)
                order_number = re.sub(r'[^A-Z0-9\-]', '', order_number.upper())
                order_number = order_number.replace('$', 'S')  # $ often read as S
                order_number = order_number.replace('O', '0')  # O often read as 0
                
                start_date = dates[0]
                end_date = dates[1] if len(dates) > 1 else dates[0]
                start_time = times[0]
                end_time = times[1] if len(times) > 1 else times[0]
                
                hours = int(hours_match.group(1))
                minutes = int(hours_match.group(2))
                decimal_hours = hours + (minutes / 60)
                
                # Construct full datetime strings
                start_datetime_str = f"{start_date} {start_time}"
                end_datetime_str = f"{end_date} {end_time}"
                
                # Try to parse the datetime to validate
                try:
                    start_dt = parser.parse(start_datetime_str)
                    end_dt = parser.parse(end_datetime_str)
                    
                    entry = {
                        'order_number': order_number,
                        'labor_type': 'RegularTime',  # Default, could be enhanced
                        'start_time': start_datetime_str,
                        'end_time': end_datetime_str,
                        'date': start_dt.date(),
                        'date_str': start_dt.date().strftime('%Y-%m-%d'),
                        'hours': round(decimal_hours, 2),
                        'entry_type': 'service_order',
                        'employee_name': 'Current User',  # Will be set by main parser
                        'format_type': 'labor_collection_table'
                    }
                    
                    entries.append(entry)
                    print(f"  ✓ Successfully parsed entry: {order_number} - {decimal_hours} hours")
                    
                except Exception as parse_error:
                    print(f"  ✗ Failed to parse datetime: {parse_error}")
                    
            except Exception as e:
                print(f"  ✗ Failed to extract entry details: {e}")
        else:
            # Debug: show what was missing
            missing = []
            if not order_match:
                missing.append("order number")
            if len(dates) < 2:
                missing.append(f"dates (found {len(dates)}, need 2)")
            if len(times) < 2:
                missing.append(f"times (found {len(times)}, need 2)")
            if not hours_match:
                missing.append("hours/minutes")
            
            if missing:
                print(f"  - Missing: {', '.join(missing)}")
    
    print(f"\nTable extraction found {len(entries)} entries")
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
