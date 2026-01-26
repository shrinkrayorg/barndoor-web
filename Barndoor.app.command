#!/bin/bash
# Barndoor Launcher - Opens in browser without terminal window

# Set project directory
PROJECT_DIR="/Users/gabrielgaft/Desktop/Barndoor/project_barnfind"

# Kill any existing Flask server
pkill -f "python3 web_server.py" 2>/dev/null

# Start Flask server in background
cd "$PROJECT_DIR"
nohup python3 web_server.py > /dev/null 2>&1 &

# Wait a moment for server to start
sleep 2

# Open in default browser
open "http://localhost:5050"

# Exit immediately (don't keep terminal open)
exit 0
