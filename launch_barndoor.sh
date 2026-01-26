#!/bin/bash
# Launch Barndoor System (Backend API + Frontend Dashboard)

# 1. Kill old processes to ensure clean state
pkill -9 -f "python3 web_server.py"
pkill -9 -f "streamlit run dashboard.py"

# 2. Start Flask Backend (API) on 5050
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
nohup python3 web_server.py > web_server.log 2>&1 &

# 3. Start Streamlit Frontend (Dashboard) on 8501
nohup python3 -m streamlit run dashboard.py --server.port 8501 --server.headless true > dashboard.log 2>&1 &

# 4. Wait a moment for startup
sleep 3

# 5. Open Dashboard in Browser
open "http://localhost:8501"
