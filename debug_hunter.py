from modules.ghost import Ghost
from playwright.sync_api import sync_playwright
import time

def debug():
    # Load config implies using settings.json
    from database.config_db import ConfigDB
    config = ConfigDB().get_config()
    target_url = config.get('target_urls', '').split(',')[0]
    
    if not target_url:
        print("No target URL found settings.")
        return

    print(f"Debugging URL: {target_url}")
    
    ghost = Ghost()
    # We use ghost to get context (cookies)
    with sync_playwright() as p:
        # Launch HEADERLESS=TRUE first to catch if it's an anti-bot redirect that only happens in headless
        # Actually user ran visible browser and it failed? User's log says "Launching visible browser..."? 
        # No, main.py uses hunter.execute which uses ghost.get_browser_context().
        # ghost.init_browser_context defaults to HEADLESS=TRUE.
        # But wait, earlier I saw "Launching visible browser..." in logs? That was my login helper.
        # main.py runs headless by default unless I changed it.
        # Let's try headless first as that's the production mode.
        
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        # Load cookies
        cookies = ghost.load_cookies()
        if cookies:
            context.add_cookies(cookies)
            print(f"Loaded {len(cookies)} cookies.")
            
        page = context.new_page()
        
        print("Navigating...")
        try:
            page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
            print("Navigation complete.")
        except Exception as e:
            print(f"Navigation error: {e}")
            
        time.sleep(5)
        
        print(f"Final URL: {page.url}")
        print(f"Page Title: {page.title()}")
        
        # Check selectors
        sel = 'div[data-testid="marketplace-feed-item"]'
        count = page.locator(sel).count()
        print(f"Selector '{sel}' count: {count}")
        
        # Screenshot
        page.screenshot(path="debug_fb.png")
        print("Screenshot saved to debug_fb.png")
        
        browser.close()

if __name__ == "__main__":
    debug()
