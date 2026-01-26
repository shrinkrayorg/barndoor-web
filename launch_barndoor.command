#!/usr/bin/osascript
-- Launch Barndoor without showing terminal
-- This AppleScript opens the app invisibly

do shell script "cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind && python3 web_server.py > /dev/null 2>&1 &"
