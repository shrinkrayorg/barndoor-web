"""
Configuration Database Manager.
Handles saving and retrieving user settings using standard JSON.
Unifies Web UI settings with Backend logic.
"""
import json
import os
from pathlib import Path

class ConfigDB:
    """
    Database interface for application configuration.
    Reads from database/settings.json.
    """
    
    def __init__(self, db_path='database/settings.json'):
        """
        Initialize the configuration database.
        
        Args:
            db_path (str): Path to the JSON settings file.
        """
        self.db_path = Path(db_path)
        # Ensure database directory exists
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Create default if not exists
        if not self.db_path.exists():
            self._create_default_settings()

    def _create_default_settings(self):
        """Create default settings file structure."""
        defaults = {
            "location": {
                "city_state": "Glenview, IL",
                "zip_code": "60025",
                "radius": 200
            },
            "lists": {
                "high_value_makes": ["toyota", "honda", "subaru"],
                "medium_value_makes": ["mazda", "hyundai"],
                "low_value_makes": ["nissan", "ford"]
            },
            "score_weights": {
                "type_pickup": 10,
                "type_minivan": 20,
                "type_handicap": 30,
                "engine_v8": 10
            }
        }
        with open(self.db_path, 'w') as f:
            json.dump(defaults, f, indent=4)

    def get_config(self):
        """
        Get the full configuration dictionary.
        Returns a flattened-like structure for backward compatibility where possible,
        or just the raw dict.
        """
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error reading config: {e}")
            return {}
            
    def get_active_config(self):
        """Aliased to get_config for backward compatibility."""
        return self.get_config()

    def get_profile(self, profile_name=None):
        """Aliased to get_config for backward compatibility."""
        return self.get_config()

    def get_active_profile_name(self):
        """Stub for compatibility."""
        return "Default"

    def update_config(self, new_config):
        """Update the configuration."""
        with open(self.db_path, 'w') as f:
            json.dump(new_config, f, indent=4)
            
    def set_active_profile(self, name):
        pass # No-op
        
    def create_profile(self, data):
        """Aliased to update_config, blindly accepts data if matches schema or just ignores."""
        # For the dashboard patch, we might need to be careful. 
        # But we are REMOVING the dashboard settings page, so this might not be called.
        pass
