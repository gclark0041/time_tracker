#!/usr/bin/env python3
"""
Test the admin settings functionality
"""

from app import app, db, AppSetting

def test_admin_settings():
    """Test the admin settings functionality that was causing errors"""
    
    with app.app_context():
        print("Testing admin settings functionality...")
        
        # Test the exact code from the admin_settings route
        settings = {}
        for section in ['general', 'time_tracking', 'notifications', 'security', 'backup']:
            section_settings = AppSetting.get_all_by_section(section)
            settings.update(section_settings)
            print(f"Section '{section}': found {len(section_settings)} settings")
        
        print(f"Total settings found: {len(settings)}")
        print("Sample settings:")
        for key, value in list(settings.items())[:5]:
            print(f"  {key}: {value}")
        
        print("✅ Admin settings functionality test passed!")

if __name__ == "__main__":
    test_admin_settings() 