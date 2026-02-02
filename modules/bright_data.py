"""
Bright Data Manager Module
Manages interactions with Bright Data's Web Scraper API and Dataset API.
Handles real-time ingestion via specific Facebook Scrapers and historical backfills.
"""
import requests
import time
import json
import os
import re
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrightDataManager:
    """
    Manages interactions with Bright Data APIs.
    """
    
    # Pre-built Scraper ID for Facebook Marketplace
    REALTIME_SCRAPER_ID = "gd_lkaxegm826bjpoo9m5" 
    # Historical Dataset ID
    HISTORICAL_DATASET_ID = "gd_lvt9iwuh6fbcwmx1a"

    def __init__(self, api_key=None, zone="web_unlocker", proxy_pass=None):
        """
        Initialize with credentials.
        """
        import config
        self.api_key = api_key or config.BRIGHT_DATA_API_KEY
        self.zone = os.getenv('BRIGHT_DATA_ZONE', zone)
        self.proxy_pass = proxy_pass or os.getenv('BRIGHT_DATA_PROXY_PASS')
        self.customer_id = os.getenv('BRIGHT_DATA_CUSTOMER_ID') # Often part of the proxy user
        
        if not self.api_key:
            logger.warning("⚠️  BrightDataManager: Missing API Key.")
            
        self.base_url = "https://api.brightdata.com/datasets/v3"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def fetch_via_web_unlocker(self, url: str) -> str:
        """
        Fetch a raw page using Bright Data's Web Unlocker (Proxy Mode).
        Requires BRIGHT_DATA_ZONE and BRIGHT_DATA_PROXY_PASS in environment.
        """
        if not self.proxy_pass or not self.customer_id:
            logger.warning("⚠️  Web Unlocker requires BRIGHT_DATA_CUSTOMER_ID and BRIGHT_DATA_PROXY_PASS")
            return None

        print(f"   🔓 Unlocking: {url}...")
        
        # Construct Proxy String
        # format: brd-customer-{id}-zone-{zone}:{password}
        # Host: brd.superproxy.io:22225
        
        proxy_user = f"brd-customer-{self.customer_id}-zone-{self.zone}"
        proxy_url = f"http://{proxy_user}:{self.proxy_pass}@brd.superproxy.io:22225"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            # verify=False is often needed for SSL bumping proxies
            r = requests.get(url, proxies=proxies, verify=False, timeout=30)
            return r.text
        except Exception as e:
            logger.error(f"   ❌ Unlock Failed: {e}")
            return None

    def fetch_listings(self, location: str, radius_miles: int = 50, limit: int = 100, sort: str = "date_listed", progress_callback=None) -> list:
        """
        Fetch real-time listings using the pre-built Facebook Scraper (Web Scraper API).
        
        Args:
            location: City, State or Zip (e.g. "San Francisco, CA")
            radius_miles: Search radius
            limit: Max listings to return
            sort: Sort order (default: "date_listed" for newest first)
            progress_callback: Optional function(current, total, message)
            
        Returns:
            list: List of standardized listing dictionaries.
        """
        print(f"   🚀 Properties: Location={location}, Radius={radius_miles}mi, Limit={limit}, Sort={sort}")
        
        # Construct Valid Facebook Marketplace URL
        # The scraper requires a direct URL, it does not accept abstract search parameters.
        
        # 1. Convert location to slug (Basic approximation)
        # "Chicago, IL" -> "chicago"
        city_slug = location.split(',')[0].strip().lower().replace(' ', '')
        
        # 2. Build Query Params
        # sort: creation_time_descend, best_match, price_ascend, price_descend
        fb_sort = "best_match"
        if "date" in sort or "newest" in sort:
             fb_sort = "creation_time_descend"
             
        # 3. Construct URL
        # https://www.facebook.com/marketplace/chicago/search?query=vehicles&sortBy=creation_time_descend
        search_url = f"https://www.facebook.com/marketplace/{city_slug}/search?query=vehicles&sortBy={fb_sort}&exact=false"
        
        print(f"   🔗 Constructed Target URL: {search_url}")
        
        # 4. Create Payload
        payload = [{
            "url": search_url,
        }]
        
        if progress_callback:
            progress_callback(10, 100, "Triggering Real-time Scraper...")
            
        snapshot_id = self.trigger_scraper(self.REALTIME_SCRAPER_ID, payload)
        
        if not snapshot_id:
            logger.error("Failed to trigger scraper.")
            return []
            
        # Poll for results
        if progress_callback:
            progress_callback(20, 100, "Waiting for Bright Data (1-3 min)...")
            
        raw_data = self.poll_results(snapshot_id, progress_callback)
        
        if not raw_data:
            print("   ⚠️  Scraper API returned 0 results. switch to Web Unlocker fallback...")
            return self._fallback_web_unlocker(search_url, progress_callback)
            
        # Check if list is empty
        if isinstance(raw_data, list) and len(raw_data) == 0:
             print("   ⚠️  Scraper API returned empty list. Switching to Web Unlocker fallback...")
             return self._fallback_web_unlocker(search_url, progress_callback)
            
        # Format results
        if progress_callback:
            progress_callback(90, 100, "Formatting Data...")
            
        listings = self._format_results(raw_data)
        
        if progress_callback:
            progress_callback(100, 100, f"Complete: {len(listings)} listings")
            
        return listings

    def fetch_historical(self, location: str, max_age_hours: int = 24) -> list:
        """
        Fetch listings from the Historical Dataset (gd_lvt9iwuh6fbcwmx1a).
        """
        # Note: Dataset API filtering is limited. We might need to fetch a batch and filter client-side 
        # or use the /query endpoint if enabled (paid feature).
        # For now, we'll try a trigger with filters if the dataset supports initiated-by-trigger subsetting.
        
        logger.info(f"Fetching historical data for {location}...")
        
        payload = [{
            "location": location,
            "include_blob": True # Request full details
        }]
        
        snapshot_id = self.trigger_scraper(self.HISTORICAL_DATASET_ID, payload)
        if not snapshot_id:
            return []
            
        raw_data = self.poll_results(snapshot_id)
        return self._format_results(raw_data) if raw_data else []

    def trigger_scraper(self, dataset_id: str, payload: list) -> str:
        """Trigger a collection job on a specific dataset/scraper."""
        url = f"{self.base_url}/trigger?dataset_id={dataset_id}"
        
        try:
            r = requests.post(url, headers=self.headers, json=payload)
            r.raise_for_status()
            data = r.json()
            snapshot_id = data.get("snapshot_id")
            print(f"   ✅ Job Started: {snapshot_id}")
            return snapshot_id
        except Exception as e:
            print(f"   ❌ Trigger Failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"      Response: {e.response.text}")
            return None

    def poll_results(self, snapshot_id: str, progress_callback=None) -> list:
        """Poll for completion."""
        url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        start_time = time.time()
        timeout = 600 # 10 minutes
        
        print("   ⏳ Polling for results...")
        
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url, headers=self.headers)
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 202:
                    # Still processing
                    elapsed = time.time() - start_time
                    if progress_callback:
                        # Fake progress 20-80%
                        pct = 20 + int((elapsed / 120) * 60) 
                        progress_callback(min(pct, 85), 100, f"Processing... ({int(elapsed)}s)")
                    time.sleep(10)
                elif r.status_code in [500, 502, 503, 504]:
                    time.sleep(5)
                else:
                    print(f"   ❌ Poll Error: {r.status_code}")
                    return None
            except Exception as e:
                print(f"   ⚠️ Poll Exception: {e}")
                time.sleep(10)
                
        print("   ❌ Polling Timed Out")
        return None

    def _format_results(self, raw_data: list) -> list:
        """
        Normalize Bright Data results into our standard internal Schema.
        """
        listings = []
        for item in raw_data:
            try:
                # Basic fields
                title = item.get('title', 'Unknown')
                
                # Price Normalization
                price = item.get('price') or item.get('final_price') or item.get('initial_price') or 0
                if isinstance(price, str):
                    price = re.sub(r'[^\d]', '', price)
                    price = int(price) if price else 0
                
                # Mileage Normalization
                mileage = 0
                raw_mi = item.get('mileage') or item.get('vehicle_mileage')
                if raw_mi:
                     if isinstance(raw_mi, (int, float)):
                         mileage = int(raw_mi)
                     elif isinstance(raw_mi, str):
                         # "12k miles" -> 12000
                         m_clean = raw_mi.lower().replace(',', '')
                         k_match = re.search(r'(\d+(?:\.\d+)?)\s*k', m_clean)
                         if k_match:
                             mileage = int(float(k_match.group(1)) * 1000)
                         else:
                             digits = re.sub(r'[^\d]', '', m_clean)
                             mileage = int(digits) if digits else 0
                
                # Timestamp Parsing
                posted_at = datetime.now(timezone.utc).isoformat()
                hours_since = 0
                
                date_str = item.get('listing_date') or item.get('date_posted') or item.get('posted_at')
                if date_str:
                    try:
                        # Try ISO
                        if date_str.endswith('Z'):
                             date_str = date_str.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(date_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        
                        posted_at = dt.isoformat()
                        
                        # Calc hours ago
                        now = datetime.now(timezone.utc)
                        diff = now - dt
                        hours_since = diff.total_seconds() / 3600.0
                        if hours_since < 0: hours_since = 0
                    except:
                        pass
                
                # Build Normalized Object
                listing = {
                    'listing_id': str(item.get('id') or item.get('listing_id') or item.get('facebook_id') or ''),
                    'title': title,
                    'price': price,
                    'mileage': mileage,
                    'location': item.get('location', {}).get('address') if isinstance(item.get('location'), dict) else str(item.get('location', '')),
                    'description': item.get('description', '') or item.get('seller_description', ''),
                    'images': item.get('images', []) or [item.get('image_url')] if item.get('image_url') else [],
                    'listing_url': item.get('url') or item.get('original_url'),
                    'source': 'facebook_marketplace',
                    'hours_since_listed': hours_since,
                    'posted_at': posted_at,
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    # Raw Payloads
                    'raw_fields': {k:v for k,v in item.items() if k not in ['images', 'description']}, 
                    'raw_json': item.get('raw_json', {})
                }
                
                # Ensure listing_id is set
                if not listing['listing_id'] and listing['listing_url']:
                    # Extract ID from URL
                    # /item/123456789/
                    match = re.search(r'item/(\d+)', listing['listing_url'])
                    if match:
                        listing['listing_id'] = match.group(1)
                
                # Strict check: need ID and URL
                if listing['listing_id'] and listing['listing_url']:
                    listings.append(listing)
                    
            except Exception as e:
                logger.warning(f"Formatting error: {e}")
                
        return listings

    def _fallback_web_unlocker(self, url: str, progress_callback=None) -> list:
        """
        Fallback: Download raw HTML via Web Unlocker and parse locally.
        """
        if progress_callback:
            progress_callback(50, 100, "Attempting Proxy Fallback...")
            
        html = self.fetch_via_web_unlocker(url)
        if not html:
            return []
            
        # Parse HTML locally
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            print("   Parsing fallback HTML...")
            
            listings = []
            
            # 2026 Generic Marketplace Parsing Strategy
            # Look for <a> tags with 'href' containing '/marketplace/item/'
            
            seen_ids = set()
            
            # Select all links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                
                if '/marketplace/item/' in href:
                    # Found a listing link
                    # Extract ID
                    match = re.search(r'item/(\d+)', href)
                    if not match: continue
                    id_ = match.group(1)
                    
                    if id_ in seen_ids: continue
                    seen_ids.add(id_)
                    
                    # Extract Data from parent/siblings
                    # Strategy: Go up to the container that holds the text
                    
                    # Try to find price and title within the link itself or its text
                    text = link.get_text(" ", strip=True)
                    
                    # Heuristic: Price is usually $123 or 123
                    price = 0
                    price_match = re.search(r'\$(\d{1,3}(?:,\d{3})*)', text)
                    if price_match:
                        price = int(price_match.group(1).replace(',', ''))
                        
                    # Title is the longest text segment?
                    # This is rough, but better than 0.
                    title = text
                    
                    # Image
                    img = link.find('img')
                    image_url = img['src'] if img else ""
                    
                    listing = {
                        'listing_id': id_,
                        'title': title,
                        'price': price,
                        'mileage': 0, # Hard to get from raw HTML easily without specific selectors
                        'location': 'Facebook Marketplace',
                        'description': 'Scraped via Proxy Fallback',
                        'images': [image_url] if image_url else [],
                        'listing_url': f"https://www.facebook.com{href}" if href.startswith('/') else href,
                        'source': 'facebook_marketplace',
                        'scraped_at': datetime.now(timezone.utc).isoformat(),
                        'posted_at': datetime.now(timezone.utc).isoformat(), # Unknown
                        'hours_since_listed': 0
                    }
                    listings.append(listing)
            
            print(f"   ✅ Fallback Recovered {len(listings)} listings")
            return listings
            
        except Exception as e:
            logger.error(f"Fallback parsing failed: {e}")
            return []

# Test
if __name__ == "__main__":
    import sys
    # Verify import works path-wise
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    manager = BrightDataManager()
    print("Manager Initialized.")
