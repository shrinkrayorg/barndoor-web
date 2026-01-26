# Scheduler & Email Digest Update

## What's New

### ⏰ Automated Scheduling
The application now runs continuously with:
- **Pipeline execution every 10 minutes** - Automatically scrapes, vets, and saves new listings
- **Daily digest email at midnight** - Sends HTML email via SendGrid with all 70-89 score listings

### 📧 Daily Digest Email
Beautiful HTML-formatted email includes:
- Summary count of medium-score vehicles
- Detailed listing cards with title, score, price, location, mileage
- Visual tags for each vehicle
- Direct links to view listings
- Professional styling with color-coded elements

## Running the Application

```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
python3 main.py
```

The scheduler will:
1. Initialize all modules once
2. Run the pipeline immediately
3. Continue running every 10 minutes
4. Send email digest at midnight (00:00)
5. Press `Ctrl+C` to stop gracefully

## Configuration Required

### Update `.env`
```bash
SENDGRID_API_KEY=your_sendgrid_api_key_here
```

### Update `config.py`
```python
FROM_EMAIL = "barnfind@yourdomain.com"  # Must be verified in SendGrid
TO_EMAIL = "your-email@example.com"     # Where to receive daily digest
```

## How It Works

### Scheduled Pipeline (Every 10 Minutes)
```
Initialize (once) → Run Pipeline → Wait 10 min → Run Pipeline → ...
                           ↓
                    Hunter → Vetter → Database → Herald
```

### Daily Digest (Midnight)
```
Midnight trigger → Collect digest (score 70-89) → Format HTML email → 
Send via SendGrid → Clear digest
```

### Score-Based Notifications
- **Score ≥90**: Immediate SMS via Twilio
- **Score 70-89**: Added to daily digest, sent via email at midnight
- **Score <70**: Logged only

## Example Daily Digest Email

```
🚗 Barnfind Daily Digest

Summary: 12 vehicles found with scores between 70-89

1. 2018 Honda CR-V EX
   Score: 85
   $16,200
   📍 Chicago, IL | 🛣️ 45,000 miles
   [reliable_make] [suv_bonus]
   [View Listing →]

2. 2019 Toyota Camry SE
   Score: 72
   $14,500
   📍 Milwaukee, WI | 🛣️ 62,000 miles
   [reliable_make]
   [View Listing →]
...
```

## Benefits

✅ **Set and Forget**: Runs continuously without manual intervention
✅ **Immediate Alerts**: High-value finds (90+) still trigger SMS instantly
✅ **Daily Summary**: Medium-value finds organized in a single email
✅ **Resource Efficient**: Reuses browser context across runs
✅ **Error Resilient**: Catches and logs errors, continues operation

## Stopping the Scheduler

Press `Ctrl+C` to stop gracefully. The application will:
1. Complete current operation
2. Save session cookies
3. Close browser and database connections
4. Exit cleanly

## Verification

After adding your SendGrid credentials, the scheduler will:
- ✅ Install `schedule` library (already complete)
- ✅ Initialize modules once at startup
- ✅ Run pipeline every 10 minutes
- ✅ Queue listings scored 70-89 in daily digest
- ✅ Send HTML email at midnight with digest
- ✅ Clear digest after successful send

## Next Steps

1. Get SendGrid API key: https://app.sendgrid.com/settings/api_keys
2. Verify sender email in SendGrid
3. Update `.env` and `config.py` with credentials
4. Run `python3 main.py` and let it run continuously
