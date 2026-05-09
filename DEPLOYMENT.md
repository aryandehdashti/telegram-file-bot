# VPS Deployment Guide

This guide covers deploying the Telegram File Download Bot on a VPS (tested on Finland VPS).

## Prerequisites

- VPS with Ubuntu/Debian (or similar Linux)
- Python 3.8+
- Git
- Telegram Bot Token
- (Optional) GitHub Token for fallback storage

## Quick Deployment

### 1. Clone Repository

```bash
cd /opt
sudo git clone <your-repo-url> telegram-file-bot
cd telegram-file-bot
```

### 2. Setup

```bash
chmod +x setup.sh
./setup.sh
```

### 3. Configure

```bash
nano .env
```

Edit the following:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
TEMP_DOWNLOAD_DIR=/opt/telegram-file-bot/downloads
LOG_FILE=/var/log/telegram_file_bot.log
```

### 4. Create Directories

```bash
sudo mkdir -p /opt/telegram-file-bot/downloads
sudo mkdir -p /var/log
sudo chown -R $USER:$USER /opt/telegram-file-bot
```

### 5. Setup Systemd Services

Edit the service files to match your paths:

```bash
# Edit bot service
nano telegram-file-bot.service
```

Change:
- `User=your_username` to your actual username
- `WorkingDirectory=/path/to/telegram-file-bot` to `/opt/telegram-file-bot`
- `Environment="PATH=..."` to `/opt/telegram-file-bot/venv/bin`
- `ExecStart=...` to `/opt/telegram-file-bot/venv/bin/python bot.py`

```bash
# Edit HTTP server service (if using)
nano telegram-http-server.service
```

Make the same changes, but with `http_server.py` instead of `bot.py`.

### 6. Install Services

```bash
# Copy service files
sudo cp telegram-file-bot.service /etc/systemd/system/
sudo cp telegram-http-server.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable telegram-file-bot
sudo systemctl enable telegram-http-server

# Start services
sudo systemctl start telegram-file-bot
sudo systemctl start telegram-http-server
```

### 7. Check Status

```bash
# Check bot status
sudo systemctl status telegram-file-bot

# Check HTTP server status
sudo systemctl status telegram-http-server

# View logs
sudo journalctl -u telegram-file-bot -f
sudo journalctl -u telegram-http-server -f
```

## Firewall Configuration

If you're using the HTTP server, allow the port:

```bash
# Allow HTTP server port (default 8080)
sudo ufw allow 8080/tcp

# Or use iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
```

## Domain Configuration (Optional)

For better download links, set up a domain:

1. Buy a domain
2. Point A record to your VPS IP
3. Set up reverse proxy with Nginx:

```nginx
server {
    listen 80;
    server_name downloads.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## SSL Configuration (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d downloads.yourdomain.com
```

## Monitoring

### Basic Monitoring

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check bot logs
sudo journalctl -u telegram-file-bot -n 100

# Check download directory size
du -sh /opt/telegram-file-bot/downloads
```

### Log Rotation

Create logrotate config:

```bash
sudo nano /etc/logrotate.d/telegram-file-bot
```

Content:
```
/var/log/telegram_file_bot.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 $USER $USER
}
```

## Automatic Cleanup

Add a cron job to clean old downloads:

```bash
crontab -e
```

Add:
```
# Clean downloads older than 24 hours
0 0 * * * find /opt/telegram-file-bot/downloads -type f -mtime +1 -delete
```

## Security Hardening

### 1. Create Dedicated User

```bash
sudo useradd -r -s /bin/false telegrambot
sudo chown -R telegrambot:telegrambot /opt/telegram-file-bot
```

Update service files to use `telegrambot` user.

### 2. Configure Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp  # if using HTTP server
sudo ufw enable
```

### 3. SSH Hardening

```bash
sudo nano /etc/ssh/sshd_config
```

Set:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

### 4. Fail2Ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Backup Strategy

### Backup Configuration

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/telegram-bot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env

# Keep last 7 days
find $BACKUP_DIR -name "config_*.tar.gz" -mtime +7 -delete
```

### Automated Backup

```bash
crontab -e
```

Add:
```
# Daily backup at 2 AM
0 2 * * * /opt/telegram-file-bot/backup.sh
```

## Troubleshooting

### Bot Not Starting

```bash
# Check logs
sudo journalctl -u telegram-file-bot -n 50

# Common issues:
# - Wrong bot token
# - Missing dependencies
# - Wrong file permissions
```

### Download Failures

```bash
# Check VPS internet connectivity
curl -I https://google.com

# Check disk space
df -h

# Check temp directory permissions
ls -la /opt/telegram-file-bot/downloads
```

### HTTP Server Issues

```bash
# Check if port is in use
sudo netstat -tlnp | grep 8080

# Test HTTP server
curl http://localhost:8080/health
```

### Memory Issues

```bash
# Check memory usage
free -h

# Add swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Performance Optimization

### 1. Increase File Descriptors

```bash
sudo nano /etc/systemd/system/telegram-file-bot.service
```

Add:
```
[Service]
LimitNOFILE=65536
```

### 2. Optimize Python

```bash
# Use PyPy for better performance (optional)
sudo apt install pypy3
```

### 3. CDN for Downloads

For very large files, consider using:
- Cloudflare R2
- AWS S3
- Backblaze B2

## Scaling

If you need to handle many users:

1. **Multiple Bot Instances**: Run multiple bots with different tokens
2. **Load Balancing**: Use Nginx to load balance HTTP servers
3. **Database**: Add PostgreSQL for tracking downloads
4. **Queue**: Use Redis/Celery for async download queue

## Network Bypassing for Iran

### Current Setup

Your setup already includes:
- **DNS Tunneling**: For Telegram access (slow but works)
- **VPS in Finland**: Unrestricted internet access
- **GitHub Fallback**: For storing files when direct downloads fail

### Additional Options

1. **Cloudflare Workers**: Proxy requests through Cloudflare
2. **Telegram Bot API via Proxy**: Use MTProto proxy
3. **Tor Network**: Alternative routing (slower)

### Integration with Existing Tools

Your current tools can be integrated:

**LatestReleaseMirror**: Use to mirror GitHub releases to your VPS
```bash
# Run on VPS
python mirror_releases.py --repo target/repo --output /opt/mirrored
```

**MasterDnsVPN**: Continue using for Telegram access
```bash
# Ensure DNS tunneling is running
# Bot will work through this connection
```

**MasterHttpRelayVPN-RUST**: Use for HTTP traffic if needed
```bash
# Configure as HTTP proxy in bot settings
HTTP_PROXY=http://localhost:8080
```

## Maintenance

### Regular Tasks

```bash
# Weekly: Check logs
sudo journalctl -u telegram-file-bot --since "7 days ago" | grep ERROR

# Weekly: Clean old downloads
find /opt/telegram-file-bot/downloads -type f -mtime +7 -delete

# Monthly: Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Monthly: Check disk usage
du -sh /opt/telegram-file-bot/*
```

### Updates

```bash
cd /opt/telegram-file-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart telegram-file-bot
sudo systemctl restart telegram-http-server
```

## Support

For issues:
1. Check logs: `sudo journalctl -u telegram-file-bot -f`
2. Check configuration: `.env` file
3. Test connectivity: `curl -I https://api.telegram.org`
4. Check GitHub issues in repository

## License

MIT License