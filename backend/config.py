# Configuration file for Time Tracker Pro

# Database settings
DATABASE = {
    'name': 'timetracker.db',
    'backup_enabled': True,
    'backup_interval': 3600  # seconds
}

# Server settings
SERVER = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True
}

# OCR settings
OCR = {
    'engine': 'tesseract',  # Options: 'tesseract', 'google_vision', 'aws_textract'
    'tesseract_path': None,  # Auto-detect if None
    'confidence_threshold': 60,
    'preprocessing': {
        'resize': True,
        'denoise': True,
        'threshold': True
    }
}

# Report settings
REPORTS = {
    'company_name': 'Time Tracker Pro',
    'logo_path': None,
    'default_format': 'pdf',
    'include_charts': True,
    'color_scheme': {
        'primary': '#2563eb',
        'secondary': '#10b981',
        'accent': '#f59e0b'
    }
}

# Time entry settings
TIME_ENTRY = {
    'types': [
        {'value': 'service', 'label': 'Service Order', 'color': '#3b82f6', 'requires_order': True},
        {'value': 'vacation', 'label': 'Vacation', 'color': '#10b981', 'requires_order': False},
        {'value': 'personal', 'label': 'Personal', 'color': '#f59e0b', 'requires_order': False},
        {'value': 'shop', 'label': 'Shop', 'color': '#6366f1', 'requires_order': False},
        {'value': 'nonbillable', 'label': 'Non-Billable', 'color': '#ef4444', 'requires_order': False},
        {'value': 'drive', 'label': 'Drive Time', 'color': '#8b5cf6', 'requires_order': False}
    ],
    'default_type': 'service',
    'allow_future_dates': False,
    'max_hours_per_entry': 24,
    'require_notes': False
}

# UI settings
UI = {
    'theme': 'light',  # Options: 'light', 'dark', 'auto'
    'animations': True,
    'compact_mode': False,
    'date_format': 'MM/DD/YYYY',
    'time_format': '12h',  # Options: '12h', '24h'
    'first_day_of_week': 0  # 0 = Sunday, 1 = Monday
}

# Export settings
EXPORT = {
    'formats': ['pdf', 'excel', 'csv'],
    'include_metadata': True,
    'compress_large_files': True,
    'email_enabled': False,
    'email_smtp': {
        'server': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True
    }
}

# Security settings (for future implementation)
SECURITY = {
    'require_authentication': False,
    'session_timeout': 3600,  # seconds
    'password_min_length': 8,
    'enable_2fa': False,
    'allowed_origins': ['http://localhost:*', 'file://*']
}

# Backup settings
BACKUP = {
    'auto_backup': True,
    'backup_interval': 86400,  # Daily (in seconds)
    'backup_location': './backups',
    'max_backups': 7,
    'compress_backups': True
}

# Integration settings (for future implementation)
INTEGRATIONS = {
    'payroll': {
        'enabled': False,
        'system': None,  # Options: 'quickbooks', 'adp', 'paychex'
        'sync_interval': 3600
    },
    'calendar': {
        'enabled': False,
        'provider': None,  # Options: 'google', 'outlook', 'ical'
        'sync_bidirectional': False
    },
    'project_management': {
        'enabled': False,
        'system': None,  # Options: 'jira', 'asana', 'trello'
        'sync_interval': 1800
    }
}

# Notification settings
NOTIFICATIONS = {
    'enabled': True,
    'types': {
        'entry_saved': True,
        'entry_edited': True,
        'entry_deleted': True,
        'report_generated': True,
        'backup_completed': False,
        'error_occurred': True
    },
    'duration': 3000  # milliseconds
}

# Development settings
DEVELOPMENT = {
    'enable_debug_panel': False,
    'log_api_calls': True,
    'mock_ocr': True,  # Use mock OCR data when Tesseract is not available
    'sample_data_available': True
}
