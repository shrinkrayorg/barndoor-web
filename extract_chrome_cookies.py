#!/usr/bin/env python3
"""
Extract Facebook cookies from Chrome and import to persistent browser profile.
Requires Chrome to be CLOSED before running.
"""
import os
import sqlite3
import json
import shutil
from pathlib import Path

def get_chrome_cookies_db():
    """Find Chrome's cookies database."""
    home = Path.home()
    chrome_paths = [
        home / "Library/Application Support/Google/Chrome/Default/Cookies",
        home / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
    ]
    
    for path in chrome_paths:
        if path.exists():
            return str(path)
    
    return None

def extract_facebook_cookies():
    """Extract Facebook cookies from Chrome."""
    cookies_db = get_chrome_cookies_db()
    
    if not cookies_db:
        print("❌ Chrome cookies database not found!")
        print("\nSearched:")
        print("  ~/Library/Application Support/Google/Chrome/Default/Cookies")
        print("  ~/Library/Application Support/Google/Chrome/Profile 1/Cookies")
        return None
    
    print(f"✅ Found Chrome cookies: {cookies_db}")
    
    # Make a temporary copy (can't read while Chrome is open)
    temp_db = "temp_cookies.db"
    try:
        shutil.copy2(cookies_db, temp_db)
    except Exception as e:
        print(f"❌ Error copying cookies (is Chrome running?): {e}")
        print("\n⚠️  Please CLOSE Chrome completely and try again!")
        return None
    
    # Extract Facebook cookies
    cookies = []
    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Query for facebook.com cookies
        cursor.execute("""
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly, samesite
            FROM cookies 
            WHERE host_key LIKE '%facebook.com%'
        """)
        
        for row in cursor.fetchall():
            name, value, domain, path, expires, secure, httponly, samesite = row
            
            # Convert Chrome timestamp to seconds
            if expires:
                # Chrome uses microseconds since 1601-01-01
                # Unix timestamp is seconds since 1970-01-01
                expires_seconds = (expires / 1000000) - 11644473600
            else:
                expires_seconds = -1
            
            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "expires": expires_seconds,
                "httpOnly": bool(httponly),
                "secure": bool(secure),
                "sameSite": "None" if samesite == -1 else ("Strict" if samesite == 1 else "Lax")
            }
            cookies.append(cookie)
        
        conn.close()
        os.remove(temp_db)
        
        print(f"✅ Extracted {len(cookies)} Facebook cookies from Chrome")
        return cookies
        
    except Exception as e:
        print(f"❌ Error reading cookies: {e}")
        if os.path.exists(temp_db):
            os.remove(temp_db)
        return None

def import_to_persistent_profile(cookies):
    """Import cookies to Playwright persistent profile."""
    profile_dir = "database/browser_profile"
    
    if not os.path.exists(profile_dir):
        print(f"❌ Persistent profile not found at: {profile_dir}")
        return False
    
    # Playwright persistent profiles store cookies in Default/Cookies
    # We need to inject via a JSON file that Playwright can read
    cookies_file = os.path.join(profile_dir, "cookies.json")
    
    try:
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"✅ Saved cookies to persistent profile")
        print(f"   Location: {cookies_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving cookies: {e}")
        return False

def main():
    print("="*60)
    print("Chrome → Persistent Profile Cookie Transfer")
    print("="*60)
    
    print("\n⚠️  IMPORTANT: Close Chrome completely before continuing!")
    input("Press ENTER when Chrome is closed...")
    
    print("\n1️⃣  Extracting Facebook cookies from Chrome...")
    cookies = extract_facebook_cookies()
    
    if not cookies:
        print("\n❌ Failed to extract cookies")
        return
    
    print("\n2️⃣  Importing cookies to persistent browser profile...")
    success = import_to_persistent_profile(cookies)
    
    if success:
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print("\nYour verified Facebook session is now in the scraper.")
        print("Next scrape will use YOUR cookies and should see all listings!")
        print("\n💡 You can now restart main.py and trigger a Facebook scrape.")
    else:
        print("\n❌ Failed to import cookies")

if __name__ == "__main__":
    main()
