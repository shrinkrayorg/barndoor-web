"""
Vetter module for data validation and verification.
Applies hard filters, valuation checks, and scoring algorithms to vehicle listings.
"""
import re
from geopy.distance import geodesic
from geopy.geocoders import Nominatim


class Vetter:
    """
    Vetter class responsible for vetting/validating collected vehicle listing data.
    Implements filtering, valuation, and scoring logic.
    """
    
    def __init__(self, config):
        """
        Initialize the Vetter module with configuration.
        
        Args:
            config (dict): Configuration dictionary containing location and filtering settings
        """
        self.config = config
        
        # Handle new nested structure from settings.json
        location_config = config.get('location', {})
        self.home_zip_code = location_config.get('zip_code', '60025')
        try:
            self.geo_radius_miles = int(location_config.get('radius', 250))
        except (ValueError, TypeError):
            self.geo_radius_miles = 250
            
        self.geolocator = Nominatim(user_agent="barnfind_vetter")
        self.processed_listings = []
    
    # ... (Keep get_wholesale_value, calculate_distance, extract_phone_numbers as is) ...

    def get_wholesale_value(self, vin):
        return 15000

    def calculate_distance(self, location):
        try:
            zip_match = re.search(r'\b\d{5}\b', location)
            location_query = zip_match.group() if zip_match else location
            home_loc = self.geolocator.geocode(self.home_zip_code)
            listing_loc = self.geolocator.geocode(location_query)
            if home_loc and listing_loc:
                return geodesic((home_loc.latitude, home_loc.longitude), (listing_loc.latitude, listing_loc.longitude)).miles
        except:
             return None
        return None

    def extract_phone_numbers(self, text):
         if not text: return []
         # Stricter regex: 10 digits required if just numbers, or (XXX) XXX-XXXX
         # Avoid matching "500 2006" (Price Year) by requiring specific separators or context
         patterns = [
             r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 555-555-5555 or 555.555.5555
             r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',     # (555) 555-5555
         ]
         nums = []
         for p in patterns: 
             matches = re.findall(p, text)
             nums.extend(matches)
         return list(set([n.strip() for n in nums]))

    def apply_hard_filters(self, listing):
        """Apply hard filters."""
        description_lower = listing.get('description', '').lower()
        salvage_keywords = ['salvage', 'rebuilt', 'branded']
        if any(keyword in description_lower for keyword in salvage_keywords):
            return False, "salvage_title"
        
        location = listing.get('location', '')
        if location:
            distance = self.calculate_distance(location)
            if distance and distance > self.geo_radius_miles:
                return False, f"too_far_{int(distance)}_miles"
        return True, "passed"

    def apply_valuation_check(self, listing):
        return True

    def calculate_score(self, listing):
        """
        Calculate quality score using dynamic weights from settings.json.
        """
        score = 50  # Starting score
        tags = []
        
        # Get settings
        weights = self.config.get('score_weights', {})
        lists = self.config.get('lists', {})
        
        # Parse Lists (defaults if empty)
        tier1_makers = lists.get('high_value_makes') or ['toyota', 'honda', 'subaru']
        tier2_makers = lists.get('medium_value_makes') or ['mazda', 'hyundai']
        tier3_makers = lists.get('low_value_makes') or ['nissan', 'ford', 'chevy']
        
        # Normalize lists
        tier1_makers = [x.lower() for x in tier1_makers]
        tier2_makers = [x.lower() for x in tier2_makers]
        tier3_makers = [x.lower() for x in tier3_makers]

        description_lower = listing.get('description', '').lower()
        title_lower = listing.get('title', '').lower()
        combined_text = description_lower + ' ' + title_lower
        
        # Extract attributes
        year = self._extract_year(combined_text)
        mileage = listing.get('mileage', 0)
        make = self._extract_make(combined_text)
        vehicle_type = self._extract_type(combined_text)
        
        # --- Dynamic Scoring ---
        
        # Make Tiers
        if make:
            make_lower = make.lower()
            if any(m in make_lower for m in tier1_makers):
                score += 40
                tags.append('tier1_make')
            elif any(m in make_lower for m in tier2_makers):
                score += 25
                tags.append('tier2_make')
            elif any(m in make_lower for m in tier3_makers):
                # Penalty only if high mileage/old
                if year and year <= 2012 and mileage > 80000:
                    score -= 20
                    tags.append('tier3_risk')
                else:
                    score += 5
        
        # Vehicle Type Bonuses (Dynamic)
        if vehicle_type == 'pickup':
            bonus = weights.get('type_pickup', 10)
            score += bonus
            tags.append('pickup_bonus')
            
        if vehicle_type == 'minivan':
            bonus = weights.get('type_minivan', 20)
            score += bonus
            tags.append('minivan_bonus')
            
        # Feature Bonuses (Dynamic)
        handicap_keywords = ['handicap', 'wheelchair', 'ramp']
        if any(k in combined_text for k in handicap_keywords):
            bonus = weights.get('type_handicap', 30)
            score += bonus
            tags.append('handicap_access')
            
        if 'v8' in combined_text:
            bonus = weights.get('engine_v8', 10)
            score += bonus
            tags.append('v8_engine')
        
        # Condition Penalties (Static for now, could move to config too)
        mechanical_issues = ['needs engine', 'transmission issue', 'rod knock', 'tow away']
        if any(issue in combined_text for issue in mechanical_issues):
            score -= 50
            tags.append('mechanical_issue')
        
        # Spanish & Emoji Penalties (User Request 2026-01-24)
        spanish_keywords = [
            'titulo', 'trasmision', 'limpio', 'llantas', 'negociable', 
            'asientos', 'falla', 'luces', 'corre', 'conduce', 'motor', 
            'aire', 'frio', 'caliente', 'genial', 'al 100'
        ]
        
        # Check for Spanish
        spanish_count = sum(1 for word in spanish_keywords if word in description_lower)
        if spanish_count >= 2: # Threshold to avoid false positives on cognates like 'motor'
            penalty = weights.get('spanish_description_penalty', -20)
            score += penalty # Add the negative value
            tags.append('spanish_description_penalty')
            
        # Check for excessive Emojis
        # Simple regex for common emoji ranges and specific ones seen in screenshot
        # Matches most 4-byte unicode characters which include emojis
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        emojis_found = emoji_pattern.findall(combined_text)
        
        if len(emojis_found) > 4:
            score -= 20
            tags.append('excessive_emojis')
        
        return score, tags
    
    def _extract_year(self, text):
        """Extract vehicle year from text."""
        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text)
        return int(year_match.group()) if year_match else None
    
    def _extract_make(self, text):
        """Extract vehicle make from text."""
        makes = ['toyota', 'honda', 'subaru', 'nissan', 'ford', 'chevy', 'chevrolet',
                'dodge', 'mitsubishi', 'buick', 'hyundai', 'kia', 'jeep', 'gmc']
        for make in makes:
            if make in text:
                return make
        return None
    
    def _extract_type(self, text):
        """Extract vehicle type from text."""
        if 'pickup' in text or 'truck' in text:
            return 'pickup'
        elif 'suv' in text:
            return 'suv'
        elif 'minivan' in text or 'van' in text:
            return 'minivan'
        return None
    
    def execute(self, raw_listings):
        """
        Execute the vetter's main validation and scoring process.
        
        Args:
            raw_listings: List of raw listing dictionaries
            
        Returns:
            list: List of processed and scored listings that passed filters
        """
        self.processed_listings = []
        
        for listing in raw_listings:
            # Step 1: Apply hard filters
            passed, reason = self.apply_hard_filters(listing)
            if not passed:
                print(f"Filtered out: {listing.get('title', 'Unknown')} - {reason}")
                continue
            
            # Step 2: Apply valuation check
            if not self.apply_valuation_check(listing):
                print(f"Filtered out: {listing.get('title', 'Unknown')} - overpriced")
                continue
            
            # Step 3: Calculate score
            score, tags = self.calculate_score(listing)
            
            # Step 4: Extract phone numbers from description
            combined_text = f"{listing.get('title', '')} {listing.get('description', '')}"
            phone_numbers = self.extract_phone_numbers(combined_text)
            
            # Create processed listing
            processed = listing.copy()
            processed['score'] = score
            processed['tags'] = tags
            processed['vet_status'] = 'approved'
            processed['phone_numbers'] = phone_numbers  # Add extracted phone numbers
            
            self.processed_listings.append(processed)
            print(f"Approved: {listing.get('title', 'Unknown')} - Score: {score}")
        
        print(f"Vetted: {len(self.processed_listings)}/{len(raw_listings)} listings approved")
        return self.processed_listings
