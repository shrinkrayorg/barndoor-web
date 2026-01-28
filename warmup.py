import os
import time
import random
import json
from dotenv import load_dotenv
from pathlib import Path
from modules.ghost import Ghost

# Load environment variables
load_dotenv()

def load_config():
    """Load settings.json and combine with env vars."""
    config = {}
    
    # 1. Load Settings (Network/Proxy)
    settings_path = Path('database/settings.json')
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            config = json.load(f)
    
    # 2. Add Credentials from Env
    config['facebook_email'] = os.getenv('FACEBOOK_EMAIL')
    config['facebook_password'] = os.getenv('FACEBOOK_PASSWORD')
    
    return config

def facebook_login(page, email, password):
    print("🔑 Attempting Login...")
    try:
        page.goto("https://www.facebook.com/")
        page.wait_for_timeout(3000)
        
        print(f"   Current URL: {page.url}")
        print(f"   Page Title: {page.title()}")
        
        # Check for Cookie Consent (Allow All)
        try:
             # Common selector for "Allow all cookies"
             cookie_btn = page.query_selector('button[data-testid="cookie-policy-manage-dialog-accept-button"], button[title="Allow all cookies"], text="Allow all cookies"')
             if cookie_btn:
                 print("   🍪 Clicking Cookie Consent...")
                 cookie_btn.click()
                 page.wait_for_timeout(1000)
        except:
             pass

        # Check if already logged in (cookies)
        if page.query_selector('div[role="feed"]'):
            print("✅ Already logged in!")
            return True
            
        # Fill Login
        print("   Entering credentials...")
        # Try multiple selectors for email
        email_sel = 'input[name="email"]'
        if not page.query_selector(email_sel):
             email_sel = 'input[type="email"]'
        
        page.fill(email_sel, email)
        page.wait_for_timeout(random.randint(500, 1500))
        
        page.fill('input[name="pass"]', password)
        page.wait_for_timeout(random.randint(500, 1500))
        
        # Click Login
        login_btn = page.query_selector('button[name="login"]')
        if login_btn:
            login_btn.click()
        else:
            page.keyboard.press('Enter')
            
        print("   Waiting for navigation...")
        try:
            page.wait_for_load_state('networkidle', timeout=30000)
        except:
            print("   ⚠️ Navigation wait timed out (might be okay if page loaded)")
        
        page.wait_for_timeout(5000)
        
        # Check for 2FA or Checkpoints
        if "checkpoint" in page.url:
            print("⚠️ FACEBOOK CHALLENGE/CHECKPOINT DETECTED ⚠️")
            return False
            
        print("✅ Login Successful!")
        return True
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        try:
             page.screenshot(path="debug_login_fail.png")
             print("   📸 Saved debug screenshot to debug_login_fail.png")
        except:
             pass
        return False

def run_warmup():
    print("🔥 Starting Account Warmup Routine...")
    config = load_config()
    
    if not config.get('facebook_email'):
        print("❌ Missing FACEBOOK_EMAIL in .env")
        return
        
    # Init Ghost (with Proxy)
    ghost = Ghost(config=config)
    
    try:
        # Launch Browser
        context = ghost.init_browser_context()
        page = context.new_page()
        
        # 1. Login
        if facebook_login(page, config['facebook_email'], config['facebook_password']):
            
            # 2. Save Session (Cookies)
            cookies = context.cookies()
            ghost.save_cookies(cookies)
            
            # 3. Perform Warmup Actions
            print("\n🤖 Initiating Social Interactions...")
            actions_count = random.randint(3, 5)
            
            # Initialize Socializer
            socializer = ghost.get_socializer(page)
            if not socializer:
                # Fallback if get_socializer not fully implemented or accessible
                from modules.ghost import Socializer
                socializer = Socializer(page, config['facebook_email'], config['facebook_password'])

            for i in range(actions_count):
                print(f"   Action {i+1}/{actions_count}:")
                
                # Scroll first
                scroll_amount = random.randint(300, 1000)
                print(f"   📜 Scrolling {scroll_amount}px...")
                page.mouse.wheel(0, scroll_amount)
                ghost.wait(2.0) # Uses smart wait with visual cursor
                
                # Do Random Action
                success = socializer.run()
                
                # Cool down between actions
                sleep_time = random.uniform(5, 12)
                print(f"   💤 Sleeping {int(sleep_time)}s...")
                ghost.wait(sleep_time)
                
            print("\n✅ Warmup Routine Complete!")
            
        else:
            print("\n❌ Warmup Aborted due to Login Failure.")
            
    except Exception as e:
        print(f"❌ Script Error: {e}")
    finally:
        print("🔌 Closing session...")
        ghost.close()

if __name__ == "__main__":
    run_warmup()
