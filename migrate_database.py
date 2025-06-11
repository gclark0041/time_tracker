#!/usr/bin/env python3
"""
Database Migration Script for Time Tracker
Adds missing columns and tables to existing database
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Migrate the database to the latest schema"""
    
    # Get the database path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'time_tracker.db')
    
    print(f"Migrating database: {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create a backup first
        backup_path = os.path.join(current_dir, f'time_tracker_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        cursor.execute("VACUUM INTO ?", (backup_path,))
        print(f"Backup created: {backup_path}")
        
        # Get existing table structure
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing user columns: {user_columns}")
        
        # Add missing columns to user table
        missing_user_columns = {
            'first_name': 'TEXT',
            'last_name': 'TEXT',
            'is_admin': 'BOOLEAN DEFAULT 0',
            'is_manager': 'BOOLEAN DEFAULT 0',
            'manager_id': 'INTEGER',
            'created_at': 'DATETIME',
            'last_login': 'DATETIME',
            'hourly_rate': 'REAL',
            'department': 'TEXT',
            'position': 'TEXT'
        }
        
        for column_name, column_type in missing_user_columns.items():
            if column_name not in user_columns:
                print(f"Adding column {column_name} to user table...")
                cursor.execute(f"ALTER TABLE user ADD COLUMN {column_name} {column_type}")
        
        # Check if app_setting table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_setting'")
        app_setting_exists = cursor.fetchone() is not None
        
        if not app_setting_exists:
            print("Creating app_setting table...")
            cursor.execute("""
                CREATE TABLE app_setting (
                    id INTEGER PRIMARY KEY,
                    key VARCHAR(100) NOT NULL UNIQUE,
                    value TEXT,
                    value_type VARCHAR(20) DEFAULT 'string',
                    section VARCHAR(50) NOT NULL DEFAULT 'general',
                    description VARCHAR(255),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default settings
            default_settings = [
                ('company_name', 'TimeTracker Pro', 'string', 'general', 'Company name'),
                ('default_currency', 'USD', 'string', 'general', 'Default currency'),
                ('timezone', 'America/New_York', 'string', 'general', 'Default timezone'),
                ('enable_desktop_mode', 'false', 'bool', 'general', 'Enable desktop mode'),
                ('work_week_start', '1', 'int', 'time_tracking', 'First day of work week (1=Monday)'),
                ('default_work_hours', '8.0', 'float', 'time_tracking', 'Default work hours per day'),
                ('round_times_to_nearest', 'false', 'bool', 'time_tracking', 'Round times to nearest interval'),
                ('rounding_interval', '15', 'int', 'time_tracking', 'Rounding interval in minutes'),
                ('require_order_number', 'false', 'bool', 'time_tracking', 'Require order number for all entries'),
                ('allow_time_overlap', 'true', 'bool', 'time_tracking', 'Allow overlapping time entries'),
                ('email_notifications', 'false', 'bool', 'notifications', 'Enable email notifications'),
                ('email_from', '', 'string', 'notifications', 'From email address'),
                ('notify_missed_timesheet', 'false', 'bool', 'notifications', 'Notify for missed timesheets'),
                ('notify_managers', 'false', 'bool', 'notifications', 'Notify managers of employee activities'),
                ('session_timeout', '480', 'int', 'security', 'Session timeout in minutes'),
                ('password_policy', 'basic', 'string', 'security', 'Password policy level'),
                ('force_password_reset', 'false', 'bool', 'security', 'Force password reset on first login'),
                ('allow_registration', 'true', 'bool', 'security', 'Allow user self-registration'),
                ('enable_auto_backup', 'false', 'bool', 'backup', 'Enable automatic backups'),
                ('backup_frequency', 'weekly', 'string', 'backup', 'Backup frequency'),
                ('backup_retention', '30', 'int', 'backup', 'Backup retention in days')
            ]
            
            cursor.executemany(
                "INSERT INTO app_setting (key, value, value_type, section, description) VALUES (?, ?, ?, ?, ?)",
                default_settings
            )
            print("Default settings inserted")
        
        # Update existing users to have proper admin status
        cursor.execute("SELECT COUNT(*) FROM user WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            print("No admin users found. Setting first user as admin...")
            cursor.execute("UPDATE user SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM user)")
            cursor.execute("UPDATE user SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        
        # Check if order table needs any updates
        cursor.execute("PRAGMA table_info(order_table)")  # SQLAlchemy might use order_table instead of order
        order_info = cursor.fetchall()
        
        if not order_info:
            # Check if it's named 'order' instead
            cursor.execute("PRAGMA table_info('order')")
            order_info = cursor.fetchall()
        
        if order_info:
            order_columns = [column[1] for column in order_info]
            print(f"Existing order columns: {order_columns}")
            
            # Add missing columns to order table if needed
            if 'user_id' not in order_columns:
                print("Adding user_id column to order table...")
                cursor.execute("ALTER TABLE `order` ADD COLUMN user_id INTEGER")
        
        # Commit all changes
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 