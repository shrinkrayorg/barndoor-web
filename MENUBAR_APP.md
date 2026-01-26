# macOS Menu Bar App Guide

## Overview

Barnfind now runs as a **native macOS application** with:
- 🚗 **Menu bar icon** - Quick access from your menu bar
- 🔄 **Auto-start on login** - Launches automatically via LaunchAgent
- ⚙️ **Visual controls** - Start/stop the service with a click
- 📊 **Live statistics** - View listing counts and last run time
- 📋 **Log access** - Open logs in Console app

---

## Installation

### Quick Install

```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
./install_menubar.sh
```

This will:
1. Install the `rumps` library
2. Create a LaunchAgent configuration
3. Start the menu bar app automatically

### Manual Install

If you prefer to do it manually:

```bash
# Install rumps
pip3 install rumps

# Create LaunchAgent
cp ~/Library/LaunchAgents/com.barnfind.menubar.plist ~/Library/LaunchAgents/

# Load the agent
launchctl load ~/Library/LaunchAgents/com.barnfind.menubar.plist
```

---

## Usage

### Menu Bar Icon

Look for the **🚗** icon in your menu bar (top-right of your screen).

**Icon States:**
- 🚗 = Service running
- 🚗💤 = Service stopped

### Menu Options

Click the 🚗 icon to see:

```
Status: ✅ Running
─────────────────
▶️  Start Service
⏹  Stop Service  
🔄 Restart Service
─────────────────
📊 Statistics
📋 View Logs
─────────────────
Quit Barnfind
```

### Controls

**▶️ Start Service**
- Starts the Barnfind pipeline in background
- Begins scraping, vetting, and notifications
- Shows system notification on start

**⏹ Stop Service**
- Gracefully stops the background service
- Preserves all data and cookies
- Shows system notification on stop

**🔄 Restart Service**
- Stops then starts the service
- Useful after config changes

**📊 Statistics**
- Shows total listings in database
- Displays last pipeline run time
- Shows current service status

**📋 View Logs**
- Opens logs in macOS Console app
- View real-time output of the service

---

## How It Works

### Architecture

```
LaunchAgent (starts on login)
    ↓
Menu Bar App (menu_bar_app.py)
    ↓
Controls Background Service (main.py)
    ↓
Runs: Pipeline, Social Activity, Digest
```

### Background Service

When you click "Start Service":
1. Launches `main.py` as a background process
2. Saves process ID (PID) to `barnfind.pid`
3. Redirects output to `barnfind.log`
4. Service runs continuously with scheduler

### Persistence

- **Menu bar app**: Runs always (via LaunchAgent)
- **Background service**: Only runs when you start it
- **Auto-start service** (optional): See configuration below

---

## Configuration

### Auto-Start Service on Login

If you want the **service itself** to start automatically:

Edit `menu_bar_app.py` and add to `__init__`:

```python
# Auto-start service if not running
if not self.is_service_running():
    self.start_service(None)
```

### Change Menu Bar Icon

The default icon is 🚗 emoji. To use a custom image:

1. Create a 22x22 pixel image (PNG with transparency)
2. Save as `icon.png` in project directory
3. Update `menu_bar_app.py`:

```python
super(BarnfindApp, self).__init__(
    "Barnfind",
    icon="icon.png",  # Path to your icon
    quit_button=None
)
```

### Notifications

macOS notifications are sent on:
- Service start
- Service stop

To disable, remove `rumps.notification()` calls from `menu_bar_app.py`

---

## Troubleshooting

### Menu Bar Icon Not Showing

```bash
# Check if LaunchAgent is loaded
launchctl list | grep barnfind

# Reload the agent
launchctl unload ~/Library/LaunchAgents/com.barnfind.menubar.plist
launchctl load ~/Library/LaunchAgents/com.barnfind.menubar.plist
```

### Service Won't Start

1. Check permissions:
```bash
chmod +x /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/menu_bar_app.py
```

2. Verify Python path:
```bash
which python3
# If not /usr/local/bin/python3, update LaunchAgent plist
```

3. Check logs:
```bash
tail -f /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/barnfind.log
```

### "Status: Stopped" But Service Running

The PID file may be stale:
```bash
rm /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/barnfind.pid
# Then restart via menu bar
```

---

## Uninstallation

### Complete Removal

```bash
# Stop and unload LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.barnfind.menubar.plist

# Remove LaunchAgent
rm ~/Library/LaunchAgents/com.barnfind.menubar.plist

# Remove PID file
rm /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/barnfind.pid
```

### Keep App, Remove Auto-Start

```bash
# Just unload the LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.barnfind.menubar.plist
```

You can still run the menu bar app manually:
```bash
python3 /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/menu_bar_app.py
```

---

## Advanced

### Run Multiple Instances

To run separate instances (e.g., different configs):

1. Copy project to new directory
2. Update LaunchAgent label (com.barnfind.menubar2)
3. Change menu bar title in `menu_bar_app.py`

### Custom Keyboard Shortcuts

Add to `menu_bar_app.py`:

```python
@rumps.clicked("Start Service")
@rumps.shortkey("s")
def start_with_shortcut(self, _):
    self.start_service(_)
```

---

## Files

- [`menu_bar_app.py`](file:///Users/gabrielgaft/Desktop/Barndoor/project_barnfind/menu_bar_app.py) - Menu bar application
- [`install_menubar.sh`](file:///Users/gabrielgaft/Desktop/Barndoor/project_barnfind/install_menubar.sh) - Installation script
- `~/Library/LaunchAgents/com.barnfind.menubar.plist` - LaunchAgent config
- `barnfind.pid` - Process ID file (auto-generated)
- `barnfind.log` - Service output log (auto-generated)

---

## Screenshots

**Menu Bar:**
```
🚗 ← Click here
```

**Dropdown Menu:**
```
┌──────────────────────┐
│ Status: ✅ Running   │
├──────────────────────┤
│ ▶️  Start Service    │
│ ⏹  Stop Service      │
│ 🔄 Restart Service   │
├──────────────────────┤
│ 📊 Statistics        │
│ 📋 View Logs         │
├──────────────────────┤
│ Quit Barnfind        │
└──────────────────────┘
```

**Statistics Dialog:**
```
┌─────────────────────────────┐
│  📊 Barnfind Statistics     │
├─────────────────────────────┤
│  Total Listings: 47         │
│  Last Run: 2026-01-24 11:30 │
│  Service Status: Running    │
│                             │
│          [  OK  ]           │
└─────────────────────────────┘
```
