import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("ERROR: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version {version.major}.{version.minor} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\nInstalling Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("ERROR: Failed to install dependencies")
        print("Please run: pip install -r backend/requirements.txt")
        return False

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print("\nChecking for Tesseract OCR...")
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        print("✓ Tesseract OCR is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ Tesseract OCR not found")
        print("\nTo install Tesseract:")
        print("- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("- Mac: brew install tesseract")
        print("- Linux: sudo apt-get install tesseract-ocr")
        print("\nThe application will still work, but OCR features will be limited")
        return False

def create_directories():
    """Create necessary directories"""
    print("\nCreating directories...")
    os.makedirs("backend", exist_ok=True)
    print("✓ Directory structure ready")

def main():
    print("Time Tracker Pro - Setup Script")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Check Tesseract
    check_tesseract()
    
    print("\n" + "=" * 40)
    print("Setup completed successfully!")
    print("\nTo run the application:")
    print("1. Double-click run_app.bat")
    print("   OR")
    print("2. Run manually:")
    print("   - cd backend && python app.py")
    print("   - Open index.html in your browser")
    
    input("\nPress Enter to continue...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
