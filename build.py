#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrintFlow Agent Build Script
Creates standalone executable and installer files.
Copyright 2024 Yasin Elabe
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Pillow is required. Run: pip install Pillow")
    sys.exit(1)

# Configuration
APP_NAME = 'PrintFlow Agent'
APP_FILENAME = 'PrintFlowAgent'
VERSION = '1.0.0'
AUTHOR = 'Yasin Elabe'

SCRIPT_DIR = Path(__file__).parent
DIST_DIR = SCRIPT_DIR / 'dist'
BUILD_DIR = SCRIPT_DIR / 'build'
ICON_PATH = SCRIPT_DIR / 'icon.ico'


def create_application_icon():
    """Generate multi-resolution icon file."""
    print("Creating application icon...")
    
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    
    # Odoo purple color
    primary_color = (113, 75, 103)  # #714B67
    white = (255, 255, 255)
    
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Scale factors
        s = size / 64.0
        
        # Main printer body
        draw.rounded_rectangle(
            [int(8*s), int(18*s), int(56*s), int(46*s)],
            radius=int(3*s),
            fill=primary_color
        )
        
        # Paper output tray
        draw.rectangle(
            [int(14*s), int(42*s), int(50*s), int(54*s)],
            fill=white,
            outline=primary_color,
            width=max(1, int(s))
        )
        
        # Paper input
        draw.rectangle(
            [int(18*s), int(10*s), int(46*s), int(22*s)],
            fill=white,
            outline=primary_color,
            width=max(1, int(s))
        )
        
        # Control panel
        draw.rectangle(
            [int(38*s), int(26*s), int(50*s), int(38*s)],
            fill=white,
            outline=None
        )
        
        # LED indicator
        draw.ellipse(
            [int(42*s), int(28*s), int(48*s), int(34*s)],
            fill=(0, 160, 157)  # Accent color
        )
        
        images.append(img)
    
    # Save as ICO with multiple resolutions
    images[0].save(
        ICON_PATH,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    
    print(f"Icon saved: {ICON_PATH}")
    return ICON_PATH


def run_pyinstaller():
    """Execute PyInstaller to create executable."""
    print("\nBuilding executable with PyInstaller...")
    
    hidden_imports = [
        'flask',
        'flask_cors',
        'werkzeug',
        'jinja2',
        'markupsafe',
        'cryptography',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'pystray',
        'pystray._win32',
        'win32print',
        'win32ui',
        'win32con',
        'win32api',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
    ]
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_FILENAME,
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        f'--icon={ICON_PATH}',
        f'--distpath={DIST_DIR}',
        f'--workpath={BUILD_DIR}',
    ]
    
    for module in hidden_imports:
        cmd.extend(['--hidden-import', module])
    
    cmd.append(str(SCRIPT_DIR / 'printflow_gui.py'))
    
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    
    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(1)
    
    print(f"\nExecutable created: {DIST_DIR / (APP_FILENAME + '.exe')}")


def create_installer_scripts():
    """Generate installer and uninstaller batch files."""
    print("\nCreating installer scripts...")
    
    install_script = f'''@echo off
setlocal enabledelayedexpansion
title {APP_NAME} Installer
color 0B

echo.
echo ============================================
echo        {APP_NAME} Installer
echo        Version {VERSION}
echo ============================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Set installation directory
set "INSTALL_DIR=%ProgramFiles%\\{APP_NAME}"

echo Installing to: %INSTALL_DIR%
echo.

:: Create directories
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy executable
echo Copying files...
copy /y "{APP_FILENAME}.exe" "%INSTALL_DIR%\\{APP_FILENAME}.exe" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy executable!
    pause
    exit /b 1
)

:: Create Start Menu shortcut
echo Creating shortcuts...
set "START_MENU=%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\\{APP_NAME}.lnk'); $s.TargetPath = '%INSTALL_DIR%\\{APP_FILENAME}.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

:: Create Desktop shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\\Desktop\\{APP_NAME}.lnk'); $s.TargetPath = '%INSTALL_DIR%\\{APP_FILENAME}.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

:: Add to Windows Startup
set "STARTUP=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP%\\{APP_NAME}.lnk'); $s.TargetPath = '%INSTALL_DIR%\\{APP_FILENAME}.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

:: Copy uninstaller
copy /y "uninstall.bat" "%INSTALL_DIR%\\uninstall.bat" >nul

echo.
echo ============================================
echo        Installation Complete!
echo ============================================
echo.
echo {APP_NAME} has been installed and will start
echo automatically when Windows starts.
echo.
echo Launch now? [Y/N]
set /p LAUNCH=
if /i "%LAUNCH%"=="Y" start "" "%INSTALL_DIR%\\{APP_FILENAME}.exe"

echo.
pause
'''
    
    uninstall_script = f'''@echo off
title {APP_NAME} Uninstaller
color 0C

echo.
echo ============================================
echo       {APP_NAME} Uninstaller
echo ============================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "INSTALL_DIR=%ProgramFiles%\\{APP_NAME}"

echo This will remove {APP_NAME} from your computer.
echo.
set /p CONFIRM=Are you sure? [Y/N]: 
if /i not "%CONFIRM%"=="Y" exit /b

:: Kill running process
echo Stopping application...
taskkill /F /IM "{APP_FILENAME}.exe" >nul 2>&1

:: Remove files
echo Removing files...
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"

:: Remove shortcuts
del /f "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\{APP_NAME}.lnk" >nul 2>&1
del /f "%USERPROFILE%\\Desktop\\{APP_NAME}.lnk" >nul 2>&1
del /f "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{APP_NAME}.lnk" >nul 2>&1

:: Remove user data (optional)
echo.
set /p REMOVE_DATA=Remove configuration and logs? [Y/N]: 
if /i "%REMOVE_DATA%"=="Y" (
    if exist "%USERPROFILE%\\.printflow" rmdir /s /q "%USERPROFILE%\\.printflow"
)

echo.
echo ============================================
echo        Uninstallation Complete
echo ============================================
echo.
pause
'''
    
    # Save scripts
    (DIST_DIR / 'install.bat').write_text(install_script, encoding='utf-8')
    (DIST_DIR / 'uninstall.bat').write_text(uninstall_script, encoding='utf-8')
    
    print(f"Installer script: {DIST_DIR / 'install.bat'}")
    print(f"Uninstaller script: {DIST_DIR / 'uninstall.bat'}")


def create_readme():
    """Generate installation instructions."""
    readme = f'''# {APP_NAME}

Version {VERSION}
By {AUTHOR}

## Installation

1. Run `install.bat` as Administrator
2. The application will be installed to Program Files
3. Shortcuts will be created on Desktop and Start Menu
4. Application will start automatically with Windows

## Usage

1. Launch {APP_NAME}
2. Copy a URL from the application window
3. Open that URL in your browser to accept the SSL certificate
4. In Odoo, go to Settings > PrintFlow and paste the URL
5. Click "Verify Connection" to test

## Files

- `{APP_FILENAME}.exe` - Main application
- `install.bat` - Installation script (run as admin)
- `uninstall.bat` - Removal script

## Support

For issues or questions, contact: support@yasinelabe.dev
'''
    
    (DIST_DIR / 'README.txt').write_text(readme, encoding='utf-8')
    print(f"README: {DIST_DIR / 'README.txt'}")


def main():
    """Main build process."""
    print(f"\n{'='*50}")
    print(f"  Building {APP_NAME} v{VERSION}")
    print(f"{'='*50}\n")
    
    # Ensure dist directory exists
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create icon
    create_application_icon()
    
    # Build executable
    run_pyinstaller()
    
    # Create installer scripts
    create_installer_scripts()
    
    # Create readme
    create_readme()
    
    print(f"\n{'='*50}")
    print("  Build Complete!")
    print(f"{'='*50}")
    print(f"\nOutput directory: {DIST_DIR}")
    print("\nTo install, copy the 'dist' folder to target machine")
    print("and run install.bat as Administrator.")


if __name__ == '__main__':
    main()
