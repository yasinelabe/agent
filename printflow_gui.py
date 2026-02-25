#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrintFlow Desktop Agent - GUI Application
Copyright 2024 Yasin Elabe
License: Proprietary
"""

import os
import sys
import webbrowser
import threading
from pathlib import Path

# Import core agent
from printflow_agent import (
    APP_TITLE, APP_VERSION, APP_AUTHOR,
    config, run_server, NetworkInfo, PrinterManager,
    LOG_PATH, USER_DATA_DIR
)

# GUI imports
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

try:
    import pystray
    from PIL import Image as PilImage, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    PilImage = None


# Color scheme (Odoo-inspired)
PALETTE = {
    'primary': '#714B67',
    'primary_dark': '#5a3c53',
    'accent': '#00A09D',
    'background': '#F8F9FA',
    'surface': '#FFFFFF',
    'text': '#212529',
    'text_muted': '#6C757D',
    'success': '#28A745',
    'error': '#DC3545',
    'border': '#DEE2E6',
}


class PreferencesWindow(tk.Toplevel):
    """Settings dialog."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Preferences')
        self.geometry('400x300')
        self.resizable(False, False)
        self.configure(bg=PALETTE['background'])
        
        self._setup_ui()
        self._center_on_parent(parent)
        self.transient(parent)
        self.grab_set()
    
    def _setup_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Auto-cut setting
        self.auto_cut_var = tk.BooleanVar(value=config.get('enable_auto_cut', False))
        ttk.Checkbutton(
            container,
            text='Enable automatic paper cutting',
            variable=self.auto_cut_var
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Label(
            container,
            text='When enabled, a cut command is sent after each print job.',
            foreground=PALETTE['text_muted'],
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # Port setting
        port_frame = ttk.Frame(container)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text='Server Port:').pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(config.get('port', 5000)))
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(
            container,
            text='Requires restart to take effect.',
            foreground=PALETTE['text_muted'],
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # Start minimized
        self.minimized_var = tk.BooleanVar(value=config.get('start_minimized', False))
        ttk.Checkbutton(
            container,
            text='Start minimized to system tray',
            variable=self.minimized_var
        ).pack(anchor=tk.W, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(
            btn_frame,
            text='Cancel',
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text='Save',
            command=self._save
        ).pack(side=tk.RIGHT)
    
    def _save(self):
        try:
            port = int(self.port_var.get())
            if not (1024 <= port <= 65535):
                raise ValueError('Port must be between 1024 and 65535')
        except ValueError as e:
            messagebox.showerror('Invalid Port', str(e), parent=self)
            return
        
        config.set('enable_auto_cut', self.auto_cut_var.get())
        config.set('port', port)
        config.set('start_minimized', self.minimized_var.get())
        
        messagebox.showinfo(
            'Settings Saved',
            'Your preferences have been saved.',
            parent=self
        )
        self.destroy()
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f'+{x}+{y}')


class LogViewerWindow(tk.Toplevel):
    """Log viewer dialog."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Agent Logs')
        self.geometry('700x500')
        self.configure(bg=PALETTE['background'])
        
        self._setup_ui()
        self._center_on_parent(parent)
        self._load_logs()
        self.transient(parent)
    
    def _setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(toolbar, text='Refresh', command=self._load_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='Open in Editor', command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='Clear Logs', command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            self,
            font=('Consolas', 10),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    def _load_logs(self):
        self.log_text.delete('1.0', tk.END)
        try:
            if LOG_PATH.exists():
                content = LOG_PATH.read_text(encoding='utf-8')
                # Show last 500 lines
                lines = content.split('\n')[-500:]
                self.log_text.insert('1.0', '\n'.join(lines))
                self.log_text.see(tk.END)
            else:
                self.log_text.insert('1.0', 'No log file found.')
        except Exception as e:
            self.log_text.insert('1.0', f'Error reading logs: {e}')
    
    def _open_file(self):
        if LOG_PATH.exists():
            if sys.platform == 'win32':
                os.startfile(LOG_PATH)
            elif sys.platform == 'darwin':
                os.system(f'open "{LOG_PATH}"')
            else:
                os.system(f'xdg-open "{LOG_PATH}"')
    
    def _clear_logs(self):
        if messagebox.askyesno('Clear Logs', 'Delete all log entries?', parent=self):
            try:
                LOG_PATH.write_text('')
                self._load_logs()
            except Exception as e:
                messagebox.showerror('Error', f'Failed to clear logs: {e}', parent=self)
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f'+{x}+{y}')


class AboutWindow(tk.Toplevel):
    """About dialog."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title('About')
        self.geometry('350x250')
        self.resizable(False, False)
        self.configure(bg=PALETTE['surface'])
        
        self._setup_ui()
        self._center_on_parent(parent)
        self.transient(parent)
        self.grab_set()
    
    def _setup_ui(self):
        container = ttk.Frame(self, padding=30)
        container.pack(fill=tk.BOTH, expand=True)
        
        # App name
        ttk.Label(
            container,
            text=APP_TITLE,
            font=('Segoe UI', 18, 'bold'),
            foreground=PALETTE['primary']
        ).pack()
        
        ttk.Label(
            container,
            text=f'Version {APP_VERSION}',
            foreground=PALETTE['text_muted']
        ).pack(pady=(5, 20))
        
        ttk.Label(
            container,
            text='Direct printing solution for Odoo',
            foreground=PALETTE['text']
        ).pack()
        
        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        ttk.Label(
            container,
            text=f'Developed by {APP_AUTHOR}',
            foreground=PALETTE['text']
        ).pack()
        
        ttk.Button(
            container,
            text='Close',
            command=self.destroy
        ).pack(pady=20)
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f'+{x}+{y}')


class PrintFlowApp:
    """Main application window."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry('680x720')
        self.root.minsize(550, 600)
        self.root.configure(bg=PALETTE['background'])
        
        self.tray_icon = None
        self.server_thread = None
        
        self._setup_styles()
        self._setup_ui()
        self._center_window()
        
        # Handle window close
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        
        # Start server
        self._start_server()
        
        # Setup system tray
        if HAS_TRAY:
            self._setup_tray()
        
        # Check if should start minimized
        if config.get('start_minimized', False) and HAS_TRAY:
            self.root.after(100, self._minimize_to_tray)
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure(
            'Card.TFrame',
            background=PALETTE['surface'],
            relief='flat'
        )
        
        # Label styles
        style.configure(
            'Header.TLabel',
            background=PALETTE['primary'],
            foreground='white',
            font=('Segoe UI', 14, 'bold'),
            padding=(15, 10)
        )
        
        style.configure(
            'CardTitle.TLabel',
            background=PALETTE['surface'],
            foreground=PALETTE['text'],
            font=('Segoe UI', 11, 'bold')
        )
        
        style.configure(
            'Status.TLabel',
            background=PALETTE['surface'],
            foreground=PALETTE['success'],
            font=('Segoe UI', 10)
        )
        
        # Button styles
        style.configure(
            'Primary.TButton',
            background=PALETTE['primary'],
            foreground='white',
            font=('Segoe UI', 10)
        )
        
        style.map('Primary.TButton',
            background=[('active', PALETTE['primary_dark'])]
        )
    
    def _setup_ui(self):
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X)
        
        header_label = tk.Label(
            header,
            text=f'  {APP_TITLE}',
            bg=PALETTE['primary'],
            fg='white',
            font=('Segoe UI', 14, 'bold'),
            anchor='w',
            pady=12
        )
        header_label.pack(fill=tk.X)
        
        # Main content area
        content = ttk.Frame(self.root, padding=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Status card
        self._create_status_card(content)
        
        # URLs card
        self._create_urls_card(content)
        
        # Printers card
        self._create_printers_card(content)
        
        # Bottom toolbar
        self._create_toolbar(content)
        
        # Footer
        footer = tk.Label(
            self.root,
            text=f'© 2024 {APP_AUTHOR}  |  Auto-cut: {"ON" if config.get("enable_auto_cut") else "OFF"}',
            bg=PALETTE['background'],
            fg=PALETTE['text_muted'],
            font=('Segoe UI', 9)
        )
        footer.pack(pady=10)
    
    def _create_status_card(self, parent):
        card = self._create_card(parent, 'Server Status')
        
        status_frame = ttk.Frame(card, style='Card.TFrame')
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_indicator = tk.Label(
            status_frame,
            text='●',
            fg=PALETTE['success'],
            bg=PALETTE['surface'],
            font=('Segoe UI', 16)
        )
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(
            status_frame,
            text='Running',
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        port = config.get('port', 5000)
        ttk.Label(
            status_frame,
            text=f'  Port {port}',
            foreground=PALETTE['text_muted']
        ).pack(side=tk.LEFT)
    
    def _create_urls_card(self, parent):
        card = self._create_card(parent, 'Connection URLs')
        
        ttk.Label(
            card,
            text='Use one of these URLs to connect Odoo to this agent:',
            foreground=PALETTE['text_muted']
        ).pack(anchor=tk.W, pady=(0, 8))
        
        # URL listbox
        url_frame = ttk.Frame(card, style='Card.TFrame')
        url_frame.pack(fill=tk.X)
        
        self.url_list = tk.Listbox(
            url_frame,
            height=4,
            font=('Consolas', 10),
            selectbackground=PALETTE['primary'],
            selectforeground='white'
        )
        self.url_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_list.config(yscrollcommand=scrollbar.set)
        
        # Populate URLs
        port = config.get('port', 5000)
        self.url_list.insert(tk.END, f'https://localhost:{port}')
        for ip in NetworkInfo.get_local_addresses():
            self.url_list.insert(tk.END, f'https://{ip}:{port}')
        
        # URL buttons
        url_btns = ttk.Frame(card, style='Card.TFrame')
        url_btns.pack(fill=tk.X, pady=(8, 0))
        
        ttk.Button(url_btns, text='Copy URL', command=self._copy_url).pack(side=tk.LEFT, padx=2)
        ttk.Button(url_btns, text='Open in Browser', command=self._open_url).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(
            card,
            text='Open URL in browser to accept the SSL certificate',
            foreground=PALETTE['accent'],
            font=('Segoe UI', 9, 'italic')
        ).pack(anchor=tk.W, pady=(8, 0))
    
    def _create_printers_card(self, parent):
        card = self._create_card(parent, 'Available Printers')
        
        ttk.Label(
            card,
            text='Copy printer names to paste into Odoo configuration:',
            foreground=PALETTE['text_muted']
        ).pack(anchor=tk.W, pady=(0, 8))
        
        # Printer listbox
        printer_frame = ttk.Frame(card, style='Card.TFrame')
        printer_frame.pack(fill=tk.BOTH, expand=True)
        
        self.printer_list = tk.Listbox(
            printer_frame,
            height=6,
            font=('Consolas', 10),
            selectbackground=PALETTE['primary'],
            selectforeground='white'
        )
        self.printer_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(printer_frame, orient=tk.VERTICAL, command=self.printer_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.printer_list.config(yscrollcommand=scrollbar.set)
        
        # Populate printers
        self._refresh_printers()
        
        # Printer buttons
        printer_btns = ttk.Frame(card, style='Card.TFrame')
        printer_btns.pack(fill=tk.X, pady=(8, 0))
        
        ttk.Button(printer_btns, text='Copy Name', command=self._copy_printer).pack(side=tk.LEFT, padx=2)
        ttk.Button(printer_btns, text='Refresh List', command=self._refresh_printers).pack(side=tk.LEFT, padx=2)
    
    def _create_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(toolbar, text='Preferences', command=self._show_preferences).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='View Logs', command=self._show_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='About', command=self._show_about).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text='Quit', command=self._quit).pack(side=tk.RIGHT, padx=2)
        
        if HAS_TRAY:
            ttk.Button(
                toolbar,
                text='Minimize to Tray',
                command=self._minimize_to_tray
            ).pack(side=tk.RIGHT, padx=2)
    
    def _create_card(self, parent, title):
        """Helper to create a styled card frame."""
        outer = ttk.Frame(parent, style='Card.TFrame')
        outer.pack(fill=tk.X, pady=8)
        
        inner = tk.Frame(
            outer,
            bg=PALETTE['surface'],
            highlightbackground=PALETTE['border'],
            highlightthickness=1
        )
        inner.pack(fill=tk.X, ipadx=12, ipady=10)
        
        ttk.Label(
            inner,
            text=title,
            style='CardTitle.TLabel'
        ).pack(anchor=tk.W)
        
        return inner
    
    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')
    
    def _start_server(self):
        def server_worker():
            try:
                run_server()
            except Exception as e:
                print(f'Server error: {e}')
        
        self.server_thread = threading.Thread(target=server_worker, daemon=True)
        self.server_thread.start()
    
    def _setup_tray(self):
        if not PilImage:
            return
        
        # Create tray icon image
        icon_size = 64
        icon_img = PilImage.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon_img)
        
        # Draw printer shape
        draw.rectangle([8, 16, 56, 48], fill=PALETTE['primary'], outline=None)
        draw.rectangle([16, 8, 48, 20], fill=PALETTE['surface'], outline=PALETTE['primary'])
        draw.rectangle([12, 44, 52, 56], fill=PALETTE['surface'], outline=PALETTE['primary'])
        
        menu = (
            pystray.MenuItem('Show Window', self._show_window, default=True),
            pystray.MenuItem('Open Logs', self._show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self._quit),
        )
        
        self.tray_icon = pystray.Icon(
            APP_TITLE,
            icon_img,
            APP_TITLE,
            menu
        )
        
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def _minimize_to_tray(self):
        if self.tray_icon:
            self.root.withdraw()
    
    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def _copy_url(self):
        selection = self.url_list.curselection()
        if selection:
            url = self.url_list.get(selection[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo('Copied', f'URL copied to clipboard:\n{url}')
    
    def _open_url(self):
        selection = self.url_list.curselection()
        if selection:
            url = self.url_list.get(selection[0])
            webbrowser.open(url)
    
    def _copy_printer(self):
        selection = self.printer_list.curselection()
        if selection:
            printer = self.printer_list.get(selection[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(printer)
            messagebox.showinfo('Copied', f'Printer name copied:\n{printer}')
    
    def _refresh_printers(self):
        self.printer_list.delete(0, tk.END)
        printers = PrinterManager.list_printers()
        
        if printers:
            for p in printers:
                self.printer_list.insert(tk.END, p)
        else:
            self.printer_list.insert(tk.END, '(No printers found)')
    
    def _show_preferences(self):
        PreferencesWindow(self.root)
    
    def _show_logs(self):
        LogViewerWindow(self.root)
    
    def _show_about(self):
        AboutWindow(self.root)
    
    def _on_close(self):
        if HAS_TRAY:
            self._minimize_to_tray()
        else:
            self._quit()
    
    def _quit(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = PrintFlowApp()
    app.run()
