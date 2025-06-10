# -*- mode: python ; coding: utf-8 -*-

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
