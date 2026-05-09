# Telegram File Download Bot

A Telegram bot that downloads files from URLs and delivers them to users, designed to work in restricted network environments like Iran.

## Features

- **User Choice Interface**: Users can choose their preferred download method
- **Multiple Download Methods**:
  - 📱 **Telegram Download**: Direct file transfer via Telegram (files <50MB)
  - 📦 **Telegram Chunks**: Large files split into chunks (50-500MB)
  - 🐙 **GitHub Storage**: Files stored in GitHub repo with raw URL access (works in Iran!)
  - 🌐 **HTTP Server**: Direct download links from VPS (for very large files)
- **Smart File Handling**: Automatic file size detection and method recommendation
- **Network Resilience**: Works around Iran's network restrictions
- **VPS-based**: Runs on Finland VPS for unrestricted access
- **GitHub Integration**: Leverages GitHub's accessible raw content delivery for Iran

## Architecture

The bot runs on a VPS in Finland (free world) and:
1. Receives download URLs from users via Telegram
2. Downloads files from the internet without restrictions
3. Sends files back via Telegram or provides alternative download links
4. Handles large files by splitting or providing direct download links

## Setup

### Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- VPS in unrestricted location (Finland)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd telegram-file-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your bot token and settings
```

### Configuration

Edit `.env` file:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
MAX_FILE_SIZE_MB=50
TEMP_DOWNLOAD_DIR=/tmp/telegram_bot_downloads
ENABLE_HTTP_SERVER=True
HTTP_SERVER_PORT=8080
VPS_HOST=your-vps-ip-or-domain
GITHUB_TOKEN=your_github_token_for_fallback
GITHUB_REPO=your_username/your_repo
```

### Running

```bash
# Run directly
python bot.py

# Or use systemd service (recommended for VPS)
sudo cp telegram-file-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-bot
sudo systemctl start telegram-file-bot
```

## Usage

1. Send a download URL to the bot
2. Bot downloads the file on the VPS
3. **Choose your download method**:
   - 📱 **Telegram Download**: Direct file transfer (fast, files <50MB)
   - 📦 **Telegram Chunks**: Large files split into parts (50-500MB)
   - 🐙 **GitHub Storage**: File stored in GitHub with raw URL (works in Iran!)
   - 🌐 **HTTP Server**: Direct download link from VPS (for very large files)
4. **GitHub Method** (Recommended for Iran):
   - File is stored in your GitHub repository
   - You receive a raw GitHub URL
   - Download directly from GitHub (works in Iran)
   - No size limits for GitHub repo storage

## Network Bypassing Methods

### Current Setup
- **DNS Tunneling**: Slow but works for Telegram access
- **GitHub Code Files**: Accessible, releases blocked
- **VPS in Finland**: Unrestricted internet access

### Alternative Methods
1. **HTTP Relay**: Use existing MasterHttpRelayVPN-RUST for HTTP traffic
2. **DNS VPN**: Continue using MasterDnsVPN for Telegram access
3. **GitHub Raw URLs**: Use GitHub as CDN for smaller files
4. **Direct VPS Download**: Users can download directly from VPS HTTP server

## File Size Handling

- **<50MB**: Send directly via Telegram
- **50MB-500MB**: Split into chunks and send via Telegram
- **>500MB**: Provide direct download link from VPS HTTP server
- **Very Large**: Use GitHub LFS or alternative storage

## Security

- Admin-only mode (configurable)
- File size limits
- URL validation
- Temporary file cleanup
- Rate limiting (optional)

## Troubleshooting

### Bot not responding
- Check bot token is correct
- Verify VPS has internet access
- Check logs: `journalctl -u telegram-file-bot -f`

### Large files failing
- Increase timeout in config
- Check VPS disk space
- Use alternative download method

### Network issues
- Ensure Telegram is accessible via your VPN
- Check VPS firewall settings
- Verify DNS tunneling is working

## License

MIT License