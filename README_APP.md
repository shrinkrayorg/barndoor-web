# Barnfind GUI Application

## Quick Start

### Option 1: Double-Click to Launch (Easiest)

1. Find the file `launch_barnfind.command` in the project folder
2. **Double-click it** - a window will open!

### Option 2: Run from Terminal

```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
python3 barnfind_app.py
```

---

## What You'll See

A window will open that looks like this:

```
┌────────────────────────────────────┐
│         🚗 Barnfind                │  ← Title bar
├────────────────────────────────────┤
│  Service Status                    │
│  ✅ Service Running                │
├────────────────────────────────────┤
│ [▶️  Start Service] [⏹ Stop Service]│  ← Buttons
├────────────────────────────────────┤
│  Statistics                        │
│  Total Listings: 42                │
│  Last Run: 2026-01-24 11:30        │
│  Status: Running                   │
├────────────────────────────────────┤
│  Recent Logs                       │
│  ┌──────────────────────────────┐ │
│  │ Pipeline logs appear here... │ │  ← Scrollable log view
│  │                              │ │
│  └──────────────────────────────┘ │
│         [🔄 Refresh Logs]         │
└────────────────────────────────────┘
```

---

## How to Use

### Start the Service
1. Click the **green "▶️ Start Service"** button
2. You'll see "Service Running" at the top
3. Logs will start appearing in the bottom section

### Stop the Service
1. Click the **red "⏹ Stop Service"** button
2. Service stops immediately

### View Statistics
- The middle section shows:
  - How many vehicle listings found
  - When the pipeline last ran
  - Current status

### View Logs
- Bottom section shows recent activity
- Click "🔄 Refresh Logs" to update
- Auto-refreshes every 5 seconds

---

## Keep It Running

### Option A: Leave Window Open
- Keep the Barnfind window open
- Service runs in background
- Close window to stop everything

### Option B: Run at Login (Auto-Start)
1. Open **System Settings** → **General** → **Login Items**
2. Click the **"+"** button under "Open at Login"
3. Navigate to: `/Users/gabrielgaft/Desktop/Barndoor/project_barnfind`
4. Select `launch_barnfind.command`
5. Click **Add**

Now Barnfind will open automatically when you log in!

---

## Create a Desktop Shortcut

To put Barnfind on your Desktop:

```bash
ln -s /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/launch_barnfind.command ~/Desktop/Barnfind
```

Now you have a "Barnfind" icon on your Desktop - just double-click to launch!

---

## Add to Dock

1. Open the Barnfind app
2. The Python rocket icon will appear in your Dock
3. **Right-click** the icon
4. Select **Options** → **Keep in Dock**

Now it stays in your Dock even after closing!

---

## Troubleshooting

### "Permission Denied" Error
Run this:
```bash
chmod +x /Users/gabrielgaft/Desktop/Barndoor/project_barnfind/launch_barnfind.command
```

### Window Doesn't Open
Make sure Python 3 with tkinter is installed:
```bash
python3 -m tkinter
```
A test window should appear. If not, tkinter needs to be installed.

### Can't Start Service
- Check that you've configured `.env` with API keys
- Look at the logs in the bottom panel for errors

---

## Comparison

| Feature | GUI App | Menu Bar App |
|---------|---------|--------------|
| Visual window | ✅ Yes | ❌ No |
| In Applications | ✅ Yes | ❌ No |
| Always visible | ❌ No (close window) | ✅ Yes (top bar) |
| View logs | ✅ Built-in | ⚠️ External |
| Ease of use | ✅ Very easy | ⚠️ Need to find icon |

**You now have the GUI app!** It's a regular application with a window.
