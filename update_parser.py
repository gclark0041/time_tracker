"""
Utility script to update the labor_collection_parser.py file with improved patterns
"""
import re

def update_labor_collection_parser():
    """Update the labor_collection_parser.py file with better extraction patterns"""
    # Read the current content
    with open('labor_collection_parser.py', 'r') as file:
        content = file.read()
    
    # Find and replace the pattern for labor collection entries
    old_pattern = r'entry_pattern = r\'([A-Z0-9\-]+)\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d+)\s+Hours\s+(\d+)\s+Minutes\''
    new_pattern = r'entry_pattern = r\'(S[O0][\dO0]{2}-[\dO0]{5}-[\dO0]{5})\s+([\w\s]+)\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[APM]{2})\s+(\d+)\s+Hours\s+(\d+)\s+Minutes\''
    
    content = re.sub(old_pattern, new_pattern, content)
    
    # Add employee name detection at the beginning of the file
    employee_detection = """    # Look for employee name in the header text
    employee_name = "Current User"  # Default
    name_pattern = r'Dear\\s+([A-Z][a-z]+\\s+[A-Z][a-z]+)'
    for line in lines[:10]:  # Check first 10 lines for greeting
        name_match = re.search(name_pattern, line)
        if name_match:
            employee_name = name_match.group(1)
            print(f"Found employee name: {employee_name}")
            break
"""
    
    # Insert employee detection before the header pattern search
    if "# Look for the table header that indicates a Labor Collection report" in content:
        content = content.replace(
            "# Look for the table header that indicates a Labor Collection report", 
            employee_detection + "\n    # Look for the table header that indicates a Labor Collection report"
        )
    
    # Update the entry creation to use extracted employee name
    old_entry_creation = """                entry = {
                    'order_number': order_number,
                    'labor_type': labor_type,
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'date': start_time.date(),
                    'date_str': start_time.date().strftime('%Y-%m-%d'),
                    'hours': round(decimal_hours, 2),
                    'entry_type': 'service_order',
                    'employee_name': 'Current User',  # Will be replaced with logged-in user
                    'format_type': 'labor_collection'
                }"""
                
    new_entry_creation = """                entry = {
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
                }"""
    
    content = content.replace(old_entry_creation, new_entry_creation)
    
    # Also update the alternative pattern match entry creation
    content = content.replace("'employee_name': 'Current User',", f"'employee_name': employee_name,")
    
    # Write the updated content back to the file
    with open('labor_collection_parser.py', 'w') as file:
        file.write(content)
    
    print("Updated labor_collection_parser.py with improved patterns")

if __name__ == "__main__":
    update_labor_collection_parser()
