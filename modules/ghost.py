"""
Ghost module for browser session management.
Handles stealth browsing with user agent rotation and cookie persistence.
Includes social automation tools for human-like behavior simulation.
"""
import json
import os
import random
from playwright.sync_api import sync_playwright, Page
from fake_useragent import UserAgent


class Socializer:
    """
    Socializer class for simulating human-like Facebook activity.
    Randomly likes posts, watches stories, and browses groups.
    """
    
    def __init__(self, page: Page, fb_email=None, fb_password=None):
        """
        Initialize the Socializer.
        
        Args:
            page: Playwright page object
            fb_email: Facebook email
            fb_password: Facebook password
        """
        self.page = page
        self.fb_email = fb_email
        self.fb_password = fb_password
    
    def like_random_post(self):
        """Like a random post on the current Facebook page."""
        try:
            posts = self.page.query_selector_all('div[data-testid="post_message"]')
            if posts:
                post = random.choice(posts)
                like_button = post.query_selector('div[aria-label="Like"]')
                if like_button:
                    like_button.click()
                    print("👍 Liked a random post")
                    return True
        except Exception as e:
            print(f"Error liking post: {e}")
        return False
    
    def watch_random_story(self):
        """Watch a random story on Facebook."""
        try:
            stories = self.page.query_selector_all('a[aria-label="Story"]')
            if stories:
                story = random.choice(stories)
                story.click()
                self.page.wait_for_timeout(5000)  # watch for 5 seconds
                print("👀 Watched a random story")
                return True
        except Exception as e:
            print(f"Error watching story: {e}")
        return False
    
    def browse_random_group(self):
        """Browse a random Facebook group."""
        try:
            groups = self.page.query_selector_all('a[aria-label="Group"]')
            if groups:
                group = random.choice(groups)
                group.click()
                self.page.wait_for_timeout(10000)  # browse for 10 seconds
                print("🔍 Browsed a random group")
                return True
        except Exception as e:
            print(f"Error browsing group: {e}")
        return False
    
    def run(self):
        """
        Execute a random social action to simulate human behavior.
        
        Returns:
            bool: True if action was successful
        """
        actions = [self.like_random_post, self.watch_random_story, self.browse_random_group]
        action = random.choice(actions)
        return action()


class AccountCreator:
    """
    AccountCreator class for automating Facebook account creation.
    Handles signup process and phone verification.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the AccountCreator.
        
        Args:
            page: Playwright page object
        """
        self.page = page
    
    def create_account(self, first_name, last_name, email, password, phone_number):
        """
        Create a new Facebook account.
        
        Args:
            first_name: First name for the account
            last_name: Last name for the account
            email: Email address
            password: Password
            phone_number: Phone number for verification
            
        Returns:
            bool: True if account creation initiated successfully
        """
        try:
            self.page.goto('https://www.facebook.com/r.php')
            self.page.wait_for_timeout(2000)
            
            self.page.fill('input[name="firstname"]', first_name)
            self.page.fill('input[name="lastname"]', last_name)
            self.page.fill('input[name="reg_email__"]', email)
            self.page.fill('input[name="reg_passwd__"]', password)
            self.page.fill('input[name="reg_phone__"]', phone_number)
            
            self.page.click('button[name="websubmit"]')
            print(f"✅ Account creation initiated for {first_name} {last_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating account: {e}")
            return False
    
    def verify_phone_number(self, verification_code):
        """
        Verify phone number with SMS code.
        
        Args:
            verification_code: SMS verification code
            
        Returns:
            bool: True if verification successful
        """
        try:
            self.page.fill('input[name="code"]', verification_code)
            self.page.click('button[name="confirm"]')
            print(f"✅ Phone number verified")
            return True
            
        except Exception as e:
            print(f"❌ Error verifying phone: {e}")
            return False


import threading

class Ghost:
    """
    Ghost class responsible for managing browser sessions with stealth features.
    Implements user agent rotation and cookie persistence for maintaining logged-in states.
    Includes social automation tools (Socializer, AccountCreator).
    """
    
    def __init__(self, config=None):
        """
        Initialize the Ghost browser with stealth features and persistent profile.
        
        Args:
            config: Optional configuration dictionary with proxy settings
        """
        self.config = config or {}
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.session_dir = "database/session"
        self.profile_dir = "database/browser_profile"  # Persistent browser profile
        
        # Create profile directory if it doesn't exist
        os.makedirs(self.profile_dir, exist_ok=True)
        
        # Initialize social automation helper
        self.socializer = None
        self.account_creator = None
        self.session_file = 'database/session.json'
        
        # --- PROFILE MANAGER ---
        # Load credentials from active profile if available
        self.fb_email = self.config.get('facebook_email')
        self.fb_password = self.config.get('facebook_password')
        
        try:
            profile_path = 'database/profiles.json'
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    pdata = json.load(f)
                    active_id = pdata.get('active_profile_id')
                    if active_id:
                        active_profile = next((p for p in pdata.get('profiles', []) if p['id'] == active_id), None)
                        if active_profile:
                            print(f"   👤 Ghost using Profile: {active_profile['username']}")
                            self.fb_email = active_profile['username']
                            self.fb_password = active_profile['password']
                            # Update config ref as well
                            self.config['facebook_email'] = self.fb_email
                            self.config['facebook_password'] = self.fb_password
        except Exception as e:
            print(f"   ⚠️ Profile Load Error: {e}")

        # Spectator Mode
        self.broadcast_file = "static/live_view.jpg"

    def capture_live_frame(self):
        """
        Take a single screenshot for the spectator feed.
        Must be called from the MAIN THREAD to avoid greenlet errors.
        """
        try:
            if self.context and self.context.pages:
                page = self.context.pages[-1]
                if page and not page.is_closed():
                    # Save to static file
                    page.screenshot(path=self.broadcast_file, type='jpeg', quality=50)
        except Exception:
            pass
            
    def wait(self, seconds: float):
        """
        Smart replacement for time.sleep().
        Breaks the sleep into 0.1s chunks and captures a frame each time.
        Creates a 'live video' effect during idle times.
        """
        import time
        steps = int(seconds / 0.1)
        for _ in range(steps):
             self.capture_live_frame()
             time.sleep(0.1)
             
    def scroll(self, page: Page, pixels: int):
        """
        Smooth scroll with continuous frame capture.
        """
        import time
        # Scroll in small chunks
        chunk_size = 100
        steps = int(pixels / chunk_size)
        
        for _ in range(steps):
            page.mouse.wheel(0, chunk_size)
            self.capture_live_frame()
            time.sleep(0.1) # smooth speed
    
    def get_random_user_agent(self):
        """
        Return a stable DESKTOP Chrome user agent.
        Marketplace frequently fails to hydrate on some mobile/random UAs.
        """
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    
    def load_cookies(self):
        """
        Load cookies from session file.
        
        Returns:
            list: List of cookie dictionaries, or empty list if file doesn't exist
        """
        # This method is likely deprecated with the new persistent context approach
        # but kept for compatibility if other parts of the code still call it.
        if os.path.exists(self.session_file): # Assuming default path if session_file is removed
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    return data.get('cookies', [])
            except Exception as e:
                print(f"Error loading cookies: {e}")
        return []
    
    def save_cookies(self, cookies):
        """
        Save cookies to session file.
        
        Args:
            cookies: List of cookie dictionaries to save
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            
            with open(self.session_file, 'w') as f:
                json.dump({'cookies': cookies}, f, indent=2)
            print(f"Saved {len(cookies)} cookies to {self.session_file}")
        except Exception as e:
            print(f"Error saving cookies: {e}")
    
    def init_browser_context(self):
        """
        Initialize a new browser context with stealth settings.
        
        Returns:
            BrowserContext: Playwright browser context
        """
        # Start Playwright
        self.playwright = sync_playwright().start()
        
        # Prepare Launch Args
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
        
        # Check for Proxy Config
        proxy = None
        if self.config:
            net_conf = self.config.get('network', {})
            if net_conf.get('mode') == 'proxy' and net_conf.get('proxy_host'):
                host = net_conf.get('proxy_host')
                port = net_conf.get('proxy_port')
                user = net_conf.get('proxy_user')
                pwd = net_conf.get('proxy_pass')
                
                server = f"http://{host}:{port}"
                proxy = {
                    "server": server
                }
                
                if user and pwd:
                    proxy["username"] = user
                    proxy["password"] = pwd
                    
                print(f"🔒 Ghost configured to use proxy: {host}:{port}")
        
        # Use persistent context instead of ephemeral browser
        # This maintains cookies and session across runs automatically
        user_agent = self.get_random_user_agent()
        
        print(f"🎭 Using persistent browser profile: {self.profile_dir}")
        self.context = self.playwright.chromium.launch_persistent_context(
            self.profile_dir,
            headless=True,
            proxy=proxy,
            args=launch_args,
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            ignore_https_errors=True
        )
        
        # Load cookies from Chrome extraction if available
        cookies_file = os.path.join(self.profile_dir, "cookies.json")
        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                print(f"✅ Loaded {len(cookies)} cookies from Chrome import")
            except Exception as e:
                print(f"⚠️  Warning loading Chrome cookies: {e}")
        
        print("✅ Persistent profile loaded (cookies managed automatically)")
        
        # INJECT STEALTH SCRIPTS (Enhanced Anti-Fingerprinting)
        # Comprehensive evasion for Facebook's advanced detection
        stealth_js = """
            // 1. Pass the Webdriver Test
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // 2. Mock Plugins (Chrome usually has these)
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 3. Mock Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // 4. Overwrite permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // 5. Add Chrome Runtime (missing in headless)
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 6. Mock WebGL Vendor/Renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };
            
            // 7. Canvas Fingerprint Protection
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width === 0 && this.height === 0) {
                    return originalToDataURL.apply(this, arguments);
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            // 8. Navigator Properties
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            Object.defineProperty(navigator, 'platform', {
                get: () => 'MacIntel'
            });
            
            // 9. Battery API (if present, mock it)
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }
            
            // 10. Screen properties
            Object.defineProperty(screen, 'availWidth', {get: () => 1920});
            Object.defineProperty(screen, 'availHeight', {get: () => 1080});
        """
        self.context.add_init_script(stealth_js)

        # INJECT VISUAL CURSOR (User Request - CRITICAL)
        cursor_js = """
            // Visual Cursor Injection for Spectator Mode
            document.addEventListener("DOMContentLoaded", () => {
                const cursor = document.createElement("div");
                cursor.id = "virtual-cursor";
                cursor.style.position = "absolute";
                cursor.style.width = "20px";
                cursor.style.height = "20px";
                cursor.style.background = "rgba(255, 0, 0, 0.7)";
                cursor.style.borderRadius = "50%";
                cursor.style.pointerEvents = "none";
                cursor.style.zIndex = "999999";
                cursor.style.transform = "translate(-50%, -50%)";
                cursor.style.transition = "transform 0.1s, background 0.1s";
                cursor.style.boxShadow = "0 0 8px rgba(255,0,0,0.6)";
                
                // Center dot
                const dot = document.createElement("div");
                dot.style.width = "4px";
                dot.style.height = "4px";
                dot.style.background = "white";
                dot.style.borderRadius = "50%";
                dot.style.position = "absolute";
                dot.style.top = "50%";
                dot.style.left = "50%";
                dot.style.transform = "translate(-50%, -50%)";
                cursor.appendChild(dot);
                
                document.body.appendChild(cursor);
                
                document.addEventListener("mousemove", (e) => {
                    cursor.style.left = e.pageX + "px";
                    cursor.style.top = e.pageY + "px";
                });
                
                document.addEventListener("mousedown", () => {
                    cursor.style.transform = "translate(-50%, -50%) scale(0.8)";
                    cursor.style.background = "rgba(255, 0, 0, 1.0)";
                });
                
                document.addEventListener("mouseup", () => {
                    cursor.style.transform = "translate(-50%, -50%) scale(1.0)";
                    cursor.style.background = "rgba(255, 0, 0, 0.7)";
                });
            });
        """
        self.context.add_init_script(cursor_js)
        
        
        # Create initial page from persistent context
        # Persistent context auto-creates a default page - we need to assign it
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
        
        print(f"Browser context initialized with user agent: {user_agent[:80]}...")
        return self.context
    
    def get_browser_context(self):
        """
        Get the current browser context, creating one if it doesn't exist.
        
        Returns:
            BrowserContext: Playwright browser context
        """
        if not self.context:
            return self.init_browser_context()
        return self.context
    
    def get_socializer(self, page: Page = None):
        """
        Get a Socializer instance for the given page.
        
        Args:
            page: Playwright page object (creates new page if None)
            
        Returns:
            Socializer: Socializer instance
        """
        if not self.context:
            self.init_browser_context()
        
        if page is None:
            page = self.context.new_page()
        
        return Socializer(page)
    
    def social_detour(self, page: Page):
        """
        Perform a random social detour (watch video, browse feed, check notifications).
        Used during scraping loops to break patterns.
        """
        # Increased probability of doing something recognizable
        action = random.choice(['natgeo', 'martial_arts', 'cooking', 'feed', 'notifications'])
        print(f"   🎭 Ghost is taking a detour: {action}")
        
        try:
            if action == 'natgeo':
                # Visit National Geographic video page
                page.goto('https://www.facebook.com/natgeo/videos')
                self.wait(random.uniform(10.0, 20.0)) # Watch for 10-20s
                # Use Visual Cursor to show attention
                page.mouse.move(500, 500) 
                
            elif action == 'martial_arts':
                # General search for video content
                page.goto('https://www.facebook.com/watch/search/?q=martial%20arts')
                self.wait(random.uniform(8.0, 15.0))
                
            elif action == 'cooking':
                 page.goto('https://www.facebook.com/watch/search/?q=cooking%20recipes')
                 self.wait(random.uniform(8.0, 15.0))
                
            elif action == 'feed':
                page.goto('https://www.facebook.com/')
                self.wait(random.uniform(3.0, 8.0))
                self.scroll(page, random.randint(300, 1000))
                
            elif action == 'notifications':
                page.goto('https://www.facebook.com/notifications')
                self.wait(random.uniform(2.0, 5.0))
        except Exception:
            pass # Detour failures shouldn't crash the bot
            
        # Return - User handles navigation back or next open
        self.wait(random.uniform(1.0, 2.0))
    
    def get_account_creator(self, page: Page = None):
        """
        Get an AccountCreator instance for the given page.
        
        Args:
            page: Playwright page object (creates new page if None)
            
        Returns:
            AccountCreator: AccountCreator instance
        """
        if not self.context:
            self.init_browser_context()
        
        if page is None:
            page = self.context.new_page()
        
        return AccountCreator(page)
    
    def run_random_social_activity(self):
        """
        Run random social activity to simulate human behavior.
        This can be called at random intervals throughout the day.
        
        Returns:
            bool: True if activity was successful
        """
        try:
            page = self.context.new_page()
            page.goto('https://www.facebook.com')
            page.wait_for_timeout(2000)
            
            socializer = Socializer(page)
            result = socializer.run()
            
            page.close()
            return result
            
        except Exception as e:
            print(f"Error running social activity: {e}")
            return False
    
    def update_session(self):
        """
        Update saved session with current cookies from browser context.
        """
        if self.context:
            cookies = self.context.cookies()
            self.save_cookies(cookies)
    
    def close(self):
        """Close the browser instance and save cookies."""
        if self.context:
            # Persistent context automatically saves cookies on close
            self.context.close()
            print("✅ Persistent browser profile closed (session saved)")
        if self.playwright:
            self.playwright.stop()
        
        print("Ghost session closed")
    
    def take_long_break(self, duration_minutes: int):
        """
        Execute a long social session to simulate a human 'break'.
        Instead of browsing marketplace, the bot consumes content for X minutes.
        """
        import time
        print(f"\n☕ [GHOST] Starting {duration_minutes}-minute Human Social Break...")
        
        end_time = time.time() + (duration_minutes * 60)
        
        if not self.context:
            self.init_browser_context()
            
        page = self.context.new_page()
        
        try:
            while time.time() < end_time:
                remaining = int((end_time - time.time()) / 60)
                print(f"   [GHOST] ~{remaining} mins remaining in break. Switching activity...")
                
                # Random Activity
                activities = ['natgeo', 'martial_arts', 'cooking', 'dancing', 'feed', 'add_friends']
                activity = random.choice(activities)
                
                print(f"   🎭 Activity: {activity}")
                
                try:
                    if activity == 'natgeo':
                        page.goto('https://www.facebook.com/natgeo/videos', wait_until='domcontentloaded')
                        self.wait(random.uniform(45.0, 90.0)) # Watch for 1-2 mins
                        
                        # Maybe like?
                        if random.random() < 0.3:
                            self.socializer.like_random_post()
                            
                    elif activity == 'martial_arts':
                        page.goto('https://www.facebook.com/watch/search/?q=martial%20arts', wait_until='domcontentloaded')
                        self.wait(random.uniform(30.0, 60.0))
                        # Click a video?
                        try:
                            vids = page.locator('a[href*="/watch/"]').all()
                            if vids:
                                random.choice(vids[:3]).click()
                                self.wait(random.uniform(60.0, 120.0)) # Watch specific video
                        except: pass
                        
                    elif activity == 'cooking':
                         page.goto('https://www.facebook.com/watch/search/?q=cooking', wait_until='domcontentloaded')
                         self.wait(random.uniform(30.0, 60.0))
                        
                    elif activity == 'dancing':
                         page.goto('https://www.facebook.com/watch/search/?q=dancing', wait_until='domcontentloaded')
                         self.wait(random.uniform(30.0, 60.0))
                         
                    elif activity == 'feed':
                        page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
                        # Scroll and read
                        for _ in range(random.randint(5, 10)):
                            self.scroll(page, random.randint(300, 800))
                            self.wait(random.uniform(5.0, 10.0))
                            
                    elif activity == 'add_friends':
                        # Go to 'People You May Know' or similar
                        page.goto('https://www.facebook.com/friends', wait_until='domcontentloaded')
                        self.wait(random.uniform(5.0, 10.0))
                        try:
                            # Look for "Add Friend" buttons
                            add_btns = page.locator('span:text-is("Add Friend")').all()
                            if add_btns:
                                target = random.choice(add_btns[:3]) # specific logic to avoid spam
                                target.click() # Uncommented for production behavior
                                print("   👥 Added a friend")
                                self.wait(random.uniform(2.0, 5.0))
                        except: pass
                        
                except Exception as e:
                    print(f"   ⚠️ Activity error: {e}")
                
                # Wait between activities
                self.wait(random.uniform(10.0, 30.0))
                
        except Exception as e:
            print(f"Break interrupted: {e}")
        finally:
            page.close()
            print("☕ Break over. Back to work.")

    def execute(self):
        """
        Execute the ghost's main session management process.
        This is called to initialize a browsing session.
        
        Returns:
            BrowserContext: Initialized browser context
        """
        # Initialize valid socializer reference
        if not self.context:
             self.init_browser_context()
        self.socializer = self.get_socializer(self.context.pages[0] if self.context.pages else None)
        
        return self.context
