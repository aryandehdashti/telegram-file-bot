# Quick Start Guide

Get your Telegram File Download Bot running in 5 minutes.

## 1. Get Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 2. Get Your Telegram User ID

1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Send any message to the bot
3. Copy your user ID (numbers only)

## 3. Clone and Setup

```bash
# Navigate to your projects directory
cd C:\Users\arian\Documents\source\Projrcts\telegram-file-bot

# Create virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 4. Configure

```bash
# Copy environment template
copy .env.example .env

# Edit .env file
notepad .env
```

Set these required variables:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
```

Optional but recommended:
```
TEMP_DOWNLOAD_DIR=C:\Users\arian\Documents\source\Projrcts\telegram-file-bot\downloads
LOG_FILE=C:\Users\arian\Documents\source\Projrcts\telegram-file-bot\logs\bot.log
```

## 5. Test Setup

```bash
# Run test script
python test_setup.py
```

Fix any issues reported by the test.

## 6. Run Bot

```bash
# Start the bot
python bot.py
```

You should see:
```
INFO - Starting Telegram File Download Bot...
INFO - Application started
```

## 7. Test Bot

1. Open Telegram and search for your bot (by username)
2. Send `/start` command
3. Send a download URL to test

Example URLs to test:
- Small file: `https://example.com/small-file.zip`
- Image: `https://example.com/image.jpg`
- Any direct download link

## 8. Deploy to VPS (Optional)

For production use, deploy to your Finland VPS:

1. **Upload to VPS:**
```bash
# On your local machine
scp -r telegram-file-bot user@your-vps-ip:/opt/
```

2. **Setup on VPS:**
```bash
# SSH into VPS
ssh user@your-vps-ip

# Navigate to project
cd /opt/telegram-file-bot

# Run setup
chmod +x setup.sh
./setup.sh

# Configure
nano .env
```

3. **Install as service:**
```bash
# Edit service files
nano telegram-file-bot.service
# Update paths and user

# Install service
sudo cp telegram-file-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-bot
sudo systemctl start telegram-file-bot
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Common Issues

### Bot doesn't respond
- Check bot token is correct
- Check you've started a conversation with the bot (`/start`)
- Check logs: `tail -f logs/bot.log`

### Download fails
- Check URL is valid and accessible
- Check VPS has internet connection
- Check temp directory has write permissions

### Large files fail
- Check disk space on VPS
- Increase timeout in `.env`
- Use alternative download method (HTTP server)

### Windows-specific issues
- Use `venv\Scripts\activate` instead of `source venv/bin/activate`
- Use backslashes for paths in `.env`
- Run Command Prompt as Administrator if needed

## Network Bypassing for Iran

Your bot is designed to work with your existing setup:

### Current Tools Integration

1. **DNS Tunneling (MasterDnsVPN)**
   - Continue using for Telegram access
   - Bot will work through this connection
   - Slow but reliable

2. **GitHub Code Files**
   - Configure GitHub fallback in `.env`
   - Useful when direct downloads are blocked
   - Files stored as base64 in GitHub repo

3. **VPS in Finland**
   - Bot runs on VPS with unrestricted internet
   - Downloads happen on VPS, not your local machine
   - Only Telegram messages go through your restricted connection

### Alternative Methods

For very large files (>500MB):

1. **HTTP Server Method**
   - Enable HTTP server in `.env`
   - Bot provides direct download link from VPS
   - You download directly from VPS (may need proxy)

2. **GitHub Storage**
   - Files split and stored in GitHub
   - Download via GitHub raw URLs
   - Works in Iran (code files accessible)

3. **Manual Transfer**
   - Contact admin for manual file transfer
   - Use alternative file sharing services

### File Size Handling

- **<50MB**: Sent directly via Telegram
- **50-500MB**: Split into chunks, sent via Telegram
- **>500MB**: HTTP download link or GitHub storage

## Next Steps

1. **Configure GitHub Fallback** (optional but recommended)
   - Create GitHub personal access token
   - Create a private repository
   - Add to `.env`:
     ```
     GITHUB_TOKEN=your_github_token
     GITHUB_REPO=your_username/your_repo
     ```

2. **Enable HTTP Server** (for large files)
   - Set in `.env`:
     ```
     ENABLE_HTTP_SERVER=True
     HTTP_SERVER_PORT=8080
     ```

3. **Set Up Monitoring**
   - Check logs regularly
   - Monitor disk space
   - Set up log rotation

4. **Security Hardening**
   - Use strong admin password
   - Enable rate limiting
   - Configure firewall on VPS

## Support

- Check logs for errors
- Run `python test_setup.py` to verify configuration
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for VPS setup
- Check [README.md](README.md) for detailed documentation

## License

MIT License