#!/bin/bash
# Setup script for Telegram File Download Bot

set -e

echo "🚀 Setting up Telegram File Download Bot..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /tmp/telegram_bot_downloads
mkdir -p logs

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
    echo "   - Set TELEGRAM_BOT_TOKEN"
    echo "   - Set ADMIN_USER_ID"
    echo "   - Configure other settings as needed"
else
    echo "✅ .env file already exists"
fi

# Make scripts executable
chmod +x bot.py
chmod +x http_server.py
chmod +x github_fallback.py

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Test the bot: python bot.py"
echo "3. For production, use systemd service (see telegram-file-bot.service)"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"