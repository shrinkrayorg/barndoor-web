#!/bin/bash
# Install Barnfind as a macOS LaunchAgent and Menu Bar App

set -e

echo "🚗 Barnfind macOS Installation"
echo "=============================="
echo ""

# Get the project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.barnfind.menubar.plist"

# Step 1: Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -q rumps

# Step 2: Create LaunchAgent for menu bar app
echo "⚙️  Creating LaunchAgent configuration..."
cat > "$LAUNCH_AGENT_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.barnfind.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>$PROJECT_DIR/menu_bar_app.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
EOF

# Step 3: Make script executable
chmod +x "$PROJECT_DIR/menu_bar_app.py"

# Step 4: Load the LaunchAgent
echo "🚀 Starting menu bar app..."
launchctl unload "$LAUNCH_AGENT_PLIST" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT_PLIST"

echo ""
echo "✅ Installation complete!"
echo ""
echo "🎯 The Barnfind menu bar app should now appear in your menu bar (🚗)"
echo ""
echo "Controls:"
echo "  • Click the 🚗 icon to access controls"
echo "  • Start/Stop the background service"
echo "  • View statistics and logs"
echo ""
echo "To uninstall:"
echo "  launchctl unload $LAUNCH_AGENT_PLIST"
echo "  rm $LAUNCH_AGENT_PLIST"
echo ""
