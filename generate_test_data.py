import sqlite3
import random
from datetime import datetime, timedelta
import os

# Sample data
EMPLOYEES = ["Greg Clark", "John Smith", "Sarah Johnson", "Mike Wilson", "Emily Davis"]
ORDER_NUMBERS = [
    "SO24-02365-21800", "SO02-11105-21723", "SO24-03421-18900",
    "SO02-12234-20100", "SO24-04567-22300", "SO02-13345-19800"
]
ENTRY_TYPES = ["service", "vacation", "personal", "shop", "nonbillable", "drive"]

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect('backend/timetracker.db')
    c = conn.cursor()
    
    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            order_number TEXT,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            elapsed_time TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    return conn

def generate_random_entry(base_date):
    """Generate a random time entry"""
    employee = random.choice(EMPLOYEES)
    entry_type = random.choice(ENTRY_TYPES)
    
    # Service orders need order numbers
    order_number = ""
    if entry_type == "service":
        order_number = random.choice(ORDER_NUMBERS)
    
    # Random start time within the day
    hour = random.randint(6, 16)  # 6 AM to 4 PM
    minute = random.choice([0, 15, 30, 45])
    start = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Random duration (1-9 hours)
    duration_hours = random.randint(1, 9)
    duration_minutes = random.choice([0, 15, 30, 45])
    end = start + timedelta(hours=duration_hours, minutes=duration_minutes)
    
    # Calculate elapsed time
    elapsed = end - start
    hours = int(elapsed.total_seconds() // 3600)
    minutes = int((elapsed.total_seconds() % 3600) // 60)
    elapsed_time = f"{hours:02d}h:{minutes:02d}m:00s"
    
    # Random notes
    notes_options = [
        "Regular work day",
        "Completed installation",
        "Customer service call",
        "Equipment maintenance",
        "Training session",
        "Project planning",
        ""
    ]
    notes = random.choice(notes_options)
    
    return {
        'employee_name': employee,
        'entry_type': entry_type,
        'order_number': order_number,
        'start_datetime': start.isoformat(),
        'end_datetime': end.isoformat(),
        'elapsed_time': elapsed_time,
        'notes': notes,
        'created_at': datetime.now().isoformat()
    }

def populate_test_data(conn, num_days=30, entries_per_day=3):
    """Populate the database with test data"""
    c = conn.cursor()
    
    # Clear existing data
    c.execute('DELETE FROM time_entries')
    
    # Generate entries for the past num_days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    
    current_date = start_date
    total_entries = 0
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # Generate random number of entries for this day
            num_entries = random.randint(1, entries_per_day)
            
            for _ in range(num_entries):
                entry = generate_random_entry(current_date)
                
                c.execute('''
                    INSERT INTO time_entries 
                    (employee_name, entry_type, order_number, start_datetime, 
                     end_datetime, elapsed_time, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry['employee_name'],
                    entry['entry_type'],
                    entry['order_number'],
                    entry['start_datetime'],
                    entry['end_datetime'],
                    entry['elapsed_time'],
                    entry['notes'],
                    entry['created_at']
                ))
                
                total_entries += 1
        
        current_date += timedelta(days=1)
    
    conn.commit()
    return total_entries

def display_summary(conn):
    """Display a summary of the generated data"""
    c = conn.cursor()
    
    # Total entries
    c.execute('SELECT COUNT(*) FROM time_entries')
    total = c.fetchone()[0]
    
    # Entries by employee
    print("\nEntries by Employee:")
    c.execute('''
        SELECT employee_name, COUNT(*) as count 
        FROM time_entries 
        GROUP BY employee_name 
        ORDER BY count DESC
    ''')
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} entries")
    
    # Entries by type
    print("\nEntries by Type:")
    c.execute('''
        SELECT entry_type, COUNT(*) as count 
        FROM time_entries 
        GROUP BY entry_type 
        ORDER BY count DESC
    ''')
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} entries")
    
    # Recent entries
    print("\nMost Recent Entries:")
    c.execute('''
        SELECT employee_name, entry_type, start_datetime 
        FROM time_entries 
        ORDER BY start_datetime DESC 
        LIMIT 5
    ''')
    for row in c.fetchall():
        start = datetime.fromisoformat(row[2])
        print(f"  {row[0]} - {row[1]} - {start.strftime('%Y-%m-%d %H:%M')}")

def main():
    print("Time Tracker Pro - Test Data Generator")
    print("=" * 40)
    
    # Check if backend directory exists
    if not os.path.exists('backend'):
        print("ERROR: backend directory not found")
        print("Please run this script from the project root directory")
        return 1
    
    # Initialize database
    conn = init_db()
    
    # Ask user for preferences
    print("\nThis will generate test data for the Time Tracker application.")
    print("WARNING: This will DELETE all existing data!\n")
    
    confirm = input("Continue? (yes/no): ").lower()
    if confirm != 'yes':
        print("Cancelled.")
        return 0
    
    try:
        num_days = int(input("\nNumber of days to generate (default 30): ") or "30")
        entries_per_day = int(input("Max entries per day (default 5): ") or "5")
    except ValueError:
        print("Invalid input. Using defaults.")
        num_days = 30
        entries_per_day = 5
    
    print(f"\nGenerating data for {num_days} days...")
    
    # Generate test data
    total = populate_test_data(conn, num_days, entries_per_day)
    
    print(f"\n✓ Generated {total} time entries")
    
    # Display summary
    display_summary(conn)
    
    conn.close()
    
    print("\n" + "=" * 40)
    print("Test data generated successfully!")
    print("\nYou can now run the application and see the test data.")
    
    input("\nPress Enter to continue...")
    return 0

if __name__ == "__main__":
    main()
