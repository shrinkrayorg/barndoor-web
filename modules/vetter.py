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
            
        self.geolocator = Nominatim(user_agent="barnfind_vetter_v2")
        self.geo_cache = {} # Cache for geocoding results
        self.processed_listings = []
    
    # ... (Keep get_wholesale_value, calculate_distance, extract_phone_numbers as is) ...

    def get_wholesale_value(self, vin):
        return 15000

    def calculate_distance(self, location):
        try:
            zip_match = re.search(r'\b\d{5}\b', location)
            location_query = zip_match.group() if zip_match else location
            
            # Use cache
            if self.home_zip_code not in self.geo_cache:
                self.geo_cache[self.home_zip_code] = self.geolocator.geocode(self.home_zip_code)
            home_loc = self.geo_cache[self.home_zip_code]
            
            if location_query not in self.geo_cache:
                self.geo_cache[location_query] = self.geolocator.geocode(location_query)
            listing_loc = self.geo_cache[location_query]
            
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
        """Apply hard filters based on database/settings.json."""
        description_lower = (listing.get('description', '') or '').lower()
        title_lower = (listing.get('title', '') or '').lower()
        combined_text = f"{title_lower} {description_lower}"

        filters_cfg = (self.config or {}).get("filters", {}) if isinstance(self.config, dict) else {}

        # 1) Excluded types (optional)
        excluded_types = [t.lower() for t in filters_cfg.get("excluded_types", []) if isinstance(t, str)]
        if excluded_types and any(t in combined_text for t in excluded_types):
            return False, "excluded_vehicle_type"

        # 2) Deal breakers / hard rejects (salvage/branded/rollback etc.)
        reject_title = [k.lower() for k in filters_cfg.get("reject_title_keywords", []) if isinstance(k, str)]
        reject_desc  = [k.lower() for k in filters_cfg.get("reject_description_keywords", []) if isinstance(k, str)]
        reject_rust  = [k.lower() for k in filters_cfg.get("reject_rust_keywords", []) if isinstance(k, str)]

        if reject_title and any(k in combined_text for k in reject_title):
            return False, "reject_title_keyword"
        if reject_desc and any(k in combined_text for k in reject_desc):
            return False, "reject_description_keyword"
        if reject_rust and any(k in combined_text for k in reject_rust):
            return False, "reject_rust_keyword"

        # 3) Location radius check
        location = listing.get('location', '') or ''
        if location:
            distance = self.calculate_distance(location)
            if distance and distance > self.geo_radius_miles:
                # SOFT WARNING: Don't reject, just tag. User might be searching remotely (e.g. Chicago).
                return True, f"passed_but_far_{int(distance)}_miles"

        return True, "passed"

    def apply_valuation_check(self, listing):
        return True
    def calculate_score(self, listing):
        """
        Calculate quality score using database/settings.json.
        Keeps the existing heuristics but pulls lists/weights from settings.json.
        """
        score = 50
        tags = []

        cfg = self.config if isinstance(self.config, dict) else {}
        lists_cfg = cfg.get("lists", {}) or {}
        weights = cfg.get("score_weights", {}) or {}

        high_value = [str(x).lower() for x in lists_cfg.get("high_value_makes", [])]
        medium_value = [str(x).lower() for x in lists_cfg.get("medium_value_makes", [])]
        low_value = [str(x).lower() for x in lists_cfg.get("low_value_makes", [])]

        description_lower = (listing.get('description', '') or '').lower()
        title_lower = (listing.get('title', '') or '').lower()
        combined_text = f"{description_lower} {title_lower}"

        year = self._extract_year(combined_text)
        mileage = listing.get('mileage', 0) or 0
        price = listing.get('price', 0) or 0
        make = self._extract_make(combined_text)
        vehicle_type = self._extract_type(combined_text)

        # --- Junk SUV suppression (allow only if super cheap) ---
        filters_cfg = cfg.get("filters", {}) or {}
        junk_keywords = [str(x).lower() for x in filters_cfg.get("junk_suv_keywords", [])]
        junk_override = int(filters_cfg.get("junk_suv_price_override", 1000) or 1000)

        is_junk_suv = False
        # Detect: SUV or common SUV body phrasing + keyword match
        if ("suv" in combined_text or vehicle_type == "suv") and junk_keywords:
            if any(k in combined_text for k in junk_keywords):
                is_junk_suv = True

        if is_junk_suv:
            if price <= junk_override:
                # allow but never prioritize
                score = min(score, 30)
                tags.append("junk_suv_super_cheap")
            else:
                # suppress hard: no alerts, effectively non-viable margin
                score -= 80
                tags.append("junk_suv_suppressed")

        # --- 1) Low-value logic (down-rank; reject unless "value is in the hundreds") ---
        is_low_value = any(m in combined_text for m in low_value)
        if is_low_value:
            if price > 1500:
                score -= 100
                tags.append("reject_low_value_model")
            else:
                score -= 10
                tags.append("cheap_low_value_model")

        # --- 2) High/Medium value logic ---
        is_high_value = False
        if any(h in combined_text for h in high_value):
            score += int(weights.get("high_value_bonus", 15))
            tags.append("high_value_keyword")
            is_high_value = True
        elif make and any(make == h for h in high_value):
            score += int(weights.get("high_value_bonus", 15))
            tags.append("high_value_make")
            is_high_value = True
        elif any(m in combined_text for m in medium_value):
            score += int(weights.get("medium_value_bonus", 5))
            tags.append("medium_value_keyword")

        # --- 3) Freshness bonus ---
        hours_since_listed = listing.get('hours_since_listed')
        if hours_since_listed is not None and hours_since_listed < 1.0:
            score += int(weights.get("freshness_under_1hr", 25))
            tags.append("fresh_listing")
        elif hours_since_listed is not None and hours_since_listed < 24.0:
            score += int(weights.get("freshness_under_24hr", 10))
            tags.append("daily_listing")

        # --- 4) Year/Mileage preference ---
        if year:
            if year >= 2010:
                score += int(weights.get("year_2010_plus", 10))
                tags.append("modern_year")
            elif year < 2005 and not is_high_value:
                score += int(weights.get("older_non_high_value_penalty", -10))
                tags.append("older_non_high_value")

        if mileage > 0:
            if mileage <= 120000:
                score += int(weights.get("mileage_under_120k", 15))
                tags.append("low_mileage")
            elif mileage > 180000 and not is_high_value:
                score += int(weights.get("high_mileage_penalty", -20))
                tags.append("high_mileage_risk")

        # --- 5) Engine/type bonuses from weights ---
        if "v8" in combined_text:
            score += int(weights.get("engine_v8", 10))
            tags.append("v8_engine")

        if vehicle_type == "pickup":
            score += int(weights.get("type_pickup", 15))
            tags.append("pickup_truck")
        elif vehicle_type == "minivan":
            score += int(weights.get("type_minivan", 15))
            tags.append("minivan")
            if any(k in combined_text for k in ["handicap", "wheelchair", "mobility", "ramp"]):
                score += int(weights.get("type_handicap", 40))
                tags.append("handicap_accessible")


        # --- Repair tolerance logic (dealer-realistic) ---
        # Allow common AWD / traction faults and normal $1500 repairs
        repair_tolerance = 2000
        estimated_repairs = 0

        if any(k in combined_text for k in ["awd fault", "traction control", "stability control", "abs light"]):
            estimated_repairs += 500
            tags.append("awd_or_sensor_issue")

        if any(k in combined_text for k in ["rough shift", "hesitation"]):
            estimated_repairs += 1000
            tags.append("minor_transmission_issue")

        if estimated_repairs > repair_tolerance:
            score -= 30
            tags.append("repair_cost_exceeds_tolerance")
        # --- 6) Spanish/emoji checks (kept) ---
        spanish_keywords = [
            "titulo", "trasmision", "limpio", "llantas", "negociable",
            "asientos", "falla", "luces", "corre", "conduce", "motor",
            "aire", "frio", "caliente", "genial", "al 100"
        ]
        spanish_count = sum(1 for word in spanish_keywords if word in description_lower)
        if spanish_count >= 2:
            score += int(weights.get("spanish_description_penalty", -10))
            tags.append("spanish_description")

        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
        if len(emoji_pattern.findall(combined_text)) > 4:
            score -= 10
            tags.append("excessive_emojis")

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
