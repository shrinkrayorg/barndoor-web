import os
import json
import random
import time
from datetime import datetime

class Persona:
    """
    Manages the 'Ghost' identity: credentials, bio, behavior history, and stats.
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.profile_path = "database/persona_profile.json"
        self.data = self._load_profile()

    def _load_profile(self):
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                return json.load(f)
        return self._create_default_profile()

    def _create_default_profile(self):
        return {
            "name": "Alex Miller",
            "age": 34,
            "job": "Freelance Carpenter",
            "location": "Glenview, IL",
            "joined_date": datetime.now().strftime("%Y-%m-%d"),
            "interests": ["Classic Cars", "DIY", "Woodworking", "F-150s", "Tool Restoration"],
            "behavior_score": 10, # 0-100, 100 = very human
            "history": []
        }
    
    def save_profile(self):
        with open(self.profile_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def log_activity(self, activity_type, details):
        """Log a user-like activity (e.g., 'watched_video', 'liked_post')."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "details": details
        }
        self.data['history'].append(entry)
        
        # Boost score slightly for every activity
        if self.data['behavior_score'] < 100:
            self.data['behavior_score'] += random.randint(1, 3)
            
        self.save_profile()
        
    def get_warmup_routine(self):
        """Returns a list of actions to perform for warming up."""
        actions = [
            "scroll_feed",
            "watch_reels", 
            "visit_marketplace_home",
            "search_random_item"
        ]
        return random.sample(actions, k=random.randint(2, 4))

    def get_credentials(self):
        # In a real scenario, this might pull from encrypted env vars
        # For now, return placeholders or load from env
        return {
            "email": os.getenv("FACEBOOK_EMAIL"),
            "password": os.getenv("FACEBOOK_PASSWORD")
        }
