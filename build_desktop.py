"""
Time Tracker Desktop Application Builder
This script creates a standalone Windows desktop application from the Flask web app
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_desktop_app():
    print("Building Time Tracker Desktop Application...")
    
    # Create spec file approach - more reliable than direct PyInstaller command
    print("Creating PyInstaller spec file...")
    
    # First, generate a spec file
    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TimeTracker.spec')
    
    # Path configurations
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Write the spec file manually - this gives us more control and avoids bytecode scanning errors
    with open(spec_file, 'w') as f:
        f.write("""# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the analysis
a = Analysis(
    ['desktop_launcher.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'sqlalchemy.sql.default_comparator',
        'plotly',
        'pandas',
        'werkzeug',
        'flask_wtf.recaptcha',
        'email_validator',
        'flask_login',
        'flask_wtf',
        'flask_sqlalchemy',
        'pytesseract',
        'cv2',
        'dateutil',
        'numpy',
        'waitress',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create the PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the EXE
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TimeTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

# Create the COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TimeTracker',
)
""")
    
    # Run PyInstaller with the spec file
    print("Running PyInstaller with spec file...")
    pyinstaller_cmd = ['pyinstaller', spec_file, '--noconfirm']
    
    try:
        subprocess.run(pyinstaller_cmd, check=True)
        
        # Make sure the uploads directory exists in the output
        build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
        uploads_dir = os.path.join(build_dir, 'TimeTracker', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        print(f"Desktop application built successfully at: {os.path.join(build_dir, 'TimeTracker')}")
        print("You can run the application by executing TimeTracker.exe in that directory.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error running PyInstaller: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if desktop_launcher.py exists
    if not os.path.exists('desktop_launcher.py'):
        print("Error: desktop_launcher.py not found. Please create this file first.")
        sys.exit(1)
        
    # Check if PyInstaller is installed
    try:
        subprocess.run(['pyinstaller', '--version'], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: PyInstaller not found. Please install it with: pip install pyinstaller")
        sys.exit(1)
    
    build_desktop_app()
