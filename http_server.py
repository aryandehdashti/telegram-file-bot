#!/usr/bin/env python3
"""
Simple HTTP server for providing direct download links.
This runs alongside the Telegram bot for large file downloads.
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import json
import base64
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """HTTP Server settings."""
    
    temp_download_dir: str = "/tmp/telegram_bot_downloads"
    http_server_port: int = 8080
    http_server_host: str = "0.0.0.0"
    download_link_expiry_hours: int = 24
    
    # Simple authentication (optional)
    enable_auth: bool = False
    auth_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DownloadLinkManager:
    """Manages download links and their expiry."""
    
    def __init__(self, expiry_hours: int):
        self.expiry_hours = expiry_hours
        self.links: Dict[str, Dict] = {}
    
    def generate_link(self, filepath: str, user_id: int) -> str:
        """Generate a download link ID."""
        import hashlib
        import time
        
        # Generate unique link ID
        link_id = hashlib.md5(f"{filepath}{user_id}{time.time()}".encode()).hexdigest()[:16]
        
        self.links[link_id] = {
            'filepath': filepath,
            'user_id': user_id,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=self.expiry_hours),
            'downloads': 0
        }
        
        logger.info(f"Generated link {link_id} for {filepath}")
        return link_id
    
    def get_file_path(self, link_id: str) -> Optional[str]:
        """Get file path for link ID if valid."""
        if link_id not in self.links:
            return None
        
        link = self.links[link_id]
        
        # Check expiry
        if datetime.now() > link['expires_at']:
            logger.info(f"Link {link_id} expired")
            del self.links[link_id]
            return None
        
        # Check if file exists
        if not Path(link['filepath']).exists():
            logger.warning(f"File not found for link {link_id}: {link['filepath']}")
            del self.links[link_id]
            return None
        
        link['downloads'] += 1
        return link['filepath']
    
    def cleanup_expired(self):
        """Remove expired links."""
        now = datetime.now()
        expired = [lid for lid, link in self.links.items() if now > link['expires_at']]
        
        for lid in expired:
            logger.info(f"Cleaning up expired link {lid}")
            del self.links[lid]

class FileDownloadHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler for file downloads."""
    
    link_manager = DownloadLinkManager(settings.download_link_expiry_hours)
    
    def __init__(self, *args, **kwargs):
        self.directory = settings.temp_download_dir
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Health check endpoint
        if parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode())
            return
        
        # Download link endpoint
        if parsed_path.path.startswith('/download/'):
            self.handle_download_link(parsed_path.path)
            return
        
        # Stats endpoint
        if parsed_path.path == '/stats':
            self.handle_stats()
            return
        
        # Default: file not found
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def handle_download_link(self, path: str):
        """Handle download link requests."""
        try:
            # Extract link ID
            link_id = path.replace('/download/', '')
            
            # Check authentication if enabled
            if settings.enable_auth:
                auth_header = self.headers.get('Authorization')
                if not auth_header or auth_header != f"Bearer {settings.auth_token}":
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                    return
            
            # Get file path
            filepath = self.link_manager.get_file_path(link_id)
            if not filepath:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Link not found or expired'}).encode())
                return
            
            # Serve file
            file_path = Path(filepath)
            if not file_path.exists():
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'File not found'}).encode())
                return
            
            # Send file
            self.send_response(200)
            self.send_header('Content-Disposition', f'attachment; filename="{file_path.name}"')
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(file_path.stat().st_size))
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
            
            logger.info(f"Served file {file_path.name} via link {link_id}")
            
        except Exception as e:
            logger.error(f"Error handling download: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_stats(self):
        """Handle stats requests."""
        try:
            # Check authentication
            if settings.enable_auth:
                auth_header = self.headers.get('Authorization')
                if not auth_header or auth_header != f"Bearer {settings.auth_token}":
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                    return
            
            stats = {
                'active_links': len(self.link_manager.links),
                'total_downloads': sum(link['downloads'] for link in self.link_manager.links.values()),
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
            
        except Exception as e:
            logger.error(f"Error handling stats: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def log_message(self, format, *args):
        """Custom log messages."""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server():
    """Run the HTTP server."""
    server_address = (settings.http_server_host, settings.http_server_port)
    httpd = HTTPServer(server_address, FileDownloadHandler)
    
    logger.info(f"Starting HTTP server on {settings.http_server_host}:{settings.http_server_port}")
    logger.info(f"Serving files from: {settings.temp_download_dir}")
    logger.info(f"Download link expiry: {settings.download_link_expiry_hours} hours")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    run_server()