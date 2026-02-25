#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrintFlow Desktop Agent
Copyright 2024 Yasin Elabe
License: Proprietary

A lightweight printing service that connects Odoo to local printers.
"""

import os
import sys
import json
import base64
import socket
import logging
import tempfile
import platform
import subprocess
import ipaddress
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone, timedelta
from threading import Thread

from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from PIL import Image
except ImportError:
    Image = None

# Platform-specific imports
SYSTEM = platform.system()
if SYSTEM == 'Windows':
    try:
        import win32print
        import win32ui
        from PIL import ImageWin
    except ImportError:
        win32print = None

# Application metadata
APP_TITLE = 'PrintFlow Agent'
APP_VERSION = '1.0.0'
APP_AUTHOR = 'Yasin Elabe'

# Paths
USER_DATA_DIR = Path.home() / '.printflow'
CONFIG_PATH = USER_DATA_DIR / 'config.json'
LOG_PATH = USER_DATA_DIR / 'agent.log'
CERT_PATH = USER_DATA_DIR / 'server.crt'
KEY_PATH = USER_DATA_DIR / 'server.key'

# Ensure data directory exists
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('printflow')

# ESC/POS constants
ESCPOS_INIT = b'\x1B\x40'
ESCPOS_LINEFEED = b'\x0A'
ESCPOS_CUT = b'\x1D\x56\x00'
ESCPOS_RASTER_START = b'\x1D\x76\x30\x00'


class Configuration:
    """Manages application settings."""
    
    DEFAULT_SETTINGS = {
        'port': 5000,
        'enable_auto_cut': False,
        'start_minimized': False,
        'log_level': 'INFO',
    }
    
    def __init__(self):
        self._settings = self.DEFAULT_SETTINGS.copy()
        self._load()
    
    def _load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    saved = json.load(f)
                self._settings.update(saved)
            except Exception as e:
                logger.warning(f'Failed to load config: {e}')
    
    def save(self):
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error(f'Failed to save config: {e}')
    
    def get(self, key, default=None):
        return self._settings.get(key, default)
    
    def set(self, key, value):
        self._settings[key] = value
        self.save()


class CertificateManager:
    """Handles SSL certificate generation."""
    
    @staticmethod
    def generate():
        """Create self-signed SSL certificate."""
        if CERT_PATH.exists() and KEY_PATH.exists():
            logger.info('Using existing SSL certificate')
            return str(CERT_PATH), str(KEY_PATH)
        
        logger.info('Generating new SSL certificate...')
        
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Build certificate
            hostname = socket.gethostname()
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, APP_TITLE),
            ])
            
            # Get all valid IP addresses
            alt_names = [
                x509.DNSName('localhost'),
                x509.DNSName(hostname),
                x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')),
            ]
            
            for ip in NetworkInfo.get_local_addresses():
                try:
                    alt_names.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
                except:
                    pass
            
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(timezone.utc))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
                .add_extension(
                    x509.SubjectAlternativeName(alt_names),
                    critical=False
                )
                .sign(private_key, hashes.SHA256(), default_backend())
            )
            
            # Save certificate
            with open(CERT_PATH, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Save private key
            with open(KEY_PATH, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info('SSL certificate generated successfully')
            return str(CERT_PATH), str(KEY_PATH)
            
        except ImportError:
            logger.warning('cryptography library not available, trying OpenSSL')
            return CertificateManager._generate_with_openssl()
    
    @staticmethod
    def _generate_with_openssl():
        """Fallback certificate generation using OpenSSL CLI."""
        hostname = socket.gethostname()
        ips = ','.join([f'IP:{ip}' for ip in NetworkInfo.get_local_addresses()])
        
        cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', str(KEY_PATH),
            '-out', str(CERT_PATH),
            '-days', '3650',
            '-nodes',
            '-subj', f'/CN={hostname}/O={APP_TITLE}',
            '-addext', f'subjectAltName=DNS:localhost,DNS:{hostname},IP:127.0.0.1,{ips}'
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info('SSL certificate generated via OpenSSL')
            return str(CERT_PATH), str(KEY_PATH)
        except Exception as e:
            logger.error(f'OpenSSL certificate generation failed: {e}')
            raise


class NetworkInfo:
    """Network utility functions."""
    
    @staticmethod
    def get_local_addresses():
        """Get all local IP addresses."""
        addresses = []
        hostname = socket.gethostname()
        
        # Get hostname-based IP
        try:
            addresses.append(socket.gethostbyname(hostname))
        except:
            pass
        
        # Get interface IPs
        try:
            import subprocess
            if SYSTEM == 'Windows':
                result = subprocess.run(
                    ['powershell', '-Command', 
                     '(Get-NetIPAddress -AddressFamily IPv4).IPAddress'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    ip = line.strip()
                    if ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
                        addresses.append(ip)
            else:
                result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True, text=True
                )
                for ip in result.stdout.strip().split():
                    if ip and not ip.startswith('127.'):
                        addresses.append(ip)
        except:
            pass
        
        # Get default route IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            addresses.append(s.getsockname()[0])
            s.close()
        except:
            pass
        
        return list(set(addresses))


class PrinterManager:
    """Handles printer discovery and print jobs."""
    
    @staticmethod
    def list_printers():
        """Get available printers on the system."""
        printers = []
        
        if SYSTEM == 'Windows' and win32print:
            try:
                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                for printer in win32print.EnumPrinters(flags):
                    printers.append(printer[2])
            except Exception as e:
                logger.error(f'Failed to enumerate Windows printers: {e}')
        
        elif SYSTEM in ('Linux', 'Darwin'):
            try:
                result = subprocess.run(
                    ['lpstat', '-p'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('printer'):
                        parts = line.split()
                        if len(parts) >= 2:
                            printers.append(parts[1])
            except Exception as e:
                logger.error(f'Failed to enumerate CUPS printers: {e}')
        
        return printers
    
    @staticmethod
    def print_raw(printer_name, data, with_cut=False):
        """Send raw bytes to printer."""
        if SYSTEM == 'Windows' and win32print:
            return PrinterManager._print_raw_windows(printer_name, data, with_cut)
        elif SYSTEM in ('Linux', 'Darwin'):
            return PrinterManager._print_raw_cups(printer_name, data, with_cut)
        else:
            raise RuntimeError(f'Unsupported platform: {SYSTEM}')
    
    @staticmethod
    def _print_raw_windows(printer_name, data, with_cut):
        """Windows raw printing via win32print."""
        if with_cut:
            data = data + ESCPOS_CUT
        
        try:
            handle = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(handle, 1, ('PrintFlow Job', None, 'RAW'))
                try:
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, data)
                    win32print.EndPagePrinter(handle)
                finally:
                    win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
            return True
        except Exception as e:
            logger.error(f'Windows print failed: {e}')
            raise
    
    @staticmethod
    def _print_raw_cups(printer_name, data, with_cut):
        """Linux/macOS raw printing via CUPS."""
        if with_cut:
            data = data + ESCPOS_CUT
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.raw') as f:
                f.write(data)
                temp_path = f.name
            
            cmd = ['lp', '-d', printer_name, '-o', 'raw', temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            os.unlink(temp_path)
            
            if result.returncode != 0:
                raise RuntimeError(result.stderr or 'lp command failed')
            
            return True
        except Exception as e:
            logger.error(f'CUPS print failed: {e}')
            raise
    
    @staticmethod
    def print_image(printer_name, image_data, with_cut=False):
        """Print image by converting to ESC/POS raster."""
        if not Image:
            raise RuntimeError('Pillow library not available')
        
        # Decode and process image
        img = Image.open(BytesIO(image_data))
        
        # Convert to grayscale then monochrome
        img = img.convert('L')
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Resize to printer width (typically 576 pixels for 80mm paper)
        max_width = 576
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        # Convert to ESC/POS raster format
        raster_data = PrinterManager._image_to_raster(img)
        
        # Combine with cut command if needed
        output = ESCPOS_INIT + raster_data
        if with_cut:
            output += ESCPOS_CUT
        
        return PrinterManager.print_raw(printer_name, output, with_cut=False)
    
    @staticmethod
    def _image_to_raster(img):
        """Convert PIL Image to ESC/POS raster bytes."""
        width = img.width
        height = img.height
        
        # Width must be multiple of 8
        padded_width = ((width + 7) // 8) * 8
        
        if padded_width != width:
            new_img = Image.new('1', (padded_width, height), 1)
            new_img.paste(img, (0, 0))
            img = new_img
        
        bytes_per_row = padded_width // 8
        
        # Build raster command
        width_low = bytes_per_row % 256
        width_high = bytes_per_row // 256
        height_low = height % 256
        height_high = height // 256
        
        raster_header = ESCPOS_RASTER_START + bytes([width_low, width_high, height_low, height_high])
        
        # Get image data
        pixels = img.load()
        raster_body = bytearray()
        
        for y in range(height):
            row_byte = 0
            bit_pos = 7
            
            for x in range(padded_width):
                if x < width and pixels[x, y] == 0:
                    row_byte |= (1 << bit_pos)
                
                bit_pos -= 1
                
                if bit_pos < 0:
                    raster_body.append(row_byte)
                    row_byte = 0
                    bit_pos = 7
        
        return raster_header + bytes(raster_body)


# Flask application
app = Flask(__name__)
CORS(app)

# Global config instance
config = Configuration()


@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint."""
    return jsonify({
        'status': 'online',
        'application': APP_TITLE,
        'version': APP_VERSION,
        'printers': PrinterManager.list_printers(),
        'platform': SYSTEM,
    })


@app.route('/printers', methods=['GET'])
def list_printers():
    """List available printers."""
    return jsonify({
        'printers': PrinterManager.list_printers()
    })


@app.route('/print_raw', methods=['POST'])
def handle_print():
    """Process incoming print job."""
    try:
        payload = request.get_json()
        
        printer_name = payload.get('printer_name')
        raw_type = payload.get('raw_type', 'text')
        raw_data = payload.get('raw_data', '')
        
        if not printer_name:
            return jsonify({'error': 'Missing printer_name'}), 400
        
        if not raw_data:
            return jsonify({'error': 'Missing raw_data'}), 400
        
        # Decode base64 data
        data_bytes = base64.b64decode(raw_data)
        
        # Determine if auto-cut should be applied
        auto_cut = config.get('enable_auto_cut', False)
        apply_cut = auto_cut or raw_type.endswith('_cut')
        
        # Process based on type
        if raw_type in ('image', 'image_cut'):
            PrinterManager.print_image(printer_name, data_bytes, with_cut=apply_cut)
        elif raw_type == 'pdf':
            # PDF printing handled differently per platform
            if SYSTEM == 'Windows':
                # Save and print via shell
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                    f.write(data_bytes)
                    temp_path = f.name
                
                subprocess.run([
                    'powershell', '-Command',
                    f'Start-Process -FilePath "{temp_path}" -Verb Print'
                ])
            else:
                PrinterManager.print_raw(printer_name, data_bytes, with_cut=False)
        else:
            # Text/raw mode
            PrinterManager.print_raw(printer_name, data_bytes, with_cut=apply_cut)
        
        logger.info(f'Print job sent: {printer_name} ({raw_type}, {len(data_bytes)} bytes)')
        
        return jsonify({
            'success': True,
            'message': f'Printed to {printer_name}'
        })
        
    except Exception as e:
        logger.exception('Print job failed')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_server(port=None):
    """Start the Flask server."""
    if port is None:
        port = config.get('port', 5000)
    
    try:
        cert_path, key_path = CertificateManager.generate()
        
        logger.info(f'{APP_TITLE} v{APP_VERSION}')
        logger.info(f'Starting server on port {port}')
        logger.info(f'Local addresses: {NetworkInfo.get_local_addresses()}')
        
        app.run(
            host='0.0.0.0',
            port=port,
            ssl_context=(cert_path, key_path),
            threaded=True,
            use_reloader=False,
        )
    except Exception as e:
        logger.exception('Server failed to start')
        raise


if __name__ == '__main__':
    run_server()
