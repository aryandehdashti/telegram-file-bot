# Network Bypassing Guide for Restricted Environments

This guide explains how to use the Telegram File Download Bot in restricted network environments where internet access is limited or censored.

## Current Situation Analysis

### Network Restrictions in Censored Regions
- **Telegram**: Often filtered but accessible via DNS tunneling (slow)
- **GitHub**: Code files usually accessible, releases may be blocked
- **Direct Downloads**: Many sources blocked or severely throttled
- **International Services**: Limited access, high latency

### Common Tools Used
Users in restricted regions often use:
- **DNS Tunneling**: For accessing Telegram and other services
- **HTTP Relays**: For bypassing HTTP traffic filtering
- **VPN Services**: Various methods to circumvent censorship
- **VPS in Unrestricted Regions**: For full internet access

## How This Bot Helps

### Architecture Overview

```
[User in Restricted Region]
    ↓ (DNS Tunneling/VPN - May be slow)
[Telegram Bot]
    ↓ (API Call)
[VPS in Unrestricted Region]
    ↓ (Full Internet Access)
[Internet/Download Source]
    ↓ (File Download)
[VPS in Unrestricted Region]
    ↓ (Multiple Methods)
[User in Restricted Region]
```

### Why This Works

1. **VPS in Free World**: VPS in unrestricted region has full internet access
2. **Download on VPS**: Files are downloaded on the VPS, not your local machine
3. **Telegram Delivery**: Only Telegram messages go through your restricted connection
4. **Multiple Fallbacks**: If one method fails, others are available

## Network Bypassing Strategies

### Strategy 1: VPS-Based Download (Primary)

**How it works:**
- User sends URL to bot via Telegram
- Bot downloads file on Finland VPS (unrestricted)
- Bot sends file back via Telegram

**Pros:**
- ✅ Works with any URL
- ✅ No local bandwidth needed for download
- ✅ VPS handles all heavy lifting

**Cons:**
- ❌ Telegram connection is slow (DNS tunneling)
- ❌ File size limits on Telegram

**Best for:**
- Files <50MB (direct Telegram send)
- When you have stable Telegram connection

### Strategy 2: File Splitting

**How it works:**
- Large files (>50MB) split into chunks
- Each chunk sent separately via Telegram
- User combines chunks on their machine

**Pros:**
- ✅ Bypasses Telegram file size limits
- ✅ Works with files up to ~500MB
- ✅ No additional infrastructure needed

**Cons:**
- ❌ Requires manual file combination
- ❌ Multiple Telegram messages needed
- ❌ Still limited by Telegram speed

**Best for:**
- Files 50-500MB
- When HTTP server is not available

**How to combine chunks:**
```bash
# On Linux/Mac
cat filename_part1 filename_part2 filename_part3 > original_file.zip

# On Windows
copy /b filename_part1+filename_part2+filename_part3 original_file.zip
```

### Strategy 3: HTTP Server (Alternative)

**How it works:**
- VPS runs HTTP server
- Bot provides direct download link
- User downloads directly from VPS

**Pros:**
- ✅ No Telegram size limits
- ✅ Can handle very large files
- ✅ Faster if you have good proxy/VPN

**Cons:**
- ❌ May require proxy/VPN to access VPS
- ❌ Uses your local bandwidth for download
- ❌ VPS IP may be blocked

**Best for:**
- Files >500MB
- When you have good HTTP proxy/VPN

**Setup:**
```bash
# Enable in .env
ENABLE_HTTP_SERVER=True
HTTP_SERVER_PORT=8080

# Start HTTP server
python http_server.py

# Access via your proxy/VPN
http://your-vps-ip:8080/download/LINK_ID
```

**Integration with MasterHttpRelayVPN-RUST:**
```bash
# Run your HTTP relay
./MasterHttpRelayVPN-RUST

# Configure bot to use relay
HTTP_PROXY=http://localhost:RELAY_PORT
```

### Strategy 4: GitHub Storage (Fallback)

**How it works:**
- Files stored as base64 in GitHub repo
- Download via GitHub raw URLs
- GitHub code files accessible in Iran

**Pros:**
- ✅ GitHub code files work in Iran
- ✅ No VPS access needed for download
- ✅ Uses GitHub's CDN
- ✅ Works with your existing GitHub access

**Cons:**
- ❌ 25MB file size limit
- ❌ Requires GitHub account
- ❌ Base64 encoding increases size (~33%)
- ❌ Not private unless using private repo

**Best for:**
- Files <25MB
- When Telegram is very slow
- As backup storage method

**Setup:**
```bash
# Create GitHub personal access token
# Settings: Developer settings -> Personal access tokens
# Permissions: repo

# Create private repository
# Settings: Repositories -> New repository

# Configure bot
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your_username/your_private_repo
```

### Strategy 5: Hybrid Approach (Recommended)

**How it works:**
- Try Telegram first (fastest for small files)
- Fall back to file splitting for medium files
- Use HTTP server for large files (if proxy available)
- Use GitHub as backup when other methods fail

**Implementation:**
The bot automatically uses this strategy:
1. Files <50MB → Telegram direct
2. Files 50-500MB → File splitting
3. Files >500MB → HTTP server + GitHub option

## Integration with Existing Tools

### LatestReleaseMirror Integration

**Current use:** Mirror GitHub releases to accessible location

**Integration:**
```bash
# On your VPS
cd /opt
git clone https://github.com/Ehs6n/LatestReleaseMirror
cd LatestReleaseMirror

# Mirror a release
python mirror.py --repo target/repo --output /opt/mirrored

# Use mirrored URL in bot
# Send bot: http://your-vps-ip/mirrored/file.zip
```

**Benefits:**
- Pre-download popular releases
- Serve from your VPS (faster)
- Bypass GitHub release blocking

### MasterDnsVPN Integration

**Current use:** DNS tunneling for Telegram access

**Integration:**
```bash
# Ensure MasterDnsVPN is running
# Bot will automatically work through this connection

# No additional configuration needed
# Just ensure bot can reach Telegram API
```

**Optimization:**
- Keep DNS tunneling running 24/7
- Use stable DNS servers
- Monitor connection quality

### MasterHttpRelayVPN-RUST Integration

**Current use:** HTTP relay for web traffic

**Integration:**
```bash
# Start HTTP relay
cd /opt/MasterHttpRelayVPN-RUST
./master-http-relay

# Configure bot to use relay
# Add to .env:
HTTP_PROXY=http://localhost:RELAY_PORT
HTTPS_PROXY=http://localhost:RELAY_PORT

# Or configure in bot.py
session = aiohttp.ClientSession(proxy='http://localhost:RELAY_PORT')
```

**Benefits:**
- Access VPS HTTP server from Iran
- Bypass IP blocking
- Faster than DNS tunneling for HTTP

## Advanced Techniques

### Technique 1: Cloudflare Workers

**How it works:**
- Use Cloudflare Workers as proxy
- Hide VPS IP behind Cloudflare
- Access from Iran without direct VPS connection

**Setup:**
```javascript
// Cloudflare Worker script
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetUrl = 'http://your-vps-ip:8080' + url.pathname;
    
    const response = await fetch(targetUrl, {
      headers: request.headers
    });
    
    return response;
  }
};
```

**Benefits:**
- Cloudflare works in most countries
- No direct VPS IP exposure
- DDoS protection
- Global CDN

### Technique 2: Telegram Bot API via MTProto

**How it works:**
- Use MTProto proxy instead of HTTP API
- Direct connection to Telegram servers
- Bypasses some filtering

**Setup:**
```python
# Use Telethon instead of python-telegram-bot
# pip install telethon

from telethon import TelegramClient

client = TelegramClient('bot', api_id, api_hash)
await client.start(bot_token='your_token')
```

**Benefits:**
- More direct connection
- May work when HTTP API is blocked
- Better for large file transfers

### Technique 3: Tor Network

**How it works:**
- Route traffic through Tor
- Access VPS via .onion address
- Additional privacy layer

**Setup:**
```bash
# Install Tor on VPS
sudo apt install tor

# Configure hidden service
sudo nano /etc/tor/torrc
# Add:
HiddenServiceDir /var/lib/tor/telegram_bot/
HiddenServicePort 8080 127.0.0.1:8080

# Restart Tor
sudo systemctl restart tor

# Get .onion address
sudo cat /var/lib/tor/telegram_bot/hostname
```

**Benefits:**
- Works in most restrictive environments
- No IP blocking possible
- Additional privacy

**Cons:**
- Very slow
- Not all Tor nodes accessible from Iran

## Performance Optimization

### Optimization 1: Connection Pooling

```python
# Reuse connections
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
)
```

### Optimization 2: Compression

```python
# Enable compression for downloads
headers = {'Accept-Encoding': 'gzip, deflate'}
```

### Optimization 3: Caching

```python
# Cache frequently accessed files
# Use Redis or simple file-based cache
```

### Optimization 4: Parallel Downloads

```python
# Download multiple files in parallel
async def download_multiple(urls):
    tasks = [download_file(url) for url in urls]
    await asyncio.gather(*tasks)
```

## Security Considerations

### 1. VPS Security
- Use strong SSH keys
- Disable password authentication
- Configure firewall (ufw)
- Keep system updated

### 2. Bot Security
- Validate all URLs
- Rate limit per user
- Sanitize filenames
- Don't expose admin functions

### 3. Data Privacy
- Don't log sensitive data
- Clean up temporary files
- Use HTTPS when possible
- Consider encryption for sensitive files

### 4. Access Control
- Admin-only mode for dangerous operations
- User whitelisting
- File size limits
- Download quotas

## Troubleshooting Network Issues

### Issue: Telegram Very Slow

**Solutions:**
1. Check DNS tunneling quality
2. Try alternative DNS servers
3. Use MTProto proxy if available
4. Reduce file size limits

### Issue: Cannot Access VPS HTTP Server

**Solutions:**
1. Use HTTP relay (MasterHttpRelayVPN-RUST)
2. Set up Cloudflare Workers proxy
3. Use Tor hidden service
4. Check VPS firewall settings

### Issue: GitHub Not Working

**Solutions:**
1. Check GitHub token permissions
2. Verify repo exists and is accessible
3. Check file size (<25MB limit)
4. Try raw GitHub user content URLs

### Issue: Downloads Fail Randomly

**Solutions:**
1. Increase timeout settings
2. Implement retry logic
3. Check VPS internet connection
4. Monitor VPS resources (CPU, RAM, disk)

## Monitoring and Maintenance

### Monitoring Commands

```bash
# Check bot status
sudo systemctl status telegram-file-bot

# Check logs
sudo journalctl -u telegram-file-bot -f

# Check VPS resources
htop
df -h
free -h

# Check network connectivity
ping -c 4 google.com
curl -I https://api.telegram.org
```

### Maintenance Tasks

```bash
# Daily: Clean old downloads
0 0 * * * find /opt/telegram-file-bot/downloads -type f -mtime +1 -delete

# Weekly: Check logs for errors
sudo journalctl -u telegram-file-bot --since "7 days ago" | grep ERROR

# Monthly: Update dependencies
cd /opt/telegram-file-bot
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Monthly: Update system
sudo apt update && sudo apt upgrade -y
```

## Cost Considerations

### VPS Costs
- Finland VPS: ~$5-10/month
- Bandwidth: Usually included
- Storage: Monitor usage

### Alternative: Free Tiers
- Oracle Cloud Free Tier (always free)
- Google Cloud Free Tier (limited)
- AWS Free Tier (12 months)

### Optimization to Reduce Costs
- Compress files before storage
- Clean up old downloads regularly
- Use CDN for popular files
- Monitor bandwidth usage

## Legal and Ethical Considerations

### Important Notes
- Respect copyright and licenses
- Don't use for illegal activities
- Be aware of local laws
- Consider terms of service of platforms

### Best Practices
- Only download content you have right to access
- Don't abuse the service
- Implement rate limiting
- Be transparent about usage

## Conclusion

This bot provides multiple layers of network bypassing for Iran's restricted environment:

1. **Primary**: VPS-based download with Telegram delivery
2. **Fallback**: File splitting for medium files
3. **Alternative**: HTTP server for large files
4. **Backup**: GitHub storage when other methods fail

The hybrid approach ensures you can download files regardless of current network conditions. Start with the basic setup and gradually enable additional features as needed.

## Support and Resources

- **Telegram Bot API**: https://core.telegram.org/bots/api
- **python-telegram-bot**: https://docs.python-telegram-bot.org/
- **GitHub API**: https://docs.github.com/en/rest
- **Your Current Tools**:
  - LatestReleaseMirror: https://github.com/Ehs6n/LatestReleaseMirror
  - MasterDnsVPN: https://github.com/masterking32/MasterDnsVPN
  - MasterHttpRelayVPN-RUST: https://github.com/therealaleph/MasterHttpRelayVPN-RUST

## License

MIT License