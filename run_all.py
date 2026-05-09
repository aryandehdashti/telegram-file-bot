#!/usr/bin/env python3
"""
Run both Telegram bot and HTTP server together.
This script starts both services in parallel for easy deployment.
"""

import subprocess
import sys
import signal
import os
from pathlib import Path

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\n🛑 Shutting down services...")
    sys.exit(0)

def main():
    """Run both bot and HTTP server."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Telegram File Download Bot services...")
    print("=" * 50)
    
    # Check if .env exists
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and configure it.")
        sys.exit(1)
    
    # Start HTTP server if enabled
    from dotenv import load_dotenv
    load_dotenv()
    
    enable_http = os.getenv('ENABLE_HTTP_SERVER', 'True').lower() == 'true'
    
    processes = []
    
    try:
        # Start HTTP server if enabled
        if enable_http:
            print("📡 Starting HTTP server...")
            http_process = subprocess.Popen(
                [sys.executable, 'http_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append(('HTTP Server', http_process))
            print("✅ HTTP server started")
        else:
            print("⚠️  HTTP server disabled in configuration")
        
        # Start Telegram bot
        print("🤖 Starting Telegram bot...")
        bot_process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(('Telegram Bot', bot_process))
        print("✅ Telegram bot started")
        
        print("=" * 50)
        print("✅ All services started successfully!")
        print("Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Wait for processes
        for name, process in processes:
            process.wait()
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Terminate all processes
        for name, process in processes:
            try:
                print(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")

if __name__ == "__main__":
    main()