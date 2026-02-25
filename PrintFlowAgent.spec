# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Program Files\\Odoo 18.0.20250930\\server\\addons\\print_direct_odoo\\agent\\printflow_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['flask', 'flask_cors', 'werkzeug', 'jinja2', 'markupsafe', 'cryptography', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'pystray', 'pystray._win32', 'win32print', 'win32ui', 'win32con', 'win32api', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PrintFlowAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Program Files\\Odoo 18.0.20250930\\server\\addons\\print_direct_odoo\\agent\\icon.ico'],
)
