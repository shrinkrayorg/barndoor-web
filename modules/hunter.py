"""
Hunter module for data collection and retrieval.
Uses Playwright with site-specific scraping strategies.
Implements the Strategy Pattern for modular, extensible scraping.
"""
try:
    from playwright.sync_api import sync_playwright, Page, Locator
except ImportError:
    sync_playwright = None
    Page = None
    Locator = None
    print("⚠️  Playwright not installed. Browser automation disabled (API only).")
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import re
import time
import random
import os
from datetime import datetime
# Import Navigator
from modules.navigator import Navigator, NavReason
# Import Enricher
# Import Enricher - Removed incorrect import
from modules.bright_data import BrightDataManager

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
        Perform minimal random actions to appear human.
        SIMPLIFIED to prevent hanging on mouse moves.
        """
        print("   🤖 Simulating human behavior (Fast)...")
        self.random_sleep(1.5, 3.0)
        # Mouse movements causing hangs in headless/server environments are removed.

    @abstractmethod
    def scrape(self, page: Page, url: str, max_hours: float = None) -> list:
        """
        Scrape listings from a page.
        
        Args:
            page: Playwright page object
            url: Target URL to scrape
            max_hours: Optional filter for listing age
            
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
            
        mileage_text = mileage_text.lower().strip()
        
        # Handle "123k" or "123.5k" notation
        k_match = re.search(r'(\d+(?:\.\d+)?)\s*k', mileage_text)
        if k_match:
            try:
                return int(float(k_match.group(1)) * 1000)
            except: pass

        # Prioritize exact numbers like "123,456"
        exact_match = re.search(r'\b(\d{1,3}(?:,\d{3})+)\b', mileage_text)
        if exact_match:
             return int(exact_match.group(1).replace(',', ''))
             
        # Broad lookup for any sequence of digits, handling separators
        # e.g. "123 456" or "123.456" or "123456"
        digits_match = re.search(r'(\d+(?:[,\s.]\d{3})*)', mileage_text)
        if digits_match:
            digits = re.sub(r'[^\d]', '', digits_match.group(1))
            val = int(digits) if digits else 0
            # Sanity check: if it's like 123, assume it's k? No, too risky.
            return val
            
        return 0



class FacebookStrategy(ScrapeStrategy):
    """
    Scraping strategy for Facebook Marketplace.
    Uses Bright Data Web Scraper API (Server-Side) to bypass anti-bot measures.
    No local browser automation is used for Facebook.
    """
    
    def __init__(self, ghost=None, navigator=None, use_direct_api=True):
        """
        Initialize Facebook strategy.
        
        Args:
            ghost: Unused in API mode, kept for interface compatibility
            navigator: Unused in API mode
            use_direct_api: Enforced to True.
        """
        super().__init__(navigator)
        from modules.bright_data import BrightDataManager
        self.manager = BrightDataManager()
    
    def auto_configure(self, criteria: dict) -> str:
        """
        Configuration is handled via API parameters, not browser navigation.
        Returns a placeholder or configured location string.
        """
        location = criteria.get('location', 'Chicago, IL')
        print(f"   🛠️ Configured for Bright Data: {location}")
        return location

    def scrape(self, page: Page, url: str, max_hours: float = None, progress_callback=None) -> list:
        """
        Scrape Facebook Marketplace using Bright Data API.
        
        Args:
            page: Unused (API mode)
            url: Can be a location string or search URL.
            max_hours: Filter for listing age.
            progress_callback: Callback for UI updates.
        """
        print("   🚀 Initiating Bright Data API Scan (No Browser)...")
        
        # Determine Location and Query from 'url' argument
        # If 'url' is a real URL, we might parse it. 
        # But commonly we pass a config object or location string in this new architecture.
        # Fallback: defaults
        location = "Chicago, IL"
        radius = 50
        
        # Try to parse properties if url looks like parameters
        if "facebook.com" not in url and "," in url:
             location = url # Treat input as location string if not a URL
        
        # Fetch properties from active config if available globally? 
        # Ideally passed in, but we'll try to use the 'url' arg as the location context
        
        print(f"   📍 Context: {location}")
        
        listings = self.manager.fetch_listings(
            location=location,
            radius_miles=radius,
            limit=100,
            sort="date_listed",
            progress_callback=progress_callback
        )
        
        # Apply Time Filter Client-Side (Double Check)
        if max_hours and listings:
            print(f"   ⏰ Applying {max_hours}h time filter...")
            filtered = []
            for l in listings:
                age = l.get('hours_since_listed')
                if age is not None and age <= max_hours:
                    filtered.append(l)
            
            print(f"   ✅ Filtered: {len(filtered)}/{len(listings)} within {max_hours}h")
            return filtered
            
        return listings

    # Legacy methods stubbed out or removed
    def login_if_needed(self, page: Page): pass
    def _extract_deep_details(self, page: Page, url: str): return None
    def _extract_facebook_listing(self, page: Page, elem): return None


class CraigslistStrategy(ScrapeStrategy):
    """
    Scraping strategy for Craigslist.
    Does not require login.
    """
    
    def scrape(self, page: Page, url: str, max_hours: float = None, progress_callback=None) -> list:
        """
        Scrape Craigslist listings.
        
        Args:
            page: Playwright page object
            url: Craigslist search URL
            max_hours: Optional filter for listing age
            progress_callback: Optional callback(current, total, status)
            
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
            # 2026 Update: Support multiple layouts (Gallery, List, Classic, Static)
            listing_elements = page.query_selector_all('.cl-search-result')
            if not listing_elements:
                listing_elements = page.query_selector_all('li.result-row') # Classic
            if not listing_elements:
                listing_elements = page.query_selector_all('li.cl-static-search-result') # Static/NoJS
            if not listing_elements:
                listing_elements = page.query_selector_all('div.gallery-card') # New Gallery View specific
            
            if not listing_elements:
                print("⚠️  No listings found with Craigslist selectors")
                # Debug screenshot for CL failures
                try: page.screenshot(path="debug_cl_failure.png") 
                except: pass
                if progress_callback: progress_callback(100, 100, "Error: Selectors Failed")
                return listings
            
            total_items = len(listing_elements)
            print(f"Found {total_items} Craigslist listings")
            
            if progress_callback:
                progress_callback(0, total_items, "Found listings, extracting...")
            
            # Extract data from each listing
            for idx, elem in enumerate(listing_elements):
                try:
                    listing_data = self._extract_craigslist_listing(page, elem)
                    
                    if listing_data and listing_data.get('title'):
                        # STRICT MODE TIME FILTER
                        if max_hours:
                            age = listing_data.get('hours_since_listed')
                            if age is None:
                                print(f"   ⏳ Skipping (Date Unknown - Strict Filter): {listing_data.get('title')}")
                                continue
                            if age > max_hours:
                                print(f"   ⏳ Skipping (Too Old: {age:.1f}h > {max_hours}h): {listing_data.get('title')}")
                                continue
                                
                        listings.append(listing_data)
                    
                    if progress_callback and idx % 2 == 0:
                         progress_callback(idx + 1, total_items, f"Extracting {idx+1}/{total_items}")
                         
                except Exception as e:
                    print(f"Error extracting Craigslist listing: {e}")
                    continue
            
            print(f"✓ Extracted {len(listings)} Craigslist listings")
            
            if progress_callback:
                 progress_callback(total_items, total_items, "Extraction complete")
            
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
        # Structure variants: "Jan 27", "Jan 27 86k mi", "Jan 27 86k mi CityName"
        # Strategy: Extract Date, Extract Mileage, Remainder is Location
        
        cleaned_meta = meta_text.replace('\n', ' ').strip()
        
        # 1. Extract Date
        hours_since_listed = None # Strict Mode: Default to None (Unknown)
        
        # --- SMART STRICTNESS: EXTENDED CRAIGSLIST DATE PARSING ---
        # Pattern 1: Absolute date "Jan 27" or "1/27"
        date_pattern = r'^(\d{1,2}/\d{1,2}|\w{3}\s\d{1,2})'
        date_match = re.search(date_pattern, cleaned_meta)
        
        # Pattern 2: Relative date "2h ago", "posted 10 mins ago"
        rel_pattern = r'(?:posted|updated)?\s*(\d+)\s*(mins?|hours?|days?|h|m|d)\s*ago'
        rel_match = re.search(rel_pattern, cleaned_meta, re.IGNORECASE)

        date_str = ""
        # Handle Absolute Dates
        if date_match:
            date_str = date_match.group(1)
            # Remove date from string
            cleaned_meta = cleaned_meta.replace(date_str, '', 1).strip()
            
            try:
                today = datetime.now()
                # Parse "Jan 27"
                try:
                    dt = datetime.strptime(date_str, "%b %d")
                    dt = dt.replace(year=today.year) # Assume current year
                    delta = today - dt
                    hours_since_listed = delta.total_seconds() / 3600.0
                except:
                    # Parse "1/27"
                    try:
                         dt = datetime.strptime(date_str, "%m/%d")
                         dt = dt.replace(year=today.year)
                         delta = today - dt
                         hours_since_listed = delta.total_seconds() / 3600.0
                    except: pass
            except:
                pass
            
        # Handle Relative Dates (Overrides absolute if present and more specific)
        if rel_match:
            try:
                val = float(rel_match.group(1))
                unit = rel_match.group(2).lower()
                
                if 'min' in unit or 'm' in unit: hours_since_listed = val / 60.0
                elif 'hour' in unit or 'h' in unit: hours_since_listed = val
                elif 'day' in unit or 'd' in unit: hours_since_listed = val * 24.0
            except: pass
            
        # 2. Extract Mileage for cleanup (redundant to later mileage extract, but needed for location clean)
        mi_pattern = r'(\d+(?:k)?\s*mi)'
        mi_match = re.search(mi_pattern, cleaned_meta, re.IGNORECASE)
        if mi_match:
             cleaned_meta = cleaned_meta.replace(mi_match.group(1), '', 1).strip()
        
        # 3. Remainder is location
        location = cleaned_meta.strip(' -·,')
        if not location:
            location = "Unknown"


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
            'source': 'craigslist',
            'hours_since_listed': hours_since_listed
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

    def update_progress(self, current, total, status="Scraping"):
        """Write progress to status file."""
        try:
            import json
            from pathlib import Path
            status_file = Path('database/scan_status.json')
            # Determine percentage
            percent = 0
            if total > 0:
                percent = int((current / total) * 100)
            elif 0 < current <= 100:
                # If total is 0 but current is e.g. 5, treat as 5% stage
                percent = int(current)
            
            data = {
                'current': current,
                'total': total,
                'percent': percent,
                'status': status,
                'active': True,
                'updated_at': datetime.now().isoformat()
            }
            with open(status_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    # ... get_domain and get_strategy methods unchanged ...
    # ... scrape_url unchanged ...


    
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
    
    def scrape_url(self, url: str, browser_context=None, max_hours: float = None) -> list:
        """
        Scrape listings from a single URL using appropriate strategy.
        
        Args:
            url: Target URL to scrape
            browser_context: Optional browser context from Ghost module
            max_hours: Optional filter for listing age in hours
            
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
                if not sync_playwright:
                    print(f"⚠️  Cannot scrape {url}: Playwright not installed.")
                    return listings
                    
                with sync_playwright() as p:
                    # Launch visible browser for user interaction (login)
                    print("   🖥️ Launching visible browser...")
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
            
            # Progress Callback Wrapper
            def callback(curr, tot, sts):
                domain = self.get_domain(url)
                self.update_progress(curr, tot, f"{domain}: {sts}")

            # Execute strategy
            listings = strategy.scrape(page, url, max_hours=max_hours, progress_callback=callback)
            
            # Close page if we created the browser
            if not browser_context:
                browser.close()
            else:
                page.close()
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return listings
    
    def execute(self, target_urls: list, max_hours: float = None) -> list:
        """
        Execute the hunter's main data collection process.
        
        Args:
            target_urls: List of URLs to scrape
            max_hours: Optional filter for listing age in hours
            
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
            
            listings = self.scrape_url(url, browser_context, max_hours=max_hours)
            self.raw_listings.extend(listings)
            print(f"   Found {len(listings)} listings")
        
        print(f"\n📊 Total listings collected: {len(self.raw_listings)}")
        return self.raw_listings
