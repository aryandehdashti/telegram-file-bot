#!/usr/bin/env python3
"""
YouTube Video Downloader Module
Handles YouTube video downloads using yt-dlp with support for restricted regions.
"""

import logging
import asyncio
import subprocess
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """Handles YouTube video downloads using yt-dlp."""
    
    def __init__(self, temp_download_dir: str = "/tmp/telegram_bot_downloads"):
        self.temp_download_dir = Path(temp_download_dir)
        self.temp_download_dir.mkdir(parents=True, exist_ok=True)
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        youtube_patterns = [
            r'https?://(www\.)?youtube\.com/watch\?v=',
            r'https?://(www\.)?youtube\.com/shorts/',
            r'https?://(www\.)?youtu\.be/',
            r'https?://(www\.)?youtube\.com/playlist\?list=',
        ]
        
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading."""
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--no-warnings',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Error getting video info: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting video info")
            return None
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Get available video formats."""
        try:
            cmd = [
                'yt-dlp',
                '--list-formats',
                '--print-json',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse the output to get format information
                formats = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if 'format_id' in data:
                                formats.append({
                                    'id': data.get('format_id'),
                                    'ext': data.get('ext'),
                                    'resolution': data.get('resolution', 'audio only'),
                                    'filesize': data.get('filesize', 0),
                                    'fps': data.get('fps', 0),
                                    'vcodec': data.get('vcodec', 'none'),
                                    'acodec': data.get('acodec', 'none'),
                                })
                        except json.JSONDecodeError:
                            continue
                return formats
            else:
                logger.error(f"Error getting formats: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting formats")
            return []
        except Exception as e:
            logger.error(f"Error getting formats: {e}")
            return []
    
    def download_video(
        self,
        url: str,
        quality: str = 'best',
        format: str = 'mp4',
        output_template: str = '%(title)s.%(ext)s',
        progress_callback=None
    ) -> Optional[Path]:
        """
        Download YouTube video.
        
        Args:
            url: YouTube video URL
            quality: Video quality (best, worst, or specific format ID)
            format: Output format (mp4, webm, mkv, etc.)
            output_template: Output filename template
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f"youtube_{timestamp}_{output_template}"
            output_path = self.temp_download_dir / output_template
            
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '--format', quality,
                '--merge-output-format', format,
                '--output', str(output_path),
                '--no-playlist',
                '--no-warnings',
                '--newline',
                url
            ]
            
            # Add progress hook if callback provided
            if progress_callback:
                cmd.extend(['--progress', '--progress-template', 'download:%(downloader)s %(percent)s %(speed)s'])
            
            logger.info(f"Downloading YouTube video: {url}")
            
            # Run download
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress
            for line in process.stdout:
                if progress_callback and '%' in line:
                    try:
                        # Extract progress percentage
                        percent_match = re.search(r'(\d+\.?\d*)%', line)
                        if percent_match:
                            percent = float(percent_match.group(1))
                            progress_callback(percent, 100)
                    except (ValueError, AttributeError):
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                # Find the downloaded file
                downloaded_files = list(self.temp_download_dir.glob(f"youtube_{timestamp}*"))
                if downloaded_files:
                    logger.info(f"YouTube video downloaded: {downloaded_files[0]}")
                    return downloaded_files[0]
                else:
                    logger.error("Download completed but file not found")
                    return None
            else:
                logger.error(f"Download failed with return code {process.returncode}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Download timeout")
            return None
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def download_audio_only(
        self,
        url: str,
        audio_format: str = 'mp3',
        output_template: str = '%(title)s.%(ext)s'
    ) -> Optional[Path]:
        """
        Download audio only from YouTube video.
        
        Args:
            url: YouTube video URL
            audio_format: Audio format (mp3, m4a, wav, etc.)
            output_template: Output filename template
            
        Returns:
            Path to downloaded audio file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f"youtube_audio_{timestamp}_{output_template}"
            output_path = self.temp_download_dir / output_template
            
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', audio_format,
                '--output', str(output_path),
                '--no-playlist',
                '--no-warnings',
                url
            ]
            
            logger.info(f"Downloading audio from: {url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                downloaded_files = list(self.temp_download_dir.glob(f"youtube_audio_{timestamp}*"))
                if downloaded_files:
                    logger.info(f"Audio downloaded: {downloaded_files[0]}")
                    return downloaded_files[0]
                else:
                    logger.error("Audio download completed but file not found")
                    return None
            else:
                logger.error(f"Audio download failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Audio download timeout")
            return None
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None
    
    def get_video_title(self, url: str) -> Optional[str]:
        """Get video title without downloading."""
        try:
            cmd = [
                'yt-dlp',
                '--get-title',
                '--no-playlist',
                '--no-warnings',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Error getting title: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting title")
            return None
        except Exception as e:
            logger.error(f"Error getting title: {e}")
            return None
    
    def download_playlist(
        self,
        url: str,
        quality: str = 'best',
        format: str = 'mp4',
        start: int = 1,
        end: Optional[int] = None
    ) -> List[Path]:
        """
        Download YouTube playlist.
        
        Args:
            url: YouTube playlist URL
            quality: Video quality
            format: Output format
            start: Start index (1-based)
            end: End index (None for all)
            
        Returns:
            List of downloaded file paths
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f"youtube_playlist_{timestamp}/%(playlist_index)s_%(title)s.%(ext)s"
            output_path = self.temp_download_dir / f"youtube_playlist_{timestamp}"
            output_path.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'yt-dlp',
                '--format', quality,
                '--merge-output-format', format,
                '--output', str(output_path / output_template),
                '--playlist-start', str(start),
                '--newline',
                url
            ]
            
            if end:
                cmd.extend(['--playlist-end', str(end)])
            
            logger.info(f"Downloading playlist: {url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for playlists
            )
            
            if result.returncode == 0:
                downloaded_files = list(output_path.glob("*"))
                logger.info(f"Playlist downloaded: {len(downloaded_files)} files")
                return downloaded_files
            else:
                logger.error(f"Playlist download failed: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Playlist download timeout")
            return []
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            return []

# Quality presets
QUALITY_PRESETS = {
    'best': 'bestvideo+bestaudio/best',
    'worst': 'worstvideo+worstaudio/worst',
    '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
    '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
    '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
    '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
    'audio_only': 'bestaudio/best'
}