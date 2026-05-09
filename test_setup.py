#!/usr/bin/env python3
"""
Test script to verify the setup and configuration.
"""

import os
import sys
from pathlib import Path

def test_python_version():
    """Test Python version."""
    print("Testing Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Need 3.8+")
        return False

def test_dependencies():
    """Test if dependencies are installed."""
    print("\nTesting dependencies...")
    required_packages = [
        'telegram',
        'aiohttp',
        'dotenv',
        'aiofiles',
        'pydantic',
        'tqdm'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True

def test_configuration():
    """Test configuration files."""
    print("\nTesting configuration...")
    
    # Check .env file
    if Path('.env').exists():
        print("✅ .env file exists")
        
        # Check required variables
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['TELEGRAM_BOT_TOKEN']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                print(f"❌ {var} - Not set")
                missing_vars.append(var)
            else:
                print(f"✅ {var} - Set")
        
        if missing_vars:
            print(f"\nMissing required variables: {', '.join(missing_vars)}")
            return False
        return True
    else:
        print("❌ .env file missing")
        print("Copy .env.example to .env and configure")
        return False

def test_directories():
    """Test required directories."""
    print("\nTesting directories...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    temp_dir = os.getenv('TEMP_DOWNLOAD_DIR', '/tmp/telegram_bot_downloads')
    
    # Create directory if it doesn't exist
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    if Path(temp_dir).exists():
        print(f"✅ Temp directory: {temp_dir}")
        return True
    else:
        print(f"❌ Cannot create temp directory: {temp_dir}")
        return False

def test_network():
    """Test network connectivity."""
    print("\nTesting network connectivity...")
    
    try:
        import aiohttp
        import asyncio
        
        async def test_connection():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.telegram.org', timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        print("✅ Telegram API reachable")
                        return True
                    else:
                        print(f"❌ Telegram API returned status {response.status}")
                        return False
        
        result = asyncio.run(test_connection())
        return result
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def test_github_config():
    """Test GitHub configuration (optional)."""
    print("\nTesting GitHub configuration (optional)...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    github_repo = os.getenv('GITHUB_REPO')
    
    if github_token and github_repo:
        print("✅ GitHub configuration found")
        return True
    else:
        print("⚠️  GitHub configuration not set (optional)")
        return True  # Not required

def main():
    """Run all tests."""
    print("=" * 50)
    print("Telegram File Download Bot - Setup Test")
    print("=" * 50)
    
    tests = [
        test_python_version,
        test_dependencies,
        test_configuration,
        test_directories,
        test_network,
        test_github_config
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("✅ All tests passed! Bot is ready to run.")
        print("\nStart the bot with: python bot.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())