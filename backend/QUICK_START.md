# Quick Start Guide - Telegram Member Adder v2.0

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies
Double-click `setup.bat` or run:
```bash
py -m pip install -r requirements.txt
```

### Step 2: Configure API Credentials
1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Edit `.env` and add your credentials from [my.telegram.org](https://my.telegram.org)

### Step 3: Run the Tool
Double-click `run.bat` or run:
```bash
py telegram_member_adder.py
```

## 📱 First Time Setup

When you run the tool for the first time:

1. **Enter API Credentials** (if not in .env)
2. **Add Phone Numbers** with country code (e.g., +1234567890)
3. **Specify Groups**:
   - Source: Group to scrape from (username or link)
   - Target: Group to add members to (username)

## 🎯 Common Workflows

### Just Want to Scrape Members?
1. Run the tool
2. Select option 1: "Scrape members from source group"
3. Find your CSV file in the `output` folder

### Add Members from Previous Scraping?
1. Run the tool
2. Select option 2: "Add members to target group"
3. Choose from your saved CSV files

### Do Both Operations?
1. Run the tool
2. Select option 3: "Both (scrape then add)"

## ⚡ Pro Tips

- **Use multiple accounts** for faster processing
- **Enable proxies** if you hit rate limits
- **Check logs** in `telegram_member_adder.log` for details
- **Resume operations** using saved progress
- **Filter settings** in `config.py` can exclude unwanted users

## ❓ Need Help?

Check the main README.md for:
- Detailed configuration options
- Troubleshooting common issues
- Safety guidelines and best practices

## 🛡️ Important Reminders

- Use responsibly and遵守 Telegram's Terms of Service
- Start with small batches to test
- Monitor your accounts for restrictions
- Respect group rules and user privacy