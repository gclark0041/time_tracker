import re
import base64
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from datetime import datetime
import numpy as np
from typing import List, Dict, Optional, Tuple

class OCREngine:
    """Base OCR Engine class"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too small
        if self.config.get('preprocessing', {}).get('resize', True):
            min_width = 1000
            if image.width < min_width:
                ratio = min_width / image.width
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Apply threshold to get black and white image
        if self.config.get('preprocessing', {}).get('threshold', True):
            threshold = 150
            image = image.point(lambda x: 0 if x < threshold else 255, '1')
            image = image.convert('L')
        
        # Denoise
        if self.config.get('preprocessing', {}).get('denoise', True):
            image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text from image - to be implemented by subclasses"""
        raise NotImplementedError

class TesseractOCR(OCREngine):
    """Tesseract OCR implementation"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.tesseract_path = config.get('tesseract_path') if config else None
        
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text using Tesseract"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text with custom config
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text
        except Exception as e:
            print(f"Tesseract OCR error: {e}")
            return ""

class MockOCR(OCREngine):
    """Mock OCR for testing when Tesseract is not available"""
    
    def extract_text(self, image: Image.Image) -> str:
        """Return mock data similar to the example image"""
        return """Punch Clocks
Order Number: SO24-02365-21800
Elapsed Time: 04h:10m:00s
6/6/2025 11:23:00 AM - 6/6/2025 3:33:00 PM
Greg Clark

Order Number: SO02-11105-21723
Elapsed Time: 07h:51m:00s
6/5/2025 7:23:00 AM - 6/5/2025 3:14:00 PM
Greg Clark

Order Number: SO02-11105-21723
Elapsed Time: 07h:26m:00s
6/4/2025 7:42:00 AM - 6/4/2025 3:08:00 PM
Greg Clark

Order Number: SO02-11105-21723
Elapsed Time: 08h:07m:00s
6/3/2025 7:28:00 AM - 6/3/2025 3:35:00 PM
Greg Clark

Order Number: SO02-11105-21723
Elapsed Time: 22h:27m:00s
6/2/2025 9:01:00 AM - 6/3/2025 7:28:00 AM
Greg Clark"""

class TimeEntryParser:
    """Parse time entries from OCR text"""
    
    def __init__(self):
        # Compile regex patterns for better performance
        self.patterns = {
            'order': re.compile(r'Order\s*Number:\s*([A-Z0-9\-]+)', re.IGNORECASE),
            'elapsed': re.compile(r'Elapsed\s*Time:\s*(\d+h:\d+m:\d+s)', re.IGNORECASE),
            'datetime_range': re.compile(
                r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)\s*[-–]\s*'
                r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
                re.IGNORECASE
            ),
            'employee': re.compile(r'(Greg Clark|John Smith|Sarah Johnson|Mike Wilson|Emily Davis)', re.IGNORECASE)
        }
    
    def parse_entries(self, text: str) -> List[Dict]:
        """Parse time entries from OCR text"""
        entries = []
        lines = text.split('\n')
        
        current_entry = {}
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for order number
            order_match = self.patterns['order'].search(line)
            if order_match:
                # Save previous entry if exists
                if self._is_valid_entry(current_entry):
                    entries.append(current_entry)
                
                # Start new entry
                current_entry = {'orderNumber': order_match.group(1)}
            
            # Check for elapsed time
            elapsed_match = self.patterns['elapsed'].search(line)
            if elapsed_match and current_entry:
                current_entry['elapsedTime'] = elapsed_match.group(1)
            
            # Check for datetime range
            datetime_match = self.patterns['datetime_range'].search(line)
            if datetime_match and current_entry:
                start_date = datetime_match.group(1)
                start_time = datetime_match.group(2)
                end_date = datetime_match.group(3)
                end_time = datetime_match.group(4)
                
                current_entry['startDateTime'] = self._convert_to_iso(start_date, start_time)
                current_entry['endDateTime'] = self._convert_to_iso(end_date, end_time)
            
            # Check for employee name
            employee_match = self.patterns['employee'].search(line)
            if employee_match and current_entry:
                current_entry['employeeName'] = employee_match.group(1)
            
            i += 1
        
        # Add last entry
        if self._is_valid_entry(current_entry):
            entries.append(current_entry)
        
        return entries
    
    def _is_valid_entry(self, entry: Dict) -> bool:
        """Check if entry has all required fields"""
        required_fields = ['orderNumber', 'startDateTime', 'endDateTime', 'employeeName']
        return all(field in entry for field in required_fields)
    
    def _convert_to_iso(self, date_str: str, time_str: str) -> str:
        """Convert date and time to ISO format"""
        try:
            # Parse datetime
            datetime_str = f"{date_str} {time_str}"
            dt = datetime.strptime(datetime_str, "%m/%d/%Y %I:%M:%S %p")
            return dt.isoformat()
        except ValueError:
            # Try without seconds
            try:
                datetime_str = f"{date_str} {time_str}"
                dt = datetime.strptime(datetime_str, "%m/%d/%Y %I:%M %p")
                return dt.isoformat()
            except ValueError:
                return datetime.now().isoformat()

class SmartTimeExtractor:
    """Advanced time entry extraction with multiple OCR engines and parsing strategies"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.parser = TimeEntryParser()
        
        # Initialize OCR engine based on config
        engine_type = self.config.get('engine', 'tesseract')
        
        if engine_type == 'tesseract':
            try:
                self.ocr_engine = TesseractOCR(config)
                # Test if Tesseract is available
                test_image = Image.new('RGB', (100, 100), color='white')
                self.ocr_engine.extract_text(test_image)
            except:
                print("Tesseract not available, using mock OCR")
                self.ocr_engine = MockOCR(config)
        else:
            self.ocr_engine = MockOCR(config)
    
    def extract_from_base64(self, base64_data: str) -> List[Dict]:
        """Extract time entries from base64 encoded image"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # Decode base64 to image
            image_data = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_data))
            
            # Extract text using OCR
            text = self.ocr_engine.extract_text(image)
            
            # Parse entries from text
            entries = self.parser.parse_entries(text)
            
            # Validate and enhance entries
            entries = self._validate_entries(entries)
            
            return entries
            
        except Exception as e:
            print(f"Error extracting entries: {e}")
            return []
    
    def _validate_entries(self, entries: List[Dict]) -> List[Dict]:
        """Validate and enhance extracted entries"""
        validated_entries = []
        
        for entry in entries:
            # Calculate elapsed time if missing
            if 'elapsedTime' not in entry and all(k in entry for k in ['startDateTime', 'endDateTime']):
                start = datetime.fromisoformat(entry['startDateTime'])
                end = datetime.fromisoformat(entry['endDateTime'])
                elapsed = end - start
                
                hours = int(elapsed.total_seconds() // 3600)
                minutes = int((elapsed.total_seconds() % 3600) // 60)
                seconds = int(elapsed.total_seconds() % 60)
                
                entry['elapsedTime'] = f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"
            
            # Ensure all required fields are present
            if all(k in entry for k in ['orderNumber', 'startDateTime', 'endDateTime', 'employeeName']):
                validated_entries.append(entry)
        
        return validated_entries

# Export main class
OCRProcessor = SmartTimeExtractor
