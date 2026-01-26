"""
Facebook Login Helper
Opens a visible browser window for the user to log in to Facebook manually.
Saves the session cookies for future headless runs.
"""
from playwright.sync_api import sync_playwright
import json
import os
import time

SESSION_FILE = 'database/session.json'

def login_session():
    print("="*60)
    print("🔑 FACEBOOK LOGIN HELPER")
    print("="*60)
    print("Launching visible browser...")
    
    print("Launching visible browser...")
    
    with sync_playwright() as p:
        # Launch visible browser with stealth args
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='en-US'
        )
        page = context.new_page()
        
        # Load existing cookies if any
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    cookies = data.get('cookies', [])
                    if cookies:
                        context.add_cookies(cookies)
                        print("✓ Loaded existing cookies")
            except Exception as e:
                print(f"Warning: Could not load cookies: {e}")
        
        print("\n🌐 Navigating to Facebook.com...")
        try:
            page.goto("https://www.facebook.com", timeout=60000, wait_until='domcontentloaded')
        except Exception as e:
            print(f"Navigation error (retrying): {e}")
            time.sleep(2)
            try:
                page.goto("https://www.facebook.com", timeout=60000)
            except:
                print("Critical navigation error. Capturing screenshot if possible.")
                
        print("\n👇 AUTOMATING LOGIN 👇")
        # Credentials
        USER = "5138182887"
        PASS = "wDmY9s+'j,m.Mc*"
        
        # Check for cookie/consent banner first (Europe/California sometimes)
        try:
            page.click('button[data-cookiebanner="accept_only_essential_button"]', timeout=3000)
        except:
            pass
            
        print("Waiting for page to settle...")
        time.sleep(5)
        
        print("Filling credentials...")
        try:
            # Wait for email field specifically
            page.wait_for_selector('input[name="email"]', state='visible', timeout=10000)
            page.fill('input[name="email"]', USER)
            page.fill('input[name="pass"]', PASS)
        except Exception as e:
            print(f"Error filling credentials: {e}")
            # Fallback to pure keyboard if selectors fail (unlikely but safe)
            # page.keyboard.type(USER) ...
            
        print("Clicking login...")
        # Try different selectors for login button just in case
        try:
            page.click('button[name="login"]')
        except:
            page.keyboard.press('Enter')
            
        print("Waiting for navigation...")
        try:
            # Wait for either home page element OR a login failure
            # x1lliihq is a common class on the feed, or checking for specific aria-labels
            page.wait_for_selector('div[role="feed"]', timeout=15000)
            print("✅ Login successful (Feed detected)")
        except:
            print("⚠️  Feed not detected immediately. Checking url...")
            if "checkpoint" in page.url:
                print("❌ SECURITY CHECKPOINT DETECTED. Manual intervention might still be required.")
            elif "login" in page.url:
                print("❌ Login might have failed (Still on login url).")
            else:
                print("✅ Assuming success based on URL change.")
                
        # Give it a moment to settle
        time.sleep(5)
        
        # Save cookies via AccountManager
        print("\n💾 Saving session...")
        cookies = context.cookies()
        
        from modules.account_manager import AccountManager
        manager = AccountManager()
        if manager.save_new_session(cookies):
            print("Session saved and activated.")
        else:
            print("Failed to save session (No UID found).")
            
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    login_session()
