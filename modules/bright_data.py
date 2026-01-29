"""
Bright Data Enricher Module
Integrates with Bright Data's Dataset API to fetch detailed listing data.
Replaces local deep scraping to reduce detection risk.
"""
import requests
import time
import json
import os
import re
from datetime import datetime, timezone

class BrightDataEnricher:
    """
    Manages interactions with Bright Data Dataset API.
    Triggers scraping jobs and retrieves results.
    """
    
    def __init__(self, api_key=None, dataset_id=None):
        """
        Initialize with credentials.
        defaults to loading from environment/config if not provided.
        """
        import config
        self.api_key = api_key or config.BRIGHT_DATA_API_KEY
        self.dataset_id = dataset_id or config.BRIGHT_DATA_DATASET_ID
        
        if not self.api_key or not self.dataset_id:
            print("⚠️  BrightDataEnricher Warning: Missing API Key or Dataset ID.")
            
        self.base_url = "https://api.brightdata.com/datasets/v3"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def enrich(self, urls: list, progress_callback=None) -> list:
        """
        Full workflow: Trigger dataset -> Poll -> Format Results.
        
        Args:
            urls: List of listing URLs to enrich.
            progress_callback: Optional callback(current, total, status)
            
        Returns:
            list: List of standardized listing dictionaries.
        """
        if not urls:
            return []
            
        print(f"   ☁️  Sending {len(urls)} items to Bright Data cloud...")
        if progress_callback:
            progress_callback(0, len(urls), "Sending to Cloud...")
        
        # 1. Trigger
        snapshot_id = self.trigger_dataset(urls)
        if not snapshot_id:
            return []
            
        # 2. Poll
        if progress_callback:
            progress_callback(0, len(urls), "Cloud Processing (Wait 1-3m)...")
            
        raw_data = self.poll_results(snapshot_id, progress_callback, len(urls))
        if not raw_data:
            return []
            
        # 3. Format
        if progress_callback:
            progress_callback(len(urls), len(urls), "Formatting...")
            
        formatted_listings = self._format_results(raw_data)
        print(f"   ✨ Received {len(formatted_listings)} enriched listings from cloud.")
        
        if progress_callback:
             progress_callback(len(urls), len(urls), "Cloud Complete")
        
        return formatted_listings

    def trigger_dataset(self, urls: list) -> str:
        """Trigger the dataset collection for specific URLs."""
        trigger_url = f"{self.base_url}/trigger?dataset_id={self.dataset_id}"
        
        # Format payload: List of objects with "url" key
        payload = [{"url": u} for u in urls]
        
        try:
            r = requests.post(trigger_url, headers=self.headers, json=payload)
            r.raise_for_status()
            data = r.json()
            snapshot_id = data.get("snapshot_id")
            print(f"   🚀 Job started. Snapshot ID: {snapshot_id}")
            return snapshot_id
        except Exception as e:
            print(f"   ❌ Error triggering Bright Data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"      Response: {e.response.text}")
            return None

    def poll_results(self, snapshot_id: str, progress_callback=None, total_expected=0) -> list:
        """Poll for results until ready."""
        result_url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        print("   ⏳ Waiting for results (cloud processing, up to 10m)...", flush=True)
        start_time = time.time()
        timeout = 600  # Restored to 10 minutes to handle 200+ links batches
        
        while time.time() - start_time < timeout:
            try:
                r = requests.get(result_url, headers=self.headers)
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 202:
                    # Still processing
                    elapsed = int(time.time() - start_time)
                    if progress_callback:
                         progress_callback(0, total_expected, f"Cloud Processing... ({elapsed}s)")
                    
                    time.sleep(10)
                    continue
                elif r.status_code in [500, 502, 503, 504]:
                    print(f"   ⚠️ Bright Data server error ({r.status_code}). Retrying in 5s...")
                    time.sleep(5)
                    continue
                else:
                    print(f"   ❌ Error fetching results: {r.status_code} - {r.text}")
                    return None
            except Exception as e:
                print(f"   ⚠️ Polling Error: {e}")
                time.sleep(10)
                
        print("   ❌ Polling timed out.")
        return None

    def _format_results(self, raw_data: list) -> list:
        """
        Convert Bright Data JSON format to Barndoor internal format.
        """
        listings = []
        for item in raw_data:
            try:
                # Map fields
                price = item.get('final_price') or item.get('initial_price') or 0
                
                # Mileage
                mileage = 0
                raw_mileage = item.get('mileage')
                if raw_mileage:
                    if isinstance(raw_mileage, (int, float)):
                        mileage = int(raw_mileage)
                    else:
                        m_text = str(raw_mileage).lower()
                        # Handle "123k" notation
                        k_match = re.search(r'(\d+(?:\.\d+)?)\s*k', m_text)
                        if k_match:
                            mileage = int(float(k_match.group(1)) * 1000)
                        else:
                            digits = re.sub(r'[^\d]', '', m_text)
                            mileage = int(digits) if digits else 0
                
                # If mileage is still 0, try to find it in title or description
                if mileage == 0:
                    combined_text = f"{item.get('title', '')} {item.get('description', '')} {item.get('seller_description', '')}".lower()
                    # Look for "123k miles" or "123,456 miles"
                    m_match = re.search(r'(\d+(?:[,\d.]\d{3})*)\s*k?\s*(?:miles|mi|k\b)', combined_text)
                    if m_match:
                        m_val = m_match.group(1).replace(',', '').replace(' ', '')
                        if 'k' in m_match.group(0).lower():
                             mileage = int(float(m_val) * 1000)
                        else:
                             mileage = int(float(m_val)) if m_val else 0
                
                # Hours Since Listed
                hours_since_listed = 0
                
                # Try 'listing_date' or 'date_posted'
                date_str = item.get('listing_date') or item.get('date_posted')
                if date_str:
                    try:
                        # Handle ISO format with 'Z' or '+00:00'
                        if date_str.endswith('Z'):
                            date_str = date_str.replace('Z', '+00:00')
                        
                        posted_date = datetime.fromisoformat(date_str)
                        now = datetime.now(timezone.utc)
                        
                        # Ensure posted_date has timezone if now does
                        if posted_date.tzinfo is None:
                            posted_date = posted_date.replace(tzinfo=timezone.utc)
                            
                        diff = now - posted_date
                        hours_since_listed = diff.total_seconds() / 3600.0
                        
                        # Sanity check: if it's in the future (due to clock skew), set to 0
                        if hours_since_listed < 0:
                            hours_since_listed = 0
                    except Exception as e:
                        print(f"   ⚠️ Date parse error: {e}")
                
                listing = {
                    'title': item.get('title', 'Unknown'),
                    'price': price,
                    'mileage': mileage, 
                    'location': item.get('location', 'Unknown'),
                    'description': item.get('description', '') or item.get('seller_description', ''),
                    'images': item.get('images', []),
                    'listing_url': item.get('url'),
                    'source': 'facebook_marketplace',
                    'hours_since_listed': hours_since_listed, 
                    'bright_data_snapshot': True
                }
                listings.append(listing)
            except Exception as e:
                print(f"   ⚠️ Error formatting item {item.get('url')}: {e}")
                
        return listings

# Quick Test
if __name__ == "__main__":
    enricher = BrightDataEnricher()
    # Test URLs
    test_urls = [
      "https://www.facebook.com/marketplace/item/981001136298403/",
    ]
    results = enricher.enrich(test_urls)
    print(json.dumps(results, indent=2))
