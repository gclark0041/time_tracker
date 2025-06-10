#!/usr/bin/env python3
"""
OCR Testing Utility for Time Tracker App
Supports testing both mobile app screenshots and labor collection reports
"""

import os
import sys
from image_processor import parse_image_for_time_entries

def test_image_formats():
    """Test different image formats with the enhanced OCR system"""
    
    print("=" * 80)
    print("TIME TRACKER OCR TESTING UTILITY")
    print("=" * 80)
    
    # Test images (you'll need to place your images here)
    test_images = {
        'mobile_app': {
            'path': 'test_mobile_screenshot.png',  # Replace with your mobile screenshot
            'format': 'punch_clocks',
            'description': 'Mobile app screenshot (Punch Clocks format)'
        },
        'labor_collection': {
            'path': 'test_labor_collection.png',   # Replace with your labor collection image
            'format': 'labor_collection',
            'description': 'Labor collection report document'
        }
    }
    
    for test_name, test_config in test_images.items():
        print(f"\n{'='*60}")
        print(f"TESTING: {test_config['description']}")
        print(f"File: {test_config['path']}")
        print(f"Format: {test_config['format']}")
        print(f"{'='*60}")
        
        if not os.path.exists(test_config['path']):
            print(f"❌ Test image not found: {test_config['path']}")
            print(f"   Please add your {test_config['description'].lower()} to this location")
            continue
        
        try:
            # Test with the specified format
            print(f"\n🔍 Processing with format: {test_config['format']}")
            entries = parse_image_for_time_entries(test_config['path'], test_config['format'])
            
            if entries:
                print(f"✅ SUCCESS: Extracted {len(entries)} time entries")
                for i, entry in enumerate(entries, 1):
                    print(f"\n   Entry {i}:")
                    print(f"   - Order Number: {entry.get('order_number', 'N/A')}")
                    print(f"   - Employee: {entry.get('employee_name', 'N/A')}")
                    print(f"   - Date: {entry.get('date_str', entry.get('date', 'N/A'))}")
                    print(f"   - Hours: {entry.get('hours', 'N/A')}")
                    print(f"   - Start Time: {entry.get('start_time', 'N/A')}")
                    print(f"   - End Time: {entry.get('end_time', 'N/A')}")
                    if 'labor_type' in entry:
                        print(f"   - Labor Type: {entry['labor_type']}")
            else:
                print(f"❌ FAILED: No entries extracted")
                
                # Try with generic format as fallback
                print(f"\n🔄 Trying generic format as fallback...")
                fallback_entries = parse_image_for_time_entries(test_config['path'], 'generic')
                if fallback_entries:
                    print(f"✅ FALLBACK SUCCESS: Extracted {len(fallback_entries)} entries with generic format")
                    for i, entry in enumerate(fallback_entries, 1):
                        print(f"\n   Entry {i}:")
                        for key, value in entry.items():
                            print(f"   - {key}: {value}")
                else:
                    print(f"❌ FALLBACK FAILED: No entries extracted with generic format")
        
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print("=" * 80)

def test_single_image(image_path, format_type='auto'):
    """Test a single image with specified format"""
    
    print(f"\n{'='*60}")
    print(f"TESTING SINGLE IMAGE")
    print(f"File: {image_path}")
    print(f"Format: {format_type}")
    print(f"{'='*60}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    try:
        entries = parse_image_for_time_entries(image_path, format_type)
        
        if entries:
            print(f"✅ SUCCESS: Extracted {len(entries)} time entries")
            for i, entry in enumerate(entries, 1):
                print(f"\n   Entry {i}:")
                for key, value in entry.items():
                    if key not in ['from_demo']:  # Skip demo flags
                        print(f"   - {key}: {value}")
        else:
            print(f"❌ FAILED: No entries extracted")
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test single image mode
        image_path = sys.argv[1]
        format_type = sys.argv[2] if len(sys.argv) > 2 else 'auto'
        test_single_image(image_path, format_type)
    else:
        # Test all configured formats
        test_image_formats()
        
        print("\n" + "="*80)
        print("USAGE EXAMPLES:")
        print("="*80)
        print("Test specific image:")
        print("  python test_ocr.py path/to/image.png")
        print("  python test_ocr.py path/to/image.png labor_collection")
        print("  python test_ocr.py path/to/image.png punch_clocks")
        print()
        print("Available formats: auto, punch_clocks, labor_collection, generic")
        print("="*80) 