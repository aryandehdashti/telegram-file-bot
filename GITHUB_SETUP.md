# GitHub Repository Setup Instructions

## Step 1: Create the Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `telegram-file-bot`
3. Description: `Telegram bot for downloading files in Iran's restricted network environment with multiple download methods`
4. Make it **Public** (so raw URLs work)
5. **Don't** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Push the Code

After creating the repository, GitHub will show you instructions. Run these commands in the telegram-file-bot directory:

```bash
cd C:\Users\arian\Documents\source\Projrcts\telegram-file-bot

# Add the remote repository
git remote add origin https://github.com/aryandehdashti/telegram-file-bot.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 3: Configure GitHub Integration

After pushing, you need to configure GitHub integration for the bot to store files:

### Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Note: "Generate new token" (classic) is important for the bot to work
4. Set expiration (choose 90 days or no expiration)
5. Select scopes:
   - ✅ `repo` (full control of private repositories)
   - ✅ `workflow` (for GitHub Actions if needed)
6. Click "Generate token"
7. **Copy the token immediately** (you won't see it again!)

### Create a Private Repository for File Storage (Optional but Recommended)

For storing downloaded files, you have two options:

**Option 1: Use the same repository (simpler)**
- Files will be stored in the main `telegram-file-bot` repository
- Raw URLs will work but files will be public

**Option 2: Create a separate private repository (recommended)**
1. Go to https://github.com/new
2. Repository name: `telegram-file-downloads` (or any name you prefer)
3. Make it **Private**
4. Create the repository
5. Your bot will store files here (more secure)

### Update .env Configuration

Edit your `.env` file and add:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=aryandehdashti/telegram-file-bot  # or aryandehdashti/telegram-file-downloads for private repo
GITHUB_BRANCH=main
```

## Step 4: Test the GitHub Integration

1. Start the bot: `python bot.py`
2. Send a small test URL to the bot
3. Choose "GitHub Download" option
4. Check if the file appears in your GitHub repository
5. Test the raw URL to ensure it works

## Important Notes

### Why Public Repository?

- **Raw URLs**: GitHub raw URLs work best with public repositories
- **Accessibility**: Public repositories are more accessible from Iran
- **No Authentication**: Raw URLs don't require authentication for public repos

### If Using Private Repository

- Raw URLs will require authentication
- You'll need to handle authentication in the bot
- More complex but more secure

### File Size Limits

- GitHub: 25MB per file (hard limit)
- Telegram: 50MB per file (2GB for Premium)
- For larger files, the bot will automatically suggest other methods

## Troubleshooting

### Push Fails with "Authentication Required"

```bash
# Configure git credentials
git config --global user.name "aryandehdashti"
git config --global user.email "your-email@example.com"

# Or use GitHub CLI if you install it later
# gh auth login
```

### GitHub Storage Fails

1. Check your GitHub token has `repo` permissions
2. Verify the repository name is correct
3. Ensure the repository exists and is accessible
4. Check file size is under 25MB

### Raw URLs Don't Work

1. Ensure repository is public
2. Check the raw URL format: `https://raw.githubusercontent.com/user/repo/branch/filename`
3. Test the URL in your browser first

## Next Steps

After successful setup:

1. Deploy the bot to your Finland VPS
2. Configure VPS_HOST in .env with your VPS IP/domain
3. Test all download methods
4. Set up monitoring and logging
5. Consider setting up GitHub Actions for automated tasks

## Security Best Practices

1. **Never commit .env file** - it's already in .gitignore
2. **Use environment variables** for sensitive data
3. **Rotate GitHub tokens** regularly
4. **Use private repository** for file storage if possible
5. **Monitor repository** for unauthorized access
6. **Implement rate limiting** to prevent abuse