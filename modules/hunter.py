"""
Hunter module for data collection and retrieval.
Uses Playwright with site-specific scraping strategies.
Implements the Strategy Pattern for modular, extensible scraping.
"""
from playwright.sync_api import sync_playwright, Page, Locator
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import re
import time
import random
import os
# Import Navigator
from modules.navigator import Navigator, NavReason

# Common User Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

class ScrapeStrategy(ABC):
    """
    Abstract base class for site-specific scraping strategies.
    Now utilizes Navigator if available, or falls back to direct actions.
    """
    def __init__(self, navigator: Navigator = None):
        self.navigator = navigator

    def navigate(self, page: Page, url: str, reason: NavReason) -> bool:
        """Centralized navigation request."""
        if self.navigator:
            return self.navigator.navigate_to(page, url, reason)
        else:
            # Fallback if no navigator provided
            try:
                page.goto(url)
                return True
            except:
                return False

    def random_sleep(self, min_seconds=2.0, max_seconds=5.0):
        """Sleep for a random amount of time to simulate human delay."""
        # Use a slight gaussian distribution for natural variance
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def simulate_human_interaction(self, page: Page):
        """
        Perform random actions to appear human:
        - Random mouse movements
        - Scrolling up and down
        - Hovering over elements
        """
        print("   🤖 Simulating human behavior...")
        
        # 1. Random Mouse Move
        # Move across screen
        page.mouse.move(random.randint(100, 500), random.randint(100, 500), steps=random.randint(5, 10))
        self.random_sleep(0.5, 1.5)
        
        # 2. Variable Scrolling (Reading behavior)
        # Scroll down randomly
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 700)
            page.mouse.wheel(0, scroll_amount)
            self.random_sleep(0.8, 2.0)
            
            # Occasionally scroll back up slightly (re-reading)
            if random.random() > 0.7:
                page.mouse.wheel(0, -random.randint(50, 200))
                self.random_sleep(0.5, 1.0)
        
        # 3. Random Hover (Interact with page elements)
        try:
            # Find interactive elements (links, headings)
            elements = page.query_selector_all('a, h2, h3, div')
            if elements:
                # Pick a random sample to hover
                target = random.choice(elements[:10]) # Limit to top few to avoid waiting
                box = target.bounding_box()
                if box:
                    # Move to element with natural curve (simulated by steps)
                    page.mouse.move(
                        box['x'] + box['width']/2, 
                        box['y'] + box['height']/2, 
                        steps=random.randint(10, 20)
                    )
        except Exception:
            pass # Ignore movement errors
            
        self.random_sleep(1.0, 3.0)

    @abstractmethod
    def scrape(self, page: Page, url: str) -> list:
        """
        Scrape listings from a page.
        
        Args:
            page: Playwright page object
            url: Target URL to scrape
            
        Returns:
            list: List of listing dictionaries
        """
        pass
    
    def extract_price(self, price_text: str) -> int:
        """Helper method to extract price from text."""
        if not price_text:
            return 0
        # Remove all non-digit characters and convert to int
        digits = re.sub(r'[^\d]', '', price_text)
        return int(digits) if digits else 0
    
    def extract_mileage(self, mileage_text: str) -> int:
        """Helper method to extract mileage from text."""
        if not mileage_text:
            return 0
            
        # Prioritize exact numbers like "123,456"
        exact_match = re.search(r'\b(\d{1,3}(?:,\d{3})+)\b', mileage_text)
        if exact_match:
             return int(exact_match.group(1).replace(',', ''))
             
        # Fallback to K notation
        # Remove all non-digit characters and convert to int
        digits = re.sub(r'[^\d]', '', mileage_text)
        return int(digits) if digits else 0

        digits = re.sub(r'[^\d]', '', mileage_text)
        return int(digits) if digits else 0



class FacebookStrategy(ScrapeStrategy):
    """
    Scraping strategy for Facebook Marketplace.
    Handles login requirements and FB-specific selectors.
    """
    
    def __init__(self, ghost=None, navigator=None):
        """
        Initialize Facebook strategy.
        
        Args:
            ghost: Ghost instance for session management and login
            navigator: Navigator instance for stealth navigation
        """
        super().__init__(navigator)
        self.ghost = ghost
    
    def login_if_needed(self, page: Page):
        """
        Check if login is required and handle it via Ghost.
        
        Args:
            page: Playwright page object
        """
        try:
            # Check if we're on a login page
            if 'login' in page.url.lower() or page.query_selector('input[name="email"]'):
                print("⚠️  Facebook login required")
                print("💡 Please ensure Ghost has valid Facebook session cookies")
                # Wait a bit for potential auto-login from cookies
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Warning during login check: {e}")
    
    
    def auto_configure(self, criteria: dict) -> str:
        """
        Automatically configure search by navigating to Marketplace and applying filters.
        Returns the resulting URL.
        """
        print("   🛠️ Auto-Configuring Search Parameters...")
        if not self.ghost:
            print("   ❌ Ghost instance required for auto-configuration.")
            return None
            
        page = self.ghost.page
        try:
            # 1. Go to Marketplace
            # page.goto("https://www.facebook.com/marketplace/vehicles", wait_until='domcontentloaded')
            self.navigate(page, "https://www.facebook.com/marketplace/vehicles", NavReason.INITIAL_LOAD)
            self.ghost.wait(random.uniform(3.0, 5.0))
            
            # 2. Set Location (Simplistic approach: assuming user is logged in or default works, 
            # otherwise just returning the base vehicle URL with query parameters manually constructed 
            # is safer/faster than UI interaction which might flake).
            
            # Construct URL manually based on criteria to avoid UI flakiness
            # Zip and Radius are usually stored in cookies, but we can try to pass them if we reverse engineer the URL.
            # However, `https://www.facebook.com/marketplace/{city_slug}/vehicles` is standard.
            # Finding the slug from zip is hard without an API.
            
            # Better approach: Use the UI to search "Vehicles" which is resilient.
            
            # For now, let's return a robust search URL based on the zip if possible, 
            # or default to the Chicago one if unknown, but better: 
            # Let's try to interact with the location filter if visible.
            
            print("   📍 Attempting to set location via URL parameters (Best Effort)...")
            # FB doesn't easily accept zip in URL for marketplace without internal ID.
            # Fallback: Return a generic search URL that the user can refine, or use the one they likely want.
            # If criteria has 'zip_code', we might need to geocode it to a city slug? 
            # Too complex for this step.
            
            # Alternative: Just search for "Vehicles"
            query = "Vehicles"
            page.fill('input[aria-label="Search Marketplace"]', query)
            page.keyboard.press('Enter')
            self.ghost.wait(3.0)
            
            current_url = page.url
            print(f"   ✅ Auto-Configuration Complete. URL: {current_url}")
            return current_url
            
        except Exception as e:
            print(f"   ❌ Auto-Configuration Failed: {e}")
            return "https://www.facebook.com/marketplace/category/vehicles"

    def scrape(self, page: Page, url: str) -> list:
        """
        Scrape Facebook Marketplace listings using Deep Loop Strategy.
        Simulates human behavior by visiting individual item pages.
        """
        listings = []
        
        try:
            # Navigate to Feed
            print(f"   Getting {url}...")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Use Ghost Wait for live feed
            if self.ghost:
                self.ghost.wait(random.uniform(3.0, 5.0))
            else:
                self.random_sleep(3.0, 5.0)
            
            # Check if content loaded, otherwise proceed
            try:
                page.wait_for_selector('a[href*="/marketplace/item/"]', timeout=5000)
            except Exception:
                print("   ⚠️ Content wait timed out, proceeding anyway...")
            
            # Initial human behavior before doing work
            self.simulate_human_interaction(page)
            self.login_if_needed(page)
            
            # Collect Links (Scroll a bit to get a good batch)
            print("   🔍 Scanning feed for potential vehicles...")
            unique_links = []
            seen_urls = set()
            
            for _ in range(3): # Scroll a few times
                # use ghost scroll for live feed
                if self.ghost:
                     self.ghost.scroll(page, random.randint(500, 1000))
                     self.ghost.wait(1.5)
                else:
                     page.mouse.wheel(0, random.randint(500, 1000))
                     self.random_sleep(1.0, 2.0)
                
                # Link discovery
                found_links = page.locator('a[href*="/marketplace/item/"]').all()
                for link in found_links:
                    href = link.get_attribute('href')
                    if href and href not in seen_urls:
                        # Convert to full URL
                        full_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
                        # Simple filter to avoid totally irrelevant links if possible
                        if '/item/' in full_url:
                            # 72-hour Freshness Check (Initial URL Filter if supported)
                            # Facebook URLs don't carry dates trivially without opening, 
                            # checking inside the loop is safer.
                            
                            # --- PRE-CLICK FILTER (Smart Feed Filtering) ---
                            # Extract text from link or parent to check for obvious dealbreakers
                            try:
                                link_text = link.inner_text().lower()
                                
                                # 1. Severe Rust Check
                                rust_keywords = ['severe rust', 'frame rot', 'rusted out', 'frame damage', 'serious rust']
                                if any(rk in link_text for rk in rust_keywords):
                                    print(f"   ⛔ Skipping (Severe Rust): {full_url}")
                                    continue
                                    
                                # 2. Super High Mileage Check (>180k)
                                # Look for "200k miles", "200,000 miles", "200k" context
                                mileage_match = re.search(r'(\d{3})[k]?\s*miles?', link_text)
                                if mileage_match:
                                    miles = int(mileage_match.group(1))
                                    # If it's just "200", assume "200k"
                                    if miles < 1000: miles *= 1000 
                                    
                                    if miles > 180000:
                                        print(f"   ⛔ Skipping (High Mileage {miles}): {full_url}")
                                        continue

                                # 3. Vehicle Type & Dealership Exclusions (Smart Filter)
                                exclude_keywords = [
                                    # Non-Standard Vehicles
                                    'motorcycle', 'scooter', 'bike', 'boat', 'trailer', 'rv', 'camper', 'motorhome', 
                                    'atv', 'snowmobile', 'parting out', 'part out', 'parts only', 'shell', 'chassis',
                                    
                                    # Dealership Keywords (Text Proxy for "Dealership Background")
                                    'down payment', 'financing', 'finance', 'bad credit', 'buy here pay here', 
                                    'auto sales', 'motors', 'dealership', 'car lot', 'monthly', 'warranty',
                                    'llc', 'inc', 'corp', 'group', 'auto group', 'imports', 'exotics'
                                ]
                                
                                # Check link text AND potentially parent text if accessible (simple heuristic for now)
                                if any(ek in link_text for ek in exclude_keywords):
                                    print(f"   ⛔ Skipping (Type/Dealer): {full_url}")
                                    continue
                                        
                            except:
                                pass # formatting varies, proceed if unsure
                            
                            seen_urls.add(full_url)
                            unique_links.append(full_url)
            
            if not unique_links:
                print("   ⚠️ Found 0 links. Taking debug screenshot...")
                page.screenshot(path="debug_failure.png")
                
            print(f"   Found {len(unique_links)} potential listing links. Selecting top 10 for deep inspection.")
            
            # Deep Loop: Visit each item individually
            # Limit to 10 to simulate realistic human browsing session
            targets = unique_links[:10]
            
            
            for i, target_url in enumerate(targets):
                print(f"   [{i+1}/{len(targets)}] Inspecting: {target_url}")
                
                # Check for Social Detour (Reduced to 5% to avoid rapid switching - relying on Long Break)
                if random.random() < 0.05 and self.ghost:
                    print("   human_behavior: Taking a break to socialize...")
                    self.ghost.social_detour(page) 
                    print("   human_behavior: Returning to work.")
                    # CRITICAL: After detour, ensure we return to work properly
                    # logic continues below with goto(target_url) which is fine.
                
                try:
                    # Visit Listing
                    page.goto(target_url, wait_until='domcontentloaded', timeout=45000)
                    
                    # Anti-Drift Check: Did we accidentally land on "Today's Picks" or generic feed?
                    # This happens if a link is broken or redirects.
                    # Since we are supposed to be on an item page here (`target_url`), 
                    # "Today's picks" usually implies we got booted to home.
                    try:
                        if page.get_by_text("Today's picks").count() > 0:
                             print("   ⚠️ Drifted to 'Today's Picks'. Retrying listing...")
                             page.goto(target_url, wait_until='domcontentloaded')
                    except:
                        pass
                    
                    if self.ghost:
                        self.ghost.wait(random.uniform(2.0, 4.0))
                        
                        # Simulate reading with ghost scroll
                        self.ghost.scroll(page, 300)
                        self.ghost.wait(random.uniform(1.0, 2.0))
                    else:
                        self.random_sleep(2.0, 4.0)
                        page.mouse.wheel(0, 300)
                        self.random_sleep(1.0, 2.0)
                    
                    # Extract Details
                    listing_data = self._extract_deep_details(page, target_url)
                    
                    # --- POST-CLICK VALIDATION (Deep Check) ---
                    # Sometimes determining factors are only visible in the full description or seller name
                    if listing_data:
                        full_text = f"{listing_data.get('title', '')} {listing_data.get('description', '')}".lower()
                        
                        # 1. Re-check Dealership Keywords in full text
                        dealer_keywords = ['llc', 'inc', 'auto group', 'financing', 'down payment', 'warranty', 'dealer']
                        if any(k in full_text for k in dealer_keywords):
                             print(f"   ⛔ Rejecting (Dealer Text): {target_url}")
                             continue

                        # 2. Re-check Rust/Damage in full text
                        rust_keywords = ['severe rust', 'frame rot', 'rusted out', 'frame damage']
                        if any(k in full_text for k in rust_keywords):
                             print(f"   ⛔ Rejecting (Severe Rust): {target_url}")
                             continue
                             
                        # 3. Re-check Vehicle Type in full text
                        bad_types = ['part out', 'parts only', 'motorcycle', 'scooter', 'boat', 'camper']
                        if any(k in full_text for k in bad_types):
                             print(f"   ⛔ Rejecting (Wrong Type): {target_url}")
                             continue

                    # 72-Hour Freshness Filter
                    if listing_data and listing_data.get('hours_since_listed') is not None: # Check for None explicitly
                        hours = listing_data.get('hours_since_listed')
                        if hours > 72:
                             print(f"   ⚠️ Stale listing ({hours}h old). Skipping.")
                             continue
                    
                    if listing_data:
                        raw_listings.append(listing_data)
                        print(f"   ✅ Collected: {listing_data.get('title', 'Unknown')}")
                    else:
                         print("   ⚠️ Failed to extract data.")
                         
                    # Cooldown between items
                    self.random_sleep(3.0, 8.0)
                    
                except Exception as e:
                    print(f"   ❌ Error inspecting item: {e}")
                    pass # Changed from continue to pass
            
            print(f"✓ Deep Scan Complete. Extracted {len(raw_listings)} verified listings") # Changed to raw_listings
            return raw_listings # Changed from listings
            
        except Exception as e:
            print(f"Error scraping Facebook Marketplace: {e}")
        
        return raw_listings # Changed from listings

    def _extract_deep_details(self, page: Page, url: str) -> dict:
        """Extract details from a specific listing page."""
        try:
            # Wait briefly for content
            try:
                page.wait_for_selector('h1', timeout=3000)
            except: pass
            
            # Get full text for broad text analysis
            body_text = page.inner_text()
            
            # TITLE
            title = "Unknown Vehicle"
            try:
                title = page.locator('h1').first.inner_text()
            except: pass
            
            # PRICE
            price = 0
            # Try finding price in the top section first
            price_match = re.search(r'\$[\d,]+', body_text)
            if price_match:
                price = self.extract_price(price_match.group(0))
                
            # MILEAGE (CRITICAL FIX FOR USER)
            # Prioritize "Driven X miles" from "About this vehicle" section
            mileage = 0
            driven_match = re.search(r'Driven\s+([\d,]+)\s+miles', body_text, re.IGNORECASE)
            if driven_match:
                mileage = self.extract_mileage(driven_match.group(1))
            else:
                # Fallback: look for "odometer" context
                odo_match = re.search(r'Odometer[:\s]+([\d,]+)', body_text, re.IGNORECASE)
                if odo_match:
                     mileage = self.extract_mileage(odo_match.group(1))

            # DESCRIPTION
            description = body_text # Use full text as fallback description if specific container not found
            # Try to expand description if possible
            try:
                page.get_by_role("button", name="See more").first.click(timeout=1000)
                description = page.inner_text() # Update text after expansion
            except: pass

            # IMAGES
            images = []
            try:
                imgs = page.locator('img').all()
                for img in imgs[:5]: # First few images usually main gallery
                    src = img.get_attribute('src')
                    if src and 'fbcdn' in src:
                        images.append(src)
            except:
                pass
            
            # TIME POSTED (Advanced Parsing)
            # Try to find relative time like "Listed 2 hours ago"
            hours_since_listed = None
            time_posted_match = re.search(r'Listed\s+([\d\.]+)\s+(min|minute|hour|day|week)s?\s+ago', body_text, re.IGNORECASE)
            if time_posted_match:
                val = float(time_posted_match.group(1))
                unit = time_posted_match.group(2).lower()
                if 'min' in unit: hours_since_listed = val / 60.0
                elif 'hour' in unit: hours_since_listed = val
                elif 'day' in unit: hours_since_listed = val * 24.0
                elif 'week' in unit: hours_since_listed = val * 24.0 * 7.0
            
            # Construct Listing
            return {
                'title': title,
                'price': price,
                'mileage': mileage, 
                'location': "Unknown", # Extractor needed or use vetting logic
                'description': description,
                'images': images,
                'listing_url': url,
                'source': 'facebook_marketplace',
                'hours_since_listed': hours_since_listed
            }
        except Exception as e:
            print(f"Deep extract error: {e}")
            return None
    
    def _extract_facebook_listing(self, page: Page, elem) -> dict:
        """Extract data from a single Facebook listing element."""
        # Title
        title_elem = elem.query_selector('span.x1lliihq.x6ikm8r.x10wlt62.x1n2onr6')
        title = title_elem.inner_text().strip() if title_elem else ""
        
        # Price
        price_elem = elem.query_selector('span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.xudqn12.x676frb.x1lkfr7t.x1lbecb7.x1s688f.xzsf02u')
        price_text = price_elem.inner_text() if price_elem else "0"
        price = self.extract_price(price_text)
        
        # Location
        location_elem = elem.query_selector('span.x1lliihq.x6ikm8r.x10wlt62.x1n2onr6.xlyipyv.xuxw1ft')
        location = location_elem.inner_text().strip() if location_elem else ""
        
        # URL
        link_elem = elem.query_selector('a[href*="/marketplace/item/"]')
        if link_elem:
            href = link_elem.get_attribute('href')
            listing_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
        else:
            listing_url = ""
        
        # Images
        img_elems = elem.query_selector_all('img')
        images = [img.get_attribute('src') for img in img_elems if img.get_attribute('src')]
        
        # Description (often not available in feed, would need detail page)
        description = ""
        
        # Mileage (extract from title/description if present)
        mileage = 0
        combined_text = f"{title} {description}"
        mileage_match = re.search(r'(\d+[,\d]*)\s*(?:miles|mi|k\s*miles)', combined_text, re.IGNORECASE)
        if mileage_match:
            mileage = self.extract_mileage(mileage_match.group(1))
        
        return {
            'title': title,
            'price': price,
            'mileage': mileage,
            'location': location,
            'description': description,
            'images': images,
            'listing_url': listing_url,
            'source': 'facebook_marketplace'
        }


class CraigslistStrategy(ScrapeStrategy):
    """
    Scraping strategy for Craigslist.
    Does not require login.
    """
    
    def scrape(self, page: Page, url: str) -> list:
        """
        Scrape Craigslist listings.
        
        Args:
            page: Playwright page object
            url: Craigslist search URL
            
        Returns:
            list: List of listing dictionaries
        """
        listings = []
        
        try:
            # Navigate to URL
            print(f"   Getting {url}...")
            # page.goto(url, wait_until='networkidle', timeout=30000)
            self.navigate(page, url, NavReason.INITIAL_LOAD)
            
            # Simulate human reading/scrolling
            self.simulate_human_interaction(page)
            self.random_sleep(1.5, 3.5)
            
            # Craigslist specific selectors
            # Updated based on debug run: 'li.cl-static-search-result' failed, '.cl-search-result' worked (60 items)
            listing_elements = page.query_selector_all('.cl-search-result')
            
            if not listing_elements:
                print("⚠️  No listings found with Craigslist selectors")
                return listings
            
            print(f"Found {len(listing_elements)} Craigslist listings")
            
            # Extract data from each listing
            for elem in listing_elements:
                try:
                    listing_data = self._extract_craigslist_listing(page, elem)
                    if listing_data and listing_data.get('title'):
                        listings.append(listing_data)
                except Exception as e:
                    print(f"Error extracting Craigslist listing: {e}")
                    continue
            
            print(f"✓ Extracted {len(listings)} Craigslist listings")
            
            # Decoy click?
            if listings and random.random() > 0.8:
                 # Click "next page" or similar if we wanted, but for now just wait
                 self.random_sleep(2.0, 4.0)
            
        except Exception as e:
            print(f"Error scraping Craigslist: {e}")
        
        return listings
    
    def _extract_craigslist_listing(self, page: Page, elem) -> dict:
        """Extract data from a single Craigslist listing element (gallery-card style)."""
        # Title
        title_elem = elem.query_selector('a.posting-title span.label')
        if not title_elem:
             # Fallback
             title_elem = elem.query_selector('a.posting-title')
        title = title_elem.inner_text().strip() if title_elem else ""
        
        # Price
        price_elem = elem.query_selector('span.priceinfo')
        price_text = price_elem.inner_text() if price_elem else "0"
        price = self.extract_price(price_text)
        
        # Location & Meta
        meta_elem = elem.query_selector('div.meta')
        meta_text = meta_elem.inner_text().strip() if meta_elem else ""
        
        # Parse meta for location (often last part after separator)
        # Structure: "1/22 199k mi Village Okla."
        # We can just treat meta_text as general location/desc context
        location = meta_text
        
        # URL
        link_elem = elem.query_selector('a.posting-title')
        listing_url = link_elem.get_attribute('href') if link_elem else ""
        if listing_url and not listing_url.startswith('http'):
            listing_url = f"https:{listing_url}" if listing_url.startswith('//') else f"https://craigslist.org{listing_url}"
        
        # Images
        img_elem = elem.query_selector('img')
        images = [img_elem.get_attribute('src')] if img_elem and img_elem.get_attribute('src') else []
        
        # Extract mileage
        mileage = 0
        combined_text = f"{title} {meta_text}"
        mileage_match = re.search(r'(\d+[,\d]*)\s*(?:miles|mi|k)', combined_text, re.IGNORECASE)
        if mileage_match:
            mileage = self.extract_mileage(mileage_match.group(1))
        
        return {
            'title': title,
            'price': price,
            'mileage': mileage,
            'location': location,
            'description': meta_text,
            'images': images,
            'listing_url': listing_url,
            'source': 'craigslist'
        }


class Hunter:
    """
    Hunter class responsible for hunting/gathering vehicle listing data from websites.
    Uses strategy pattern to support multiple marketplace platforms.
    """
    
    def __init__(self, ghost=None, config=None):
        """
        Initialize the Hunter.
        """
        self.ghost = ghost
        self.config = config or {}
        self.global_history = set()
        
        # Load global history from DB to prevent duplicate inspections forever
        try:
            from tinydb import TinyDB
            db = TinyDB('database/ledger.json')
            table = db.table('listings')
            # standardized lookup set
            for item in table.all():
                url = item.get('listing_url', '')
                if url:
                    self.global_history.add(url)
                    self.global_history.add(url.split('?')[0]) # Add clean version too
            db.close()
            print(f"   📜 Loaded {len(self.global_history)} previously seen items from history.")
        except Exception as e:
            print(f"Error loading history: {e}")

        self.navigator = Navigator()
        
        # Strategy registry
        self.strategies = {
            'facebook.com': FacebookStrategy(ghost=ghost, navigator=self.navigator),
            'craigslist.org': CraigslistStrategy(navigator=self.navigator),
        }
        
        # Inject history into strategies
        for s in self.strategies.values():
            if hasattr(s, 'set_history'):
                s.set_history(self.global_history)

    # ... get_domain and get_strategy methods unchanged ...
    # ... scrape_url unchanged ...

    def execute(self, target_urls: list) -> list:
        """Execute main hunting process."""
        self.raw_listings = []
        browser_context = None
        if self.ghost:
            browser_context = self.ghost.get_browser_context()
        
        # 1. Scrape all targets first
        for url in target_urls:
            print(f"\n🔍 Scraping: {url}")
            listings = self.scrape_url(url, browser_context)
            self.raw_listings.extend(listings)
        
        # 2. Add found items to global history so we don't re-scrape them next run (within same session)
        for l in self.raw_listings:
            u = l.get('listing_url')
            if u: self.global_history.add(u)
            
        # 3. TRIGGER LONG SOCIAL BREAK (Human Behavior)
        # Instead of rapid switching, we take a dedicated 15-20 min break AFTER the work is done.
        # This replaces the rapid random detours.
        if self.ghost and self.raw_listings:
            print("\n☕ Work complete. Taking a 15-minute social break (Human Pattern)...")
            self.ghost.take_long_break(duration_minutes=15)
        
        print(f"\n📊 Total listings collected: {len(self.raw_listings)}")
        return self.raw_listings
    
    def get_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: Full URL string
            
        Returns:
            str: Domain name (e.g., 'facebook.com', 'craigslist.org')
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            return ""
    
    def get_strategy(self, url: str) -> ScrapeStrategy:
        """
        Select appropriate scraping strategy based on URL domain.
        
        Args:
            url: Target URL
            
        Returns:
            ScrapeStrategy: Appropriate strategy instance, or None if unsupported
        """
        domain = self.get_domain(url)
        
        # Check for exact match
        if domain in self.strategies:
            return self.strategies[domain]
        
        # Check for partial match (e.g., 'm.facebook.com' matches 'facebook.com')
        for key, strategy in self.strategies.items():
            if key in domain:
                return strategy
        
        print(f"⚠️  No strategy found for domain: {domain}")
        return None
    
    def scrape_url(self, url: str, browser_context=None) -> list:
        """
        Scrape listings from a single URL using appropriate strategy.
        
        Args:
            url: Target URL to scrape
            browser_context: Optional browser context from Ghost module
            
        Returns:
            list: List of listing dictionaries
        """
        listings = []
        
        # Get appropriate strategy
        strategy = self.get_strategy(url)
        if not strategy:
            print(f"⚠️  Skipping unsupported URL: {url}")
            return listings
        
        try:
            # Create page from context or new browser
            if browser_context:
                page = browser_context.new_page()
            else:
                with sync_playwright() as p:
                    # Launch visible browser for user interaction (login)
                    print("   🖥️ Launching visible browser...")
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
            
            # Execute strategy
            listings = strategy.scrape(page, url)
            
            # Close page if we created the browser
            if not browser_context:
                browser.close()
            else:
                page.close()
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return listings
    
    def execute(self, target_urls: list) -> list:
        """
        Execute the hunter's main data collection process.
        
        Args:
            target_urls: List of URLs to scrape
            
        Returns:
            list: List of raw listing dictionaries from all sources
        """
        self.raw_listings = []
        
        # Get browser context from Ghost if available
        browser_context = None
        if self.ghost:
            browser_context = self.ghost.get_browser_context()
        
        # Process each URL with appropriate strategy
        for url in target_urls:
            print(f"\n🔍 Scraping: {url}")
            domain = self.get_domain(url)
            print(f"   Domain: {domain}")
            
            listings = self.scrape_url(url, browser_context)
            self.raw_listings.extend(listings)
            print(f"   Found {len(listings)} listings")
        
        print(f"\n📊 Total listings collected: {len(self.raw_listings)}")
        return self.raw_listings
