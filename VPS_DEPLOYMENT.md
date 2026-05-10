# VPS Deployment Guide for Your Setup

This guide is specifically for deploying to your VPS at `65.109.196.183`.

## Your Current Configuration

- **VPS IP**: 65.109.196.183
- **GitHub Storage**: aryandehdashti/DL-portal
- **Bot Token**: Configured
- **Admin User ID**: 109539684

## Quick Deployment Steps

### 1. SSH into Your VPS

```bash
ssh root@65.109.196.183
```

### 2. Navigate to Project Directory

```bash
cd /root/telegram-file-bot
```

### 3. Create Virtual Environment (if not exists)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Create .env File

```bash
nano .env
```

Paste your configuration:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_telegram_user_id
MAX_FILE_SIZE_MB=50
TEMP_DOWNLOAD_DIR=/tmp/telegram_bot_downloads
ENABLE_HTTP_SERVER=True
HTTP_SERVER_PORT=8080
VPS_HOST=your_vps_ip_address
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your_github_username/your_storage_repo
GITHUB_BRANCH=main
LOG_LEVEL=INFO
LOG_FILE=/var/log/telegram_file_bot.log
```

Save and exit (Ctrl+X, Y, Enter)

### 6. Create Necessary Directories

```bash
mkdir -p /tmp/telegram_bot_downloads
mkdir -p /var/log
```

### 7. Test the Bot

```bash
source venv/bin/activate
python bot.py
```

If it starts successfully, press Ctrl+C to stop it.

### 8. Install Systemd Service

```bash
cp telegram-file-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable telegram-file-bot
systemctl start telegram-file-bot
```

### 9. Check Service Status

```bash
systemctl status telegram-file-bot
```

### 10. View Logs

```bash
journalctl -u telegram-file-bot -f
```

## Troubleshooting Your Specific Issues

### Issue 1: Syntax Error (FIXED)

The syntax error `async with outside async function` has been fixed in the latest code.

### Issue 2: Systemd Service Error (FIXED)

The service files have been updated with correct paths:
- User: root
- WorkingDirectory: /root/telegram-file-bot
- Python path: /root/telegram-file-bot/venv/bin/python

### Issue 3: Service Still Failing

If the service still fails after updating:

1. **Check the actual error**:
```bash
journalctl -u telegram-file-bot -n 50
```

2. **Test manually first**:
```bash
cd /root/telegram-file-bot
source venv/bin/activate
python bot.py
```

3. **Check dependencies**:
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Firewall Configuration

Allow HTTP server port:

```bash
ufw allow 8080/tcp
```

Or using iptables:

```bash
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
```

## Testing the Bot

### 1. Test Bot Response
Send `/start` to your bot in Telegram

### 2. Test Download
Send a test URL:
```
https://example.com/test-file.zip
```

### 3. Test GitHub Storage
Choose "GitHub Download" option and check if file appears in:
https://github.com/aryandehdashti/DL-portal

### 4. Test HTTP Server
If you choose HTTP download, test:
```
http://65.109.196.183:8080/health
```

## Updating the Bot

When you push changes to GitHub:

```bash
cd /root/telegram-file-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart telegram-file-bot
```

## Monitoring

### Check Service Status
```bash
systemctl status telegram-file-bot
```

### View Real-time Logs
```bash
journalctl -u telegram-file-bot -f
```

### Check Disk Space
```bash
df -h
du -sh /tmp/telegram_bot_downloads
```

### Check Memory
```bash
free -h
```

## Automatic Cleanup

### Local Download Cleanup

Add cron job to clean old downloads:

```bash
crontab -e
```

Add:
```
# Clean downloads older than 24 hours
0 0 * * * find /tmp/telegram_bot_downloads -type f -mtime +1 -delete
```

### GitHub Storage Cleanup

Add cron job to automatically clean up GitHub storage:

```bash
crontab -e
```

Add:
```
# Clean GitHub storage daily at 2 AM (keeps files older than 7 days, keeps repo under 500MB, keeps 10 recent files)
0 2 * * * cd /root/telegram-file-bot && source venv/bin/activate && python cleanup_github.py >> /var/log/github_cleanup.log 2>&1
```

You can customize the cleanup schedule and parameters:

- **Schedule**: Change `0 2 * * *` to your preferred time (format: minute hour day month weekday)
- **Age limit**: Add `--age N` to change days threshold (default: 7)
- **Size limit**: Add `--size N` to change MB threshold (default: 500)
- **Keep recent**: Add `--keep N` to change number of recent files to keep (default: 10)

Examples:
```
# Clean every 6 hours, delete files older than 3 days, keep repo under 1GB
0 */6 * * * cd /root/telegram-file-bot && source venv/bin/activate && python cleanup_github.py --age 3 --size 1024 >> /var/log/github_cleanup.log 2>&1

# Clean weekly, delete files older than 30 days, keep 20 recent files
0 0 * * 0 cd /root/telegram-file-bot && source venv/bin/activate && python cleanup_github.py --age 30 --keep 20 >> /var/log/github_cleanup.log 2>&1
```

### Manual Cleanup

You can also trigger cleanup manually from Telegram as admin:

- `/cleanup` - Run automatic cleanup (both age and size based)
- `/cleanup age` - Clean only by age
- `/cleanup size` - Clean only by size

Or run the cleanup script manually from SSH:

```bash
cd /root/telegram-file-bot
source venv/bin/activate
python cleanup_github.py
```

To see what would be deleted without actually deleting:

```bash
python cleanup_github.py --dry-run
```

## Security Notes

⚠️ **Important Security Notes**:

1. **Your GitHub Token**: Your GitHub token is in your .env file
   - Make sure your storage repository is PRIVATE
   - Consider rotating this token if it becomes compromised

2. **Your Bot Token**: The bot token is also in .env
   - Keep the .env file secure
   - Don't commit it to git

3. **VPS Security**:
   - Use SSH keys instead of password authentication
   - Keep your system updated: `apt update && apt upgrade -y`
   - Configure firewall properly

## Alternative: Use Combined Service

If you want to run both bot and HTTP server together:

```bash
cp telegram-file-bot-combined.service /etc/systemd/system/
systemctl daemon-reload
systemctl disable telegram-file-bot
systemctl disable telegram-http-server
systemctl enable telegram-file-bot-combined
systemctl start telegram-file-bot-combined
```

## Support

If you encounter issues:

1. Check logs: `journalctl -u telegram-file-bot -n 100`
2. Test manually: `python bot.py`
3. Check configuration: `cat .env`
4. Verify GitHub repo exists and is accessible
5. Check VPS internet connectivity: `curl -I https://api.telegram.org`