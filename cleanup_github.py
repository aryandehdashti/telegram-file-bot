#!/usr/bin/env python3
"""
GitHub Storage Cleanup Script

This script performs automatic cleanup of the GitHub storage repository
to prevent it from filling up over time. It can be run manually or via cron job.

Usage:
    python cleanup_github.py [--age DAYS] [--size MB] [--keep N] [--dry-run]

Options:
    --age DAYS        Delete files older than this many days (default: 7)
    --size MB         Cleanup if repo exceeds this size in MB (default: 500)
    --keep N          Always keep this many recent files (default: 10)
    --dry-run         Show what would be deleted without actually deleting
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_fallback import GitHubStorage, GitHubSettings

async def cleanup_github(args):
    """Perform GitHub cleanup based on arguments."""
    
    # Load settings from environment
    settings = GitHubSettings(
        github_token=os.getenv("GITHUB_TOKEN"),
        github_repo=os.getenv("GITHUB_REPO"),
        github_branch=os.getenv("GITHUB_BRANCH", "main"),
    )
    
    if not settings.github_token or not settings.github_repo:
        print("❌ Error: GITHUB_TOKEN and GITHUB_REPO environment variables must be set")
        return 1
    
    # Initialize GitHub storage
    github = GitHubStorage(settings)
    
    if not github.is_configured():
        print("❌ Error: GitHub storage not configured")
        return 1
    
    print("🧹 GitHub Storage Cleanup")
    print("=" * 50)
    print(f"Repository: {settings.github_repo}")
    print(f"Branch: {settings.github_branch}")
    print(f"Age limit: {args.age} days")
    print(f"Size limit: {args.size} MB")
    print(f"Keep recent: {args.keep} files")
    print(f"Dry run: {args.dry_run}")
    print("=" * 50)
    
    # Get current repo size
    current_size = await github.get_repo_size()
    current_size_mb = current_size / (1024 * 1024)
    print(f"Current repository size: {current_size_mb:.2f} MB")
    
    if args.dry_run:
        print("\n🔍 Dry run mode - no files will be deleted")
    
    # Perform age-based cleanup
    print(f"\n📅 Checking for files older than {args.age} days...")
    if args.dry_run:
        print("(Would delete old files)")
    else:
        deleted_age = await github.cleanup_old_files(
            max_age_days=args.age,
            keep_recent=args.keep
        )
        print(f"✅ Deleted {deleted_age} files by age")
    
    # Perform size-based cleanup
    print(f"\n📊 Checking if repository exceeds {args.size} MB...")
    if args.dry_run:
        print("(Would delete files if size limit exceeded)")
    else:
        deleted_size = await github.cleanup_by_size(
            max_size_mb=args.size,
            keep_recent=args.keep
        )
        print(f"✅ Deleted {deleted_size} files by size")
    
    # Get new repo size
    new_size = await github.get_repo_size()
    new_size_mb = new_size / (1024 * 1024)
    print(f"\nNew repository size: {new_size_mb:.2f} MB")
    print(f"Freed space: {current_size_mb - new_size_mb:.2f} MB")
    
    print("\n✅ Cleanup complete!")
    return 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GitHub Storage Cleanup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--age",
        type=int,
        default=7,
        help="Delete files older than this many days (default: 7)"
    )
    
    parser.add_argument(
        "--size",
        type=int,
        default=500,
        help="Cleanup if repo exceeds this size in MB (default: 500)"
    )
    
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Always keep this many recent files (default: 10)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    # Run cleanup
    return asyncio.run(cleanup_github(args))

if __name__ == "__main__":
    sys.exit(main())
