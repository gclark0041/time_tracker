#!/usr/bin/env python3
"""
Populate default settings in the AppSetting table
"""

from app import app, db, AppSetting

def populate_default_settings():
    """Populate the AppSetting table with default values"""
    
    with app.app_context():
        # Default settings
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

        for key, value, value_type, section, description in default_settings:
            # Check if setting already exists
            existing = AppSetting.query.filter_by(key=key).first()
            if not existing:
                AppSetting.set(key, value, value_type, section, description)
                print(f"Added setting: {key} = {value}")
            else:
                print(f"Setting already exists: {key}")

        print('Default settings populated successfully')

if __name__ == "__main__":
    populate_default_settings() 