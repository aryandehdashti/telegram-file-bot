#!/usr/bin/env python3
"""
GitHub Fallback Module
Stores files as base64-encoded content in GitHub repositories.
Useful when direct downloads are blocked but GitHub code files are accessible.
"""

import base64
import logging
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

class GitHubSettings(BaseSettings):
    """GitHub API settings."""
    
    github_token: Optional[str] = None
    github_repo: Optional[str] = None  # format: username/repo
    github_branch: str = "main"
    github_api_url: str = "https://api.github.com"
    
    model_config = {"extra": "ignore", "env_file": ".env", "case_sensitive": False}

try:
    github_settings = GitHubSettings()
except Exception as e:
    logging.warning(f"GitHub settings not configured: {e}")
    github_settings = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitHubStorage:
    """Store and retrieve files using GitHub API."""
    
    def __init__(self, settings: Optional[GitHubSettings] = None):
        self.settings = settings or github_settings
        self.headers = {}
        
        if self.settings and self.settings.github_token:
            self.headers['Authorization'] = f"token {self.settings.github_token}"
    
    def is_configured(self) -> bool:
        """Check if GitHub storage is properly configured."""
        return (
            self.settings is not None
            and self.settings.github_token is not None
            and self.settings.github_repo is not None
        )
    
    async def store_file(
        self, 
        filepath: Path, 
        commit_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Store a file in GitHub repository as base64-encoded content.
        
        Args:
            filepath: Path to the file to store
            commit_message: Custom commit message
            
        Returns:
            GitHub raw URL for the stored file, or None if failed
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return None
        
        try:
            # Read file and encode to base64
            async with aiofiles.open(filepath, 'rb') as f:
                file_content = await f.read()
            
            # Check file size (GitHub has limits)
            file_size_mb = len(file_content) / (1024 * 1024)
            if file_size_mb > 25:  # GitHub's soft limit for files
                logger.warning(f"File too large for GitHub ({file_size_mb:.2f}MB)")
                return None
            
            # Encode to base64
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare API request
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}/contents/{filepath.name}"
            
            # Check if file already exists
            sha = None
            async with aiohttp.ClientSession(headers=self.headers) as session:
                try:
                    async with session.get(api_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            sha = data.get('sha')
                except:
                    pass
            
            # Prepare data
            data = {
                'message': commit_message or f"Add {filepath.name}",
                'content': encoded_content,
                'branch': self.settings.github_branch
            }
            
            if sha:
                data['sha'] = sha
            
            # Upload to GitHub
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.put(api_url, json=data) as response:
                    response_text = await response.text()
                    logger.info(f"GitHub API response status: {response.status}")
                    logger.info(f"GitHub API response: {response_text[:500]}")

                    if response.status != 200 and response.status != 201:
                        logger.error(f"GitHub API error: {response.status} - {response_text}")
                        return None

                    result = await response.json()

                    if result.get('content'):
                        content = result['content']

                        # Try multiple ways to get the raw URL
                        raw_url = content.get('raw_url')
                        if not raw_url:
                            # Try download_url
                            raw_url = content.get('download_url')

                        if not raw_url:
                            # Construct raw URL manually
                            # Format: https://raw.githubusercontent.com/{username}/{repo}/{branch}/{path}
                            raw_url = f"https://raw.githubusercontent.com/{self.settings.github_repo}/{self.settings.github_branch}/{filepath.name}"
                            logger.info(f"Constructed raw URL: {raw_url}")

                        if raw_url:
                            logger.info(f"Stored {filepath.name} in GitHub: {raw_url}")
                            return raw_url
                        else:
                            logger.error(f"Could not extract raw URL from response. Available keys: {list(content.keys())}")
                            logger.error(f"Full content object: {content}")
                            return None
                    else:
                        logger.error(f"No content in GitHub response: {result}")
                        return None

            return None
            
        except Exception as e:
            logger.error(f"Error storing file in GitHub: {e}")
            return None
    
    async def retrieve_file(self, filename: str, output_path: Path) -> bool:
        """
        Retrieve a file from GitHub repository.
        
        Args:
            filename: Name of the file to retrieve
            output_path: Path where to save the retrieved file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return False
        
        try:
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}/contents/{filename}"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if data.get('content'):
                        # Decode base64 content
                        encoded_content = data['content']
                        file_content = base64.b64decode(encoded_content)
                        
                        # Write to file
                        async with aiofiles.open(output_path, 'wb') as f:
                            await f.write(file_content)
                        
                        logger.info(f"Retrieved {filename} from GitHub")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error retrieving file from GitHub: {e}")
            return False
    
    async def delete_file(self, filename: str, commit_message: Optional[str] = None) -> bool:
        """
        Delete a file from GitHub repository.
        
        Args:
            filename: Name of the file to delete
            commit_message: Custom commit message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return False
        
        try:
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}/contents/{filename}"
            
            # Get file SHA first
            sha = None
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        sha = data.get('sha')
            
            if not sha:
                logger.warning(f"File {filename} not found in GitHub")
                return False
            
            # Delete file
            data = {
                'message': commit_message or f"Delete {filename}",
                'sha': sha,
                'branch': self.settings.github_branch
            }
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.delete(api_url, json=data) as response:
                    response.raise_for_status()
                    logger.info(f"Deleted {filename} from GitHub")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file from GitHub: {e}")
            return False
    
    async def list_files(self) -> list:
        """
        List all files stored in the repository.
        
        Returns:
            List of file information dictionaries
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return []
        
        try:
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}/contents/"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if isinstance(data, list):
                        files = []
                        for item in data:
                            if item.get('type') == 'file':
                                files.append({
                                    'name': item['name'],
                                    'size': item.get('size', 0),
                                    'raw_url': item.get('raw_url'),
                                    'download_url': item.get('download_url')
                                })
                        return files
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing files from GitHub: {e}")
            return []
    
    async def split_file_for_github(self, filepath: Path, max_size_mb: int = 20) -> list[Path]:
        """
        Split a large file into smaller parts suitable for GitHub storage.
        
        Args:
            filepath: Path to the file to split
            max_size_mb: Maximum size per part in MB (default 20MB to stay under 25MB limit)
        
        Returns:
            List of paths to the split files
        """
        chunk_size_bytes = max_size_mb * 1024 * 1024
        chunks = []
        
        try:
            async with aiofiles.open(filepath, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk_data = await f.read(chunk_size_bytes)
                    if not chunk_data:
                        break
                    
                    chunk_path = filepath.parent / f"{filepath.stem}_part{chunk_num + 1}{filepath.suffix}"
                    async with aiofiles.open(chunk_path, 'wb') as chunk_file:
                        await chunk_file.write(chunk_data)
                    
                    chunks.append(chunk_path)
                    chunk_num += 1
            
            logger.info(f"Split {filepath} into {len(chunks)} parts for GitHub")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting file for GitHub: {e}")
            # Clean up partial chunks
            for chunk in chunks:
                chunk.unlink(missing_ok=True)
            return []
    
    async def store_split_files(self, chunks: list[Path], commit_message: str = None) -> list:
        """
        Store multiple file chunks to GitHub.

        Args:
            chunks: List of file paths to store
            commit_message: Custom commit message

        Returns:
            List of raw URLs for the stored chunks
        """
        raw_urls = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Uploading chunk {i+1}/{len(chunks)}: {chunk.name}")
            chunk_size_mb = chunk.stat().st_size / (1024 * 1024)
            logger.info(f"Chunk size: {chunk_size_mb:.2f}MB")

            raw_url = await self.store_file(chunk, commit_message)
            if raw_url:
                raw_urls.append(raw_url)
                logger.info(f"Successfully uploaded chunk {i+1}/{len(chunks)}")
            else:
                logger.error(f"Failed to store chunk {i+1}/{len(chunks)}: {chunk}")

        logger.info(f"Uploaded {len(raw_urls)}/{len(chunks)} chunks successfully")
        return raw_urls
    
    def generate_recombination_instructions(self, filename: str, num_chunks: int) -> str:
        """
        Generate instructions for recombining split files.
        
        Args:
            filename: Original filename
            num_chunks: Number of chunks
            
        Returns:
            Recombination instructions
        """
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        
        instructions = f"""
📦 File Splitting Instructions

Your file has been split into {num_chunks} parts and stored in GitHub.

🔗 Download Links:
"""
        
        # This would be filled in when chunks are uploaded
        for i in range(num_chunks):
            instructions += f"Part {i+1}: [Link will be provided]\n"
        
        instructions += f"""
📝 How to Recombine:

Linux/Mac:
cat {stem}_part*{suffix} > {filename}

Windows:
copy /b {stem}_part1{suffix}+{stem}_part2{suffix}+{stem}_part3{suffix} {filename}

PowerShell:
Get-Content {stem}_part*{suffix} | Set-Content {filename}

💡 Note: Make sure to download all parts before recombining.
"""
        
        return instructions
    
    async def combine_parts(self, output_path: Path, parts: list[Path]) -> bool:
        """
        Combine split file parts back into original file.
        
        Args:
            output_path: Path for the combined output file
            parts: List of paths to the part files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiofiles.open(output_path, 'wb') as outfile:
                for part in sorted(parts):
                    async with aiofiles.open(part, 'rb') as infile:
                        await outfile.write(await infile.read())
            
            logger.info(f"Combined {len(parts)} parts into {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error combining file parts: {e}")
            return False
    
    async def cleanup_old_files(self, max_age_days: int = 7, keep_recent: int = 10) -> int:
        """
        Clean up old files from GitHub repository.
        
        Args:
            max_age_days: Delete files older than this many days
            keep_recent: Always keep this many most recent files
            
        Returns:
            Number of files deleted
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return 0
        
        try:
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}/contents/"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if isinstance(data, list):
                        # Get all files with their info
                        files_to_delete = []
                        now = datetime.now()
                        
                        # Sort by last modified date (most recent first)
                        sorted_files = sorted(
                            [item for item in data if item.get('type') == 'file'],
                            key=lambda x: x.get('name', ''),
                            reverse=True
                        )
                        
                        # Keep the most recent files
                        recent_files = sorted_files[:keep_recent]
                        recent_names = {f['name'] for f in recent_files}
                        
                        # Mark older files for deletion
                        for file_info in sorted_files[keep_recent:]:
                            if file_info['name'] not in recent_names:
                                files_to_delete.append(file_info)
                        
                        logger.info(f"Found {len(files_to_delete)} files to delete (keeping {keep_recent} recent)")
                        
                        # Delete old files
                        deleted_count = 0
                        for file_info in files_to_delete:
                            try:
                                # Get SHA for deletion
                                async with session.get(
                                    f"{api_url}{file_info['name']}"
                                ) as response:
                                    if response.status == 200:
                                        data = await response.json()
                                        sha = data.get('sha')
                                        
                                        # Delete file
                                        delete_data = {
                                            'message': f"Auto-cleanup: Removing old file {file_info['name']}",
                                            'sha': sha,
                                            'branch': self.settings.github_branch
                                        }
                                        
                                        async with session.delete(
                                            f"{api_url}{file_info['name']}",
                                            json=delete_data
                                        ) as response:
                                            if response.status == 200:
                                                deleted_count += 1
                                                logger.info(f"Deleted old file: {file_info['name']}")
                                    else:
                                        logger.warning(f"Failed to delete {file_info['name']}: {response.status}")
                            except Exception as e:
                                logger.error(f"Error deleting {file_info['name']}: {e}")
                        
                        return deleted_count
            return 0
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    async def get_repo_size(self) -> int:
        """
        Get total size of GitHub repository in bytes.
        
        Returns:
            Total size in bytes, 0 if unable to determine
        """
        if not self.is_configured():
            return 0
        
        try:
            api_url = f"{self.settings.github_api_url}/repos/{self.settings.github_repo}"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('size', 0)
        except Exception as e:
            logger.error(f"Error getting repo size: {e}")
            return 0
    
    async def cleanup_by_size(self, max_size_mb: int, keep_recent: int = 10) -> int:
        """
        Clean up repository if it exceeds size limit.
        
        Args:
            max_size_mb: Maximum repository size in MB
            keep_recent: Always keep this many most recent files
            
        Returns:
            Number of files deleted
        """
        if not self.is_configured():
            logger.warning("GitHub storage not configured")
            return 0
        
        current_size_mb = (await self.get_repo_size()) / (1024 * 1024)
        
        if current_size_mb <= max_size_mb:
            logger.info(f"Repository size {current_size_mb:.2f}MB is under limit {max_size_mb}MB")
            return 0
        
        logger.info(f"Repository size {current_size_mb:.2f}MB exceeds limit {max_size_mb}MB, cleaning up...")
        
        # Use the same cleanup logic as age-based cleanup
        return await self.cleanup_old_files(max_age_days=0, keep_recent=keep_recent)

# Example usage and testing
async def main():
    """Test GitHub storage functionality."""
    storage = GitHubStorage()
    
    if not storage.is_configured():
        print("GitHub storage not configured. Set GITHUB_TOKEN and GITHUB_REPO in .env")
        return
    
    # Test storing a file
    test_file = Path("test_file.txt")
    test_file.write_text("This is a test file for GitHub storage.")
    
    print(f"Storing {test_file} in GitHub...")
    raw_url = await storage.store_file(test_file)
    
    if raw_url:
        print(f"File stored at: {raw_url}")
        
        # Test retrieving
        output_path = Path("retrieved_file.txt")
        success = await storage.retrieve_file(test_file.name, output_path)
        
        if success:
            print(f"File retrieved successfully: {output_path}")
            print(f"Content: {output_path.read_text()}")
        
        # Clean up
        test_file.unlink()
        output_path.unlink()
        
        # Delete from GitHub
        await storage.delete_file(test_file.name)
        print("Test file deleted from GitHub")
    else:
        print("Failed to store file in GitHub")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())