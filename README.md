# Quick Start Guide

## Installation Complete ✅

All dependencies have been installed successfully:
- ✅ Python packages installed
- ✅ Playwright browser (Chromium) installed

## Before Running

### 1. Configure Your Environment

Edit `.env` file with your actual API keys:
```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
nano .env  # or use your preferred editor
```

**Required**:
- `TWILIO_SID` - From https://www.twilio.com/console
- `TWILIO_TOKEN` - From https://www.twilio.com/console

**Optional** (for future features):
- `CARFAX_API_KEY` - For vehicle valuation
- `SENDGRID_API_KEY` - For email notifications

### 2. Update Configuration

Edit `config.py` to set:
```python
TARGET_URLS = [
    "https://your-actual-listing-site.com/search",
    # Add more URLs
]

HOME_ZIP_CODE = "12345"  # Your actual ZIP code
PHONE_NUMBER = "+15551234567"  # Your phone number (E.164 format)
```

### 3. Customize Selectors (Optional)

The Hunter module uses generic CSS selectors. For best results, inspect your target websites and customize selectors in `modules/hunter.py` in the `extract_listing_data()` method.

## Run the Application

```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
python3 main.py
```

## What Happens Next

The system will:
1. 🌐 Initialize stealth browser session
2. 🔍 Scrape listings from your TARGET_URLS
3. ✅ Filter and score each vehicle
4. 💾 Save approved listings to database
5. 📱 Send SMS alerts for high-scoring finds (≥90)

## File Structure Reference

```
project_barnfind/
├── main.py              # Run this file
├── config.py            # Edit: URLs, ZIP, phone number
├── .env                 # Edit: API keys
├── requirements.txt
├── modules/
│   ├── hunter.py        # May need customization
│   ├── vetter.py        # Scoring logic
│   ├── ghost.py
│   └── herald.py
└── database/
    ├── ledger.json      # Auto-generated
    └── session.json     # Auto-generated
```

## Troubleshooting

**No listings found?**
- Check that TARGET_URLS are accessible
- Inspect the site HTML and update CSS selectors in `hunter.py`

**No SMS sent?**
- Verify Twilio credentials in `.env`
- Check phone number format (+15551234567)
- Ensure score ≥90 for immediate alerts

**Distance filtering not working?**
- Geopy requires internet connection
- Location must contain ZIP code or city name

## Next Steps

See [walkthrough.md](file:///Users/gabrielgaft/.gemini/antigravity/brain/b19a1bde-b79c-4a84-a96c-76f2456bf4f2/walkthrough.md) for complete documentation.
