#!/bin/bash

# 1. Kill existing processes
echo "🛑 Stopping existing Barndoor services..."
pkill -f "python main.py"
pkill -f "streamlit run dashboard.py"

# Wait a moment
sleep 1

# 2. Launch Main (Backend) in a new Terminal tab
echo "🚀 Starting Backend (main.py)..."
osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'\" && python3 main.py"'

# 3. Launch Dashboard (Frontend) in a new Terminal tab
echo "📊 Starting Dashboard (dashboard.py)..."
osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'\" && streamlit run dashboard.py"'

echo "✅ Restart Complete! Check the new Terminal windows."
