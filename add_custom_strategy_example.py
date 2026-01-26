"""
Example script demonstrating how to add new scraping strategies to Hunter.

This shows how to extend the Hunter module with a new marketplace platform.
"""
from playwright.sync_api import Page
from modules.hunter import ScrapeStrategy
import re


class OfferUpStrategy(ScrapeStrategy):
    """
    Example scraping strategy for OfferUp marketplace.
    Demonstrates how to create a new strategy for a different platform.
    """
    
    def scrape(self, page: Page, url: str) -> list:
        """
        Scrape OfferUp listings.
        
        Args:
            page: Playwright page object
            url: OfferUp search URL
            
        Returns:
            list: List of listing dictionaries
        """
        listings = []
        
        try:
            # Navigate to URL
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # OfferUp-specific selectors (example - would need actual selectors)
            listing_elements = page.query_selector_all('div[data-testid="listing-card"]')
            
            if not listing_elements:
                print("⚠️  No listings found with OfferUp selectors")
                return listings
            
            print(f"Found {len(listing_elements)} OfferUp listings")
            
            # Extract data from each listing
            for elem in listing_elements:
                try:
                    listing_data = self._extract_offerup_listing(page, elem)
                    if listing_data and listing_data.get('title'):
                        listings.append(listing_data)
                except Exception as e:
                    print(f"Error extracting OfferUp listing: {e}")
                    continue
            
            print(f"✓ Extracted {len(listings)} OfferUp listings")
            
        except Exception as e:
            print(f"Error scraping OfferUp: {e}")
        
        return listings
    
    def _extract_offerup_listing(self, page: Page, elem) -> dict:
        """Extract data from a single OfferUp listing element."""
        # Title
        title_elem = elem.query_selector('h2')
        title = title_elem.inner_text().strip() if title_elem else ""
        
        # Price
        price_elem = elem.query_selector('span.price')
        price_text = price_elem.inner_text() if price_elem else "0"
        price = self.extract_price(price_text)
        
        # Location
        location_elem = elem.query_selector('div.location')
        location = location_elem.inner_text().strip() if location_elem else ""
        
        # URL
        link_elem = elem.query_selector('a')
        listing_url = link_elem.get_attribute('href') if link_elem else ""
        if listing_url and not listing_url.startswith('http'):
            listing_url = f"https://offerup.com{listing_url}"
        
        # Images
        img_elem = elem.query_selector('img')
        images = [img_elem.get_attribute('src')] if img_elem and img_elem.get_attribute('src') else []
        
        # Description (might require detail page visit)
        description = ""
        
        # Mileage (extract from title if present)
        mileage = 0
        mileage_match = re.search(r'(\d+[,\d]*)\s*(?:miles|mi|k)', title, re.IGNORECASE)
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
            'source': 'offerup'
        }


def add_offerup_to_hunter():
    """
    Example function showing how to add OfferUp strategy to Hunter.
    
    Usage:
        from modules import Hunter
        hunter = Hunter()
        add_offerup_to_hunter(hunter)
    """
    from modules import Hunter
    
    # Create Hunter instance
    hunter = Hunter()
    
    # Add OfferUp strategy to the strategy registry
    hunter.strategies['offerup.com'] = OfferUpStrategy()
    
    print("✅ OfferUp strategy added to Hunter")
    print(f"Supported domains: {list(hunter.strategies.keys())}")
    
    return hunter


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Adding Custom Strategy to Hunter")
    print("=" * 60)
    
    hunter = add_offerup_to_hunter()
    
    print("\n💡 Now you can scrape OfferUp URLs:")
    print("   hunter.execute(['https://offerup.com/search/?q=cars'])")
