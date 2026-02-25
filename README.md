# PrintFlow Desktop Agent

A lightweight service that enables direct printing from Odoo to local printers.

## Requirements

- Python 3.8+
- Windows 10/11, Linux, or macOS

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. On Windows, also install pywin32:
   ```bash
   pip install pywin32
   ```

3. Run the application:
   ```bash
   python printflow_gui.py
   ```

## Building Standalone Executable

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   python build.py
   ```

3. Find the output in the `dist` folder

## Installation on Target Computer

1. Copy the `dist` folder to the target PC
2. Run `install.bat` as Administrator
3. The agent will start automatically

## Configuration

- **Server Port**: Default is 5000, can be changed in Preferences
- **Auto-Cut**: Enable/disable automatic paper cutting
- **Start Minimized**: Start in system tray

## SSL Certificate

On first run, the agent generates a self-signed SSL certificate.
To use from Odoo:

1. Copy the URL from the agent window
2. Open it in a browser
3. Accept the security warning
4. The certificate is now trusted

## Connecting to Odoo

1. In Odoo, go to Settings > PrintFlow
2. Enter the agent URL (e.g., https://192.168.1.100:5000)
3. Click "Verify Connection"
4. Assign printers to your reports and POS terminals

## Support

Contact: support@yasinelabe.dev

---
Copyright 2024 Yasin Elabe
