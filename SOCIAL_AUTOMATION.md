# Social Automation Features

## Overview

The Ghost module now includes two powerful automation classes for Facebook:

### 🎭 Socializer
Simulates human-like activity on Facebook to avoid detection as a bot.

**Actions:**
- 👍 Like random posts
- 👀 Watch random stories (5 seconds)
- 🔍 Browse random groups (10 seconds)

**Scheduling:**
- Runs automatically at random intervals (1-4 hours)
- Integrated into the main scheduler
- Simulates unpredictable human behavior

### 👤 AccountCreator
Automates Facebook account registration and phone verification.

**Features:**
- Create new Facebook accounts programmatically
- Automated form filling
- SMS phone number verification

---

## Usage

### Socializer (Automatic)

The Socializer runs automatically when you start the main application:

```bash
python3 main.py
```

Output example:
```
📅 SCHEDULER STARTED
============================================================
⏰ Pipeline runs every 10 minutes
📧 Daily digest email sent at midnight
🎭 Social activity runs at random intervals (1-4 hours)
...
📅 Next social activity scheduled in 2.3 hours
```

The scheduler will automatically:
1. Run social activity at the scheduled random time
2. Choose a random action (like post, watch story, or browse group)
3. Schedule the next run at another random interval

### AccountCreator (Manual)

Use the provided example script:

```bash
python3 create_account_example.py
```

Or integrate into your own code:

```python
from modules.ghost import Ghost

# Initialize Ghost
ghost = Ghost()
ghost.execute()

# Get AccountCreator
account_creator = ghost.get_account_creator()

# Create account
account_creator.create_account(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    password="SecurePass123!",
    phone_number="+15551234567"
)

# Verify with SMS code
account_creator.verify_phone_number("123456")

# Cleanup
ghost.close()
```

---

## How It Works

### Socializer Architecture

```
Main Scheduler
    ↓
Random Interval (1-4 hours)
    ↓
run_social_activity()
    ↓
Ghost.run_random_social_activity()
    ↓
Open Facebook → Socializer.run() → Random Action
    ↓
Schedule Next (1-4 hours later)
```

### Random Action Selection

The Socializer randomly chooses one action per run:
- 33% chance: Like a post
- 33% chance: Watch a story
- 33% chance: Browse a group

This unpredictability mimics real human browsing patterns.

---

## Benefits

✅ **Bot Detection Avoidance**: Random intervals and actions appear human-like
✅ **Session Persistence**: Maintains cookies between runs
✅ **Stealth Browsing**: Uses Ghost's user-agent rotation
✅ **Flexible**: Can be called manually or run automatically
✅ **Error Resistant**: Gracefully handles missing elements

---

## Advanced Usage

### Manual Socializer Control

```python
from modules.ghost import Ghost

ghost = Ghost()
ghost.execute()

# Get a new page
page = ghost.context.new_page()
page.goto('https://www.facebook.com')

# Create Socializer
socializer = ghost.get_socializer(page)

# Run specific actions
socializer.like_random_post()
socializer.watch_random_story()
socializer.browse_random_group()

# Or run random action
socializer.run()

ghost.close()
```

### Disable Social Activity

If you want to run the main application WITHOUT social activity:

1. Comment out lines in `main.py`:
```python
# schedule_next_social_activity()  # Comment this line
```

2. Or set a very long interval (e.g., 24 hours):
```python
schedule.every(24).hours.do(run_social_activity)
```

---

## Important Notes

### Facebook Login
- The Socializer assumes you're already logged into Facebook
- Cookies are loaded from `database/session.json`
- You may need to manually log in once and save cookies

### Account Creation Limits
- Facebook has rate limits on account creation
- Use unique email addresses
- Phone numbers must be able to receive SMS
- Follow Facebook's Terms of Service

### Legal Considerations
⚠️ **Warning**: Automating Facebook interactions may violate their Terms of Service. Use responsibly and at your own risk.

---

## Troubleshooting

**Social activity not working?**
- Ensure you're logged into Facebook (check cookies)
- Facebook's HTML structure may have changed (update selectors)
- Check network connection

**Account creation fails?**
- Verify email is not already used
- Check phone number format (+15551234567)
- Facebook may require CAPTCHA (not automated)

**Random intervals too frequent/infrequent?**
- Adjust in `main.py` → `schedule_next_social_activity()`
- Change `random.uniform(1, 4)` to your desired range

---

## Files Modified

- [`modules/ghost.py`](file:///Users/gabrielgaft/Desktop/Barndoor/project_barnfind/modules/ghost.py) - Added Socializer & AccountCreator classes
- [`main.py`](file:///Users/gabrielgaft/Desktop/Barndoor/project_barnfind/main.py) - Integrated social activity scheduler
- [`create_account_example.py`](file:///Users/gabrielgaft/Desktop/Barndoor/project_barnfind/create_account_example.py) - Example usage script
