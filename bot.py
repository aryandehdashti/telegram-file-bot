#!/usr/bin/env python3
"""
Telegram File Download Bot
A bot that downloads files from URLs and sends them to users,
designed to work in restricted network environments.
"""

import os
import asyncio
import logging
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from tqdm.asyncio import tqdm_asyncio
import hashlib
import shutil

# Import optional modules
try:
    from github_fallback import GitHubStorage
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("GitHub fallback module not available")

try:
    from youtube_downloader import YouTubeDownloader, QUALITY_PRESETS
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("YouTube downloader module not available")

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Configuration
    telegram_bot_token: str
    admin_user_id: Optional[int] = None
    
    # File Handling
    max_file_size_mb: int = 50
    chunk_size_mb: int = 45
    temp_download_dir: str = "/tmp/telegram_bot_downloads"
    download_timeout: int = 300
    
    # HTTP Server Configuration
    enable_http_server: bool = True
    http_server_port: int = 8080
    http_server_host: str = "0.0.0.0"
    vps_host: str = "your-vps-ip"  # Public IP or domain of VPS
    download_link_expiry_hours: int = 24
    
    # GitHub Configuration
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    github_branch: str = "main"
    
    # Rate Limiting
    enable_rate_limiting: bool = False
    max_downloads_per_hour: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Cleanup Configuration
    enable_auto_cleanup: bool = True
    cleanup_age_days: int = 7  # Delete files older than this many days
    cleanup_max_repo_size_mb: int = 500  # Cleanup if repo exceeds this size
    cleanup_keep_recent: int = 10  # Always keep this many recent files
    
    model_config = {"extra": "ignore", "env_file": ".env", "case_sensitive": False}

# Initialize settings
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    print("Please ensure .env file exists with required variables")
    exit(1)

# Setup logging
def setup_logging():
    """Configure logging based on settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    if settings.log_file:
        handlers.append(logging.FileHandler(settings.log_file))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Ensure temp directory exists
Path(settings.temp_download_dir).mkdir(parents=True, exist_ok=True)

class FileDownloader:
    """Handles file downloading operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.download_history: Dict[int, list] = {}  # user_id -> list of timestamps
        
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit."""
        if not self.settings.enable_rate_limiting:
            return False
            
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        if user_id in self.download_history:
            self.download_history[user_id] = [
                ts for ts in self.download_history[user_id] 
                if ts > hour_ago
            ]
        
        # Check limit
        recent_downloads = len(self.download_history.get(user_id, []))
        return recent_downloads >= self.settings.max_downloads_per_hour
    
    def record_download(self, user_id: int):
        """Record a download for rate limiting."""
        if self.settings.enable_rate_limiting:
            if user_id not in self.download_history:
                self.download_history[user_id] = []
            self.download_history[user_id].append(datetime.now())
    
    def is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def get_file_size(self, url: str, session: aiohttp.ClientSession) -> Optional[int]:
        """Get file size from URL headers."""
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        return int(content_length)
        except Exception as e:
            logger.warning(f"Error getting file size: {e}")
        return None
    
    async def download_file(
        self, 
        url: str, 
        filename: Optional[str] = None,
        progress_callback=None
    ) -> Optional[Path]:
        """Download file from URL to temp directory."""
        if not self.is_valid_url(url):
            raise ValueError("Invalid URL format")
        
        # Generate filename if not provided
        if not filename:
            url_path = urlparse(url).path
            filename = os.path.basename(url_path) or "downloaded_file"
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in '._-')
        filepath = Path(self.settings.temp_download_dir) / filename
        
        # Add timestamp if file exists
        if filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = filepath.stem
            suffix = filepath.suffix
            filepath = filepath.parent / f"{stem}_{timestamp}{suffix}"
        
        logger.info(f"Downloading {url} to {filepath}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get file size first
                file_size = await self.get_file_size(url, session)
                
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=self.settings.download_timeout)
                ) as response:
                    response.raise_for_status()
                    
                    # Download with progress
                    downloaded = 0
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and file_size:
                                progress_callback(downloaded, file_size)
                    
                    logger.info(f"Downloaded {filepath} ({downloaded} bytes)")
                    return filepath
                    
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if filepath.exists():
                filepath.unlink()
            raise
    
    def split_file(self, filepath: Path, chunk_size_mb: int) -> list[Path]:
        """Split large file into chunks."""
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        chunks = []
        
        logger.info(f"Splitting {filepath} into {chunk_size_mb}MB chunks")
        
        with open(filepath, 'rb') as f:
            chunk_num = 0
            while True:
                chunk_data = f.read(chunk_size_bytes)
                if not chunk_data:
                    break
                
                chunk_path = filepath.parent / f"{filepath.stem}_part{chunk_num + 1}{filepath.suffix}"
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                
                chunks.append(chunk_path)
                chunk_num += 1
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def cleanup_file(self, filepath: Path):
        """Clean up downloaded file."""
        try:
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Cleaned up {filepath}")
        except Exception as e:
            logger.warning(f"Error cleaning up {filepath}: {e}")

class TelegramBot:
    """Telegram bot handler."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.downloader = FileDownloader(settings)
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self.setup_handlers()
        
        # Store download links with expiry
        self.download_links: Dict[str, Dict[str, Any]] = {}
        
        # Store file information for download options
        self.file_storage: Dict[str, Dict[str, Any]] = {}
        
        # Store YouTube download information
        self.youtube_storage: Dict[str, Dict[str, Any]] = {}
        
        # Initialize GitHub storage if available
        self.github_storage = None
        if GITHUB_AVAILABLE:
            try:
                self.github_storage = GitHubStorage()
                if self.github_storage.is_configured():
                    logger.info("GitHub storage initialized successfully")
                else:
                    logger.info("GitHub storage available but not configured")
                    self.github_storage = None
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub storage: {e}")
                self.github_storage = None
        
        # Initialize YouTube downloader if available
        self.youtube_downloader = None
        self.youtube_available = False
        if YOUTUBE_AVAILABLE:
            try:
                self.youtube_downloader = YouTubeDownloader(settings.temp_download_dir)
                if self.youtube_downloader.available:
                    self.youtube_available = True
                    logger.info("YouTube downloader initialized successfully")
                else:
                    logger.warning("YouTube downloader initialized but yt-dlp not available")
                    self.youtube_downloader = None
            except Exception as e:
                logger.warning(f"Failed to initialize YouTube downloader: {e}")
                self.youtube_downloader = None
    
    def setup_handlers(self):
        """Setup bot command and message handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("cleanup", self.cleanup_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
🤖 *Telegram File Download Bot*

I can download files from URLs and send them to you!

*Usage:*
Just send me a download URL and I'll handle the rest.

*Features:*
✅ Download any file from the internet
✅ Download YouTube videos with quality selection
✅ Handle large files (>50MB) by splitting
✅ Alternative download methods for very large files
✅ Works around network restrictions

*Commands:*
/start - Show this message
/help - Show help information
/status - Check bot status

Send me a URL to get started!
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
📖 *Help*

*How to use:*
1. Send me any download URL
2. I'll download it on my VPS
3. I'll send it to you via Telegram

*YouTube Downloads:*
• Send any YouTube URL
• Choose quality (1080p, 720p, 480p, 360p, or audio only)
• Download via Telegram, GitHub, or HTTP

*File size handling:*
• <50MB: Sent directly via Telegram
• 50-500MB: Split into chunks
• >500MB: Direct download link provided

*Example URLs:*
• Direct downloads: https://example.com/file.zip
• YouTube: https://youtube.com/watch?v=xxxxx
• Google Drive: (shareable links)
• GitHub: (raw file URLs)

*Notes:*
• Downloads happen on VPS in unrestricted region
• Large files may take time to process
• Temporary files are cleaned up automatically

Need help? Contact admin.
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        youtube_status = "✅ Available" if self.youtube_downloader else "❌ Not Available"
        github_status = "✅ Configured" if self.github_storage else "❌ Not Configured"
        
        status = f"""
📊 *Bot Status*

✅ Bot is running
💾 Temp Dir: {self.settings.temp_download_dir}
📁 Max File Size: {self.settings.max_file_size_mb}MB
🔗 HTTP Server: {'Enabled' if self.settings.enable_http_server else 'Disabled'}
🎬 YouTube Downloads: {youtube_status}
🐙 GitHub Storage: {github_status}
        """
        await update.message.reply_text(status, parse_mode='Markdown')
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command (admin only)."""
        if self.settings.admin_user_id and update.effective_user.id != self.settings.admin_user_id:
            await update.message.reply_text("⚠️ Admin command only")
            return
        
        admin_info = f"""
🔧 *Admin Panel*

*Rate Limiting:* {'Enabled' if self.settings.enable_rate_limiting else 'Disabled'}
*Max Downloads/Hour:* {self.settings.max_downloads_per_hour}
*Download History:* {len(self.downloader.download_history)} users

*Recent Downloads:*
"""
        for user_id, timestamps in list(self.downloader.download_history.items())[:5]:
            admin_info += f"• User {user_id}: {len(timestamps)} downloads\n"
        
        await update.message.reply_text(admin_info, parse_mode='Markdown')
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cleanup command (admin only)."""
        if self.settings.admin_user_id and update.effective_user.id != self.settings.admin_user_id:
            await update.message.reply_text("⚠️ Admin command only")
            return
        
        if not self.github_storage or not self.github_storage.is_configured():
            await update.message.reply_text("❌ GitHub storage not configured")
            return
        
        # Parse arguments
        args = context.args if context.args else []
        cleanup_type = "auto"  # default
        force = False
        
        for arg in args:
            if arg in ["auto", "age", "size"]:
                cleanup_type = arg
            elif arg == "--force":
                force = True
        
        await update.message.reply_text("🧹 Starting GitHub cleanup...")
        
        try:
            if cleanup_type == "auto":
                # Run both age and size cleanup
                deleted_age = await self.github_storage.cleanup_old_files(
                    max_age_days=self.settings.cleanup_age_days,
                    keep_recent=self.settings.cleanup_keep_recent
                )
                deleted_size = await self.github_storage.cleanup_by_size(
                    max_size_mb=self.settings.cleanup_max_repo_size_mb,
                    keep_recent=self.settings.cleanup_keep_recent
                )
                total_deleted = deleted_age + deleted_size
                message = f"✅ Cleanup complete!\n\nDeleted {total_deleted} files:\n• {deleted_age} by age (>{self.settings.cleanup_age_days} days)\n• {deleted_size} by size (>{self.settings.cleanup_max_repo_size_mb}MB)"
            
            elif cleanup_type == "age":
                deleted = await self.github_storage.cleanup_old_files(
                    max_age_days=self.settings.cleanup_age_days,
                    keep_recent=self.settings.cleanup_keep_recent
                )
                message = f"✅ Age-based cleanup complete!\n\nDeleted {deleted} files older than {self.settings.cleanup_age_days} days"
            
            elif cleanup_type == "size":
                deleted = await self.github_storage.cleanup_by_size(
                    max_size_mb=self.settings.cleanup_max_repo_size_mb,
                    keep_recent=self.settings.cleanup_keep_recent
                )
                message = f"✅ Size-based cleanup complete!\n\nDeleted {deleted} files to keep repo under {self.settings.cleanup_max_repo_size_mb}MB"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await update.message.reply_text(f"❌ Cleanup failed: {str(e)}")
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle URL messages."""
        url = update.message.text.strip()
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested download: {url}")
        
        # Check rate limit
        if self.downloader.is_rate_limited(user_id):
            await update.message.reply_text(
                "⚠️ Rate limit exceeded. Please wait before downloading more files."
            )
            return
        
        # Check if YouTube URL
        if self.youtube_downloader and self.youtube_downloader.is_youtube_url(url):
            await self.handle_youtube_url(update, url)
            return
        
        # Validate URL
        if not self.downloader.is_valid_url(url):
            await update.message.reply_text("❌ Invalid URL format. Please send a valid URL.")
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text("⏳ Starting download...")
        
        try:
            # Download file
            filepath = await self.downloader.download_file(
                url, 
                progress_callback=lambda d, t: self._update_progress(processing_msg, d, t)
            )
            
            if not filepath:
                raise Exception("Download failed - no file returned")
            
            # Get file size
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            
            logger.info(f"Downloaded {filepath} ({file_size_mb:.2f}MB)")
            
            # Record download
            self.downloader.record_download(user_id)
            
            # Handle file based on size
            await self.handle_file(update, filepath, file_size_mb)
            
            # Clean up processing message
            try:
                await processing_msg.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error handling download: {e}")
            await processing_msg.edit_text(f"❌ Download failed: {str(e)}")
            
            # Clean up if file exists
            if 'filepath' in locals() and filepath.exists():
                self.downloader.cleanup_file(filepath)
    
    def _update_progress(self, message, downloaded: int, total: int):
        """Update progress message (async wrapper needed)."""
        # This would need to be called differently in async context
        pass
    
    async def handle_youtube_url(self, update: Update, url: str):
        """Handle YouTube URL with quality/format selection."""
        user_id = update.effective_user.id
        
        # Check if YouTube downloader is available
        if not self.youtube_available or not self.youtube_downloader:
            await update.message.reply_text(
                "❌ YouTube downloads are not available.\n\n"
                "This is because yt-dlp is not installed on the VPS.\n\n"
                "To enable YouTube downloads:\n"
                "1. SSH into your VPS\n"
                "2. Run: pip install yt-dlp\n"
                "3. Restart the bot"
            )
            return
        
        # Check rate limit
        if self.downloader.is_rate_limited(user_id):
            await update.message.reply_text(
                "⚠️ Rate limit exceeded. Please wait before downloading more files."
            )
            return
        
        # Get video info
        await update.message.reply_text("🎬 Getting video information...")
        
        try:
            # Get video title
            video_title = self.youtube_downloader.get_video_title(url)
            
            if not video_title:
                await update.message.reply_text("❌ Could not get video information. The video may be private or unavailable.")
                return
            
            # Store YouTube download info
            youtube_id = hashlib.md5(f"{url}{datetime.now()}".encode()).hexdigest()[:8]
            self.youtube_storage = getattr(self, 'youtube_storage', {})
            self.youtube_storage[youtube_id] = {
                'url': url,
                'title': video_title,
                'user_id': user_id
            }
            
            # Build quality selection message
            message = f"🎬 **YouTube Video Detected**\n\n"
            message += f"📺 Title: {video_title}\n\n"
            message += "Choose download quality:\n"
            
            keyboard = []
            
            # Quality options
            quality_options = [
                ('🎥 Best Quality (1080p+)', 'best'),
                ('📺 Good Quality (720p)', '720p'),
                ('📱 Medium Quality (480p)', '480p'),
                ('📲 Low Quality (360p)', '360p'),
                ('🎵 Audio Only (MP3)', 'audio_only'),
            ]
            
            for label, quality in quality_options:
                keyboard.append([InlineKeyboardButton(label, callback_data=f"yt_quality_{youtube_id}_{quality}")])
            
            # Add cancel button
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"yt_cancel_{youtube_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling YouTube URL: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_youtube_quality_selection(self, query, youtube_id: str, quality: str):
        """Handle YouTube quality selection callback."""
        if youtube_id not in self.youtube_storage:
            await query.edit_message_text("❌ Video information expired")
            return
        
        video_info = self.youtube_storage[youtube_id]
        url = video_info['url']
        
        await query.edit_message_text(f"🎬 Downloading with quality: {quality}...\n\nThis may take a few minutes.")
        
        try:
            # Download video
            if quality == 'audio_only':
                filepath = self.youtube_downloader.download_audio_only(url)
            else:
                quality_format = QUALITY_PRESETS.get(quality, 'best')
                filepath = self.youtube_downloader.download_video(url, quality=quality_format)
            
            if not filepath:
                await query.edit_message_text("❌ Video download failed")
                return
            
            # Get file size
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            
            logger.info(f"YouTube video downloaded: {filepath} ({file_size_mb:.2f}MB)")
            
            # Record download
            self.downloader.record_download(video_info['user_id'])
            
            # Store file info for download options
            file_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
            self.file_storage[file_id] = {
                'filepath': str(filepath),
                'file_size_mb': file_size_mb,
                'filename': filepath.name,
                'is_youtube': True
            }
            
            # Show download options
            await self.show_download_options(query, file_id, filepath.name, file_size_mb)
            
            # Clean up YouTube storage
            del self.youtube_storage[youtube_id]
            
        except Exception as e:
            logger.error(f"Error in YouTube download: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_download_options(self, query, file_id: str, filename: str, file_size_mb: float):
        """Show download options for a file."""
        # Ensure file_storage is initialized
        if not hasattr(self, 'file_storage'):
            self.file_storage = {}
        
        message = f"✅ Download complete!\n\n"
        message += f"📁 File: {filename}\n"
        message += f"📊 Size: {file_size_mb:.2f}MB\n\n"
        message += "Choose download method:\n"
        
        keyboard = []
        
        # Option 1: Telegram download
        if file_size_mb <= self.settings.max_file_size_mb:
            message += "1. 📱 Download via Telegram (fast, direct)\n"
            keyboard.append([InlineKeyboardButton("📱 Telegram Download", callback_data=f"telegram_{file_id}")])
        elif file_size_mb <= 500:
            message += "1. 📱 Download via Telegram (split into chunks)\n"
            keyboard.append([InlineKeyboardButton("📱 Telegram (Chunks)", callback_data=f"telegram_chunks_{file_id}")])
        
        # Option 2: GitHub download (if configured)
        if self.github_storage and self.github_storage.is_configured():
            if file_size_mb <= 25:
                message += "2. 🐙 Download via GitHub (works in restricted regions)\n"
                keyboard.append([InlineKeyboardButton("🐙 GitHub Download", callback_data=f"github_{file_id}")])
            else:
                message += "2. 🐙 GitHub Download (file too large, max 25MB)\n"
        
        # Option 3: HTTP server (if enabled)
        if self.settings.enable_http_server:
            message += "3. 🌐 Download via HTTP Server (direct link)\n"
            keyboard.append([InlineKeyboardButton("🌐 HTTP Download", callback_data=f"http_{file_id}")])
        
        message += "\n💡 GitHub works best in restricted regions"
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{file_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_file(self, update: Update, filepath: Path, file_size_mb: float):
        """Handle downloaded file by offering download options."""
        # Store file info for later use
        # Use filepath in hash to ensure uniqueness and persistence
        file_id = hashlib.md5(f"{filepath}_{datetime.now()}".encode()).hexdigest()[:8]
        
        # Ensure file_storage is initialized
        if not hasattr(self, 'file_storage'):
            self.file_storage = {}
        
        self.file_storage[file_id] = {
            'filepath': str(filepath),
            'file_size_mb': file_size_mb,
            'filename': filepath.name,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Stored file with ID: {file_id} for file: {filepath.name}")
        
        # Build download options message
        message = f"✅ File downloaded successfully!\n\n"
        message += f"📁 File: {filepath.name}\n"
        message += f"📊 Size: {file_size_mb:.2f}MB\n\n"
        message += "Choose download method:\n"
        
        keyboard = []
        
        # Option 1: Telegram download
        if file_size_mb <= self.settings.max_file_size_mb:
            message += "1. 📱 Download via Telegram (fast, direct)\n"
            keyboard.append([InlineKeyboardButton("📱 Telegram Download", callback_data=f"telegram_{file_id}")])
        elif file_size_mb <= 500:
            message += "1. 📱 Download via Telegram (split into chunks)\n"
            keyboard.append([InlineKeyboardButton("📱 Telegram (Chunks)", callback_data=f"telegram_chunks_{file_id}")])
        
        # Option 2: GitHub download (if configured)
        if self.github_storage and self.github_storage.is_configured():
            if file_size_mb <= 25:  # GitHub limit
                message += "2. 🐙 Download via GitHub (works in restricted regions)\n"
                keyboard.append([InlineKeyboardButton("🐙 GitHub Download", callback_data=f"github_{file_id}")])
            else:
                # Large files can be stored via splitting
                message += "2. 🐙 Download via GitHub (file will be split into chunks)\n"
                keyboard.append([InlineKeyboardButton("🐙 GitHub (Split)", callback_data=f"github_{file_id}")])
        
        # Option 3: HTTP server (if enabled)
        if self.settings.enable_http_server:
            message += "3. 🌐 Download via HTTP Server (direct link)\n"
            keyboard.append([InlineKeyboardButton("🌐 HTTP Download", callback_data=f"http_{file_id}")])
        
        message += "\n💡 GitHub works best in restricted regions"
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{file_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def send_file_directly(self, update: Update, filepath: Path):
        """Send file directly via Telegram."""
        try:
            logger.info(f"Sending file directly: {filepath}")
            
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📁 {filepath.name} ({filepath.stat().st_size / (1024*1024):.2f}MB)"
                )
            
            logger.info("File sent successfully")
            
        except TelegramError as e:
            logger.error(f"Telegram error sending file: {e}")
            await update.message.reply_text(f"❌ Failed to send file: {str(e)}")
        
        finally:
            self.downloader.cleanup_file(filepath)
    
    async def send_file_chunks(self, update: Update, filepath: Path):
        """Split file into chunks and send."""
        try:
            chunk_size = self.settings.chunk_size_mb
            chunks = self.downloader.split_file(filepath, chunk_size)
            
            await update.message.reply_text(
                f"📦 File is too large ({filepath.stat().st_size / (1024*1024):.2f}MB)\n"
                f"Splitting into {len(chunks)} chunks..."
            )
            
            for i, chunk in enumerate(chunks, 1):
                try:
                    with open(chunk, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            caption=f"📦 Part {i}/{len(chunks)} - {chunk.name}"
                        )
                    logger.info(f"Sent chunk {i}/{len(chunks)}")
                    
                    # Small delay between chunks
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error sending chunk {i}: {e}")
                    await update.message.reply_text(f"❌ Error sending chunk {i}: {str(e)}")
                
                # Clean up chunk
                self.downloader.cleanup_file(chunk)
            
            await update.message.reply_text(
                f"✅ All {len(chunks)} chunks sent! "
                f"You can combine them using:\n"
                f"`cat {filepath.stem}_part*{filepath.suffix} > {filepath.name}`",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in chunk splitting: {e}")
            await update.message.reply_text(f"❌ Error splitting file: {str(e)}")
        
        finally:
            self.downloader.cleanup_file(filepath)
    
    async def provide_download_link(self, update: Update, filepath: Path, file_size_mb: float):
        """Provide alternative download link for very large files."""
        try:
            # Build message with available download options
            message = f"📁 File is very large ({file_size_mb:.2f}MB)\n\nDownload options:\n"
            keyboard = []
            
            # Option 1: HTTP Server (if enabled)
            if self.settings.enable_http_server:
                link_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                
                # Store link info
                self.download_links[link_id] = {
                    'filepath': str(filepath),
                    'expiry': datetime.now() + timedelta(hours=self.settings.download_link_expiry_hours),
                    'user_id': update.effective_user.id
                }
                
                message += f"1. 📥 Direct download from VPS (HTTP server)\n"
                keyboard.append([InlineKeyboardButton("� Download via HTTP", callback_data=f"download_{link_id}")])
            
            # Option 2: GitHub Storage (if configured and file size allows)
            if self.github_storage and file_size_mb <= 25:  # GitHub limit
                message += f"2. 🐙 Store in GitHub (works in restricted regions)\n"
                keyboard.append([InlineKeyboardButton("🐙 Store in GitHub", callback_data=f"github_{filepath.name}")])
            
            # Option 3: Admin transfer
            message += f"3. 👤 Request admin for manual transfer\n"
            
            # Add file info
            message += f"\nFile: {filepath.name}\n"
            if self.settings.enable_http_server:
                message += f"Expires in: {self.settings.download_link_expiry_hours} hours\n"
            
            # Add cancel button
            if self.settings.enable_http_server:
                link_id = list(self.download_links.keys())[-1] if self.download_links else "unknown"
                keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{link_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error providing download link: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
            self.downloader.cleanup_file(filepath)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("telegram_"):
            file_id = query.data.replace("telegram_", "")
            await self.handle_telegram_callback(query, file_id)
        elif query.data.startswith("telegram_chunks_"):
            file_id = query.data.replace("telegram_chunks_", "")
            await self.handle_telegram_chunks_callback(query, file_id)
        elif query.data.startswith("github_"):
            file_id = query.data.replace("github_", "")
            await self.handle_github_callback(query, file_id)
        elif query.data.startswith("http_"):
            file_id = query.data.replace("http_", "")
            await self.handle_http_callback(query, file_id)
        elif query.data.startswith("cancel_"):
            file_id = query.data.replace("cancel_", "")
            await self.handle_cancel_callback(query, file_id)
        elif query.data == "github_too_large":
            await query.edit_message_text("❌ File is too large for GitHub (max 25MB)\nPlease use Telegram or HTTP download instead.")
        elif query.data.startswith("yt_quality_"):
            # Handle YouTube quality selection
            parts = query.data.replace("yt_quality_", "").split("_")
            youtube_id = parts[0]
            quality = parts[1]
            await self.handle_youtube_quality_selection(query, youtube_id, quality)
        elif query.data.startswith("yt_cancel_"):
            youtube_id = query.data.replace("yt_cancel_", "")
            if youtube_id in self.youtube_storage:
                del self.youtube_storage[youtube_id]
            await query.edit_message_text("❌ YouTube download cancelled")
    
    async def handle_download_callback(self, query, link_id: str):
        """Handle download button callback."""
        if link_id not in self.download_links:
            await query.edit_message_text("❌ Invalid or expired download link")
            return
        
        link_info = self.download_links[link_id]
        
        # Check expiry
        if datetime.now() > link_info['expiry']:
            await query.edit_message_text("❌ Download link has expired")
            del self.download_links[link_id]
            # Clean up file
            Path(link_info['filepath']).unlink(missing_ok=True)
            return
        
        await query.edit_message_text(
            "📥 HTTP download feature requires additional server setup.\n"
            "For now, please contact admin for manual transfer."
        )
    
    async def handle_cancel_callback(self, query, file_id: str):
        """Handle cancel button callback."""
        # Clean up from file_storage
        if file_id in self.file_storage:
            filepath = Path(self.file_storage[file_id]['filepath'])
            self.downloader.cleanup_file(filepath)
            del self.file_storage[file_id]
        
        # Clean up from download_links (for HTTP server)
        if file_id in self.download_links:
            link_info = self.download_links[file_id]
            Path(link_info['filepath']).unlink(missing_ok=True)
            del self.download_links[file_id]
        
        await query.edit_message_text("❌ Download cancelled")
    
    async def handle_telegram_callback(self, query, file_id: str):
        """Handle Telegram download callback."""
        if file_id not in self.file_storage:
            await query.edit_message_text("❌ File not found or expired")
            return
        
        file_info = self.file_storage[file_id]
        filepath = Path(file_info['filepath'])
        
        if not filepath.exists():
            await query.edit_message_text("❌ File not found")
            del self.file_storage[file_id]
            return
        
        await query.edit_message_text("📱 Sending file via Telegram...")
        
        # Create a mock update for the send_file_directly method
        class MockUpdate:
            def __init__(self, message):
                self.message = message
        
        class MockMessage:
            def __init__(self, chat_id):
                self.chat_id = chat_id
                self.reply_document = self._reply_document
            
            async def _reply_document(self, document, caption=None):
                from telegram import Bot
                bot = Bot(token=self.settings.telegram_bot_token)
                await bot.send_document(
                    chat_id=self.chat_id,
                    document=document,
                    caption=caption
                )
        
        try:
            with open(filepath, 'rb') as f:
                from telegram import Bot
                bot = Bot(token=self.settings.telegram_bot_token)
                await bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    caption=f"📁 {filepath.name} ({file_info['file_size_mb']:.2f}MB)"
                )
            
            await query.edit_message_text("✅ File sent via Telegram!")
            self.downloader.cleanup_file(filepath)
            del self.file_storage[file_id]
            
        except Exception as e:
            logger.error(f"Error sending via Telegram: {e}")
            await query.edit_message_text(f"❌ Failed to send via Telegram: {str(e)}")
    
    async def handle_telegram_chunks_callback(self, query, file_id: str):
        """Handle Telegram chunks download callback."""
        if file_id not in self.file_storage:
            await query.edit_message_text("❌ File not found or expired")
            return
        
        file_info = self.file_storage[file_id]
        filepath = Path(file_info['filepath'])
        
        await query.edit_message_text("📦 Splitting file and sending via Telegram...")
        
        # Create a mock update for the send_file_chunks method
        try:
            chunk_size = self.settings.chunk_size_mb
            chunks = self.downloader.split_file(filepath, chunk_size)
            
            from telegram import Bot
            bot = Bot(token=self.settings.telegram_bot_token)
            
            await query.edit_message_text(
                f"📦 Sending {len(chunks)} chunks via Telegram..."
            )
            
            for i, chunk in enumerate(chunks, 1):
                try:
                    with open(chunk, 'rb') as f:
                        await bot.send_document(
                            chat_id=query.message.chat_id,
                            document=f,
                            caption=f"📦 Part {i}/{len(chunks)} - {chunk.name}"
                        )
                    logger.info(f"Sent chunk {i}/{len(chunks)}")
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error sending chunk {i}: {e}")
                    await bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"❌ Error sending chunk {i}: {str(e)}"
                    )
                
                self.downloader.cleanup_file(chunk)
            
            await bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ All {len(chunks)} chunks sent!\n\nCombine them using:\n`cat {filepath.stem}_part*{filepath.suffix} > {filepath.name}`",
                parse_mode='Markdown'
            )
            
            self.downloader.cleanup_file(filepath)
            del self.file_storage[file_id]
            
        except Exception as e:
            logger.error(f"Error in chunk splitting: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def handle_github_callback(self, query, file_id: str):
        """Handle GitHub storage button callback."""
        logger.info(f"GitHub callback called with file_id: {file_id}")
        
        if not self.github_storage:
            await query.edit_message_text("❌ GitHub storage not configured")
            return
        
        if not hasattr(self, 'file_storage'):
            logger.warning("file_storage not initialized")
            await query.edit_message_text("❌ File storage not initialized")
            return
        
        if file_id not in self.file_storage:
            logger.warning(f"File ID {file_id} not found in file_storage")
            logger.info(f"Available file IDs: {list(self.file_storage.keys())}")
            await query.edit_message_text("❌ File not found or expired")
            return
        
        file_info = self.file_storage[file_id]
        filepath = Path(file_info['filepath'])
        
        logger.info(f"Processing GitHub storage for file: {filepath}")
        
        if not filepath.exists():
            logger.error(f"File not found at path: {filepath}")
            await query.edit_message_text("❌ File not found on disk")
            del self.file_storage[file_id]
            return
        
        await query.edit_message_text("🐙 Storing file in GitHub...")
        
        try:
            file_size_mb = file_info['file_size_mb']
            
            # Check if file needs splitting (GitHub limit is 25MB, use 20MB to be safe)
            if file_size_mb > 20:
                await query.edit_message_text(
                    f"📦 File is too large ({file_size_mb:.2f}MB) for direct GitHub storage.\n"
                    f"Splitting into chunks under 20MB each..."
                )
                
                # Split the file
                chunks = await self.github_storage.split_file_for_github(filepath, max_size_mb=20)
                
                if not chunks or len(chunks) == 0:
                    await query.edit_message_text("❌ Failed to split file for GitHub storage")
                    return
                
                await query.edit_message_text(
                    f"📦 Split into {len(chunks)} chunks. Uploading to GitHub..."
                )
                
                # Upload chunks to GitHub
                raw_urls = await self.github_storage.store_split_files(chunks)
                
                if raw_urls and len(raw_urls) == len(chunks):
                    # Generate recombination instructions
                    instructions = self.github_storage.generate_recombination_instructions(
                        file_info['filename'], len(chunks)
                    )
                    
                    # Add the actual download links to instructions
                    instructions_with_links = instructions
                    for i, url in enumerate(raw_urls):
                        instructions_with_links = instructions_with_links.replace(
                            f"Part {i+1}: [Link will be provided]",
                            f"Part {i+1}: {url}"
                        )
                    
                    await query.edit_message_text(
                        f"✅ File split and stored in GitHub!\n\n"
                        f"📦 Split into {len(chunks)} chunks\n"
                        f"📥 Download all parts from GitHub\n\n"
                        f"📝 Recombination instructions:\n"
                        f"```\n{instructions_with_links}```\n\n"
                        f"💡 Download all parts before recombining."
                    )
                    
                    # Clean up chunks and original file
                    for chunk in chunks:
                        self.downloader.cleanup_file(chunk)
                    self.downloader.cleanup_file(filepath)
                    del self.file_storage[file_id]
                else:
                    await query.edit_message_text(f"❌ Failed to upload all chunks ({len(raw_urls) if raw_urls else 0}/{len(chunks)} uploaded)")
                    # Clean up chunks
                    for chunk in chunks:
                        self.downloader.cleanup_file(chunk)
                    self.downloader.cleanup_file(filepath)
                    del self.file_storage[file_id]
                return  # Exit after handling split case
            else:
                # Store file directly
                raw_url = await self.github_storage.store_file(filepath)
            
            if raw_url:
                await query.edit_message_text(
                    f"✅ File stored in GitHub!\n\n"
                    f"📥 Download link: {raw_url}\n\n"
                    f"💡 This link works in restricted regions via GitHub's raw content delivery.\n"
                    f"📦 File size: {file_info['file_size_mb']:.2f}MB"
                )
                # Clean up local file
                self.downloader.cleanup_file(filepath)
                del self.file_storage[file_id]
            else:
                await query.edit_message_text("❌ Failed to store file in GitHub")
                
        except Exception as e:
            logger.error(f"Error in GitHub callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def handle_http_callback(self, query, file_id: str):
        """Handle HTTP server download callback."""
        if not self.settings.enable_http_server:
            await query.edit_message_text("❌ HTTP server is disabled")
            return
        
        if file_id not in self.file_storage:
            await query.edit_message_text("❌ File not found or expired")
            return
        
        file_info = self.file_storage[file_id]
        
        # Generate download link
        link_id = file_id  # Use same ID for simplicity
        
        # Store link info
        self.download_links[link_id] = {
            'filepath': file_info['filepath'],
            'expiry': datetime.now() + timedelta(hours=self.settings.download_link_expiry_hours),
            'user_id': query.from_user.id
        }
        
        # Get VPS IP or domain from settings
        vps_host = self.settings.vps_host
        vps_port = self.settings.http_server_port
        
        download_url = f"http://{vps_host}:{vps_port}/download/{link_id}"
        
        await query.edit_message_text(
            f"🌐 HTTP download link generated!\n\n"
            f"📥 Download URL: {download_url}\n\n"
            f"⏰ Expires in: {self.settings.download_link_expiry_hours} hours\n"
            f"📊 File size: {file_info['file_size_mb']:.2f}MB\n\n"
            f"💡 Use this link with your proxy/VPN to download from Iran."
        )
    
    def run(self):
        """Run the bot."""
        logger.info("Starting Telegram File Download Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main entry point."""
    try:
        bot = TelegramBot(settings)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    main()