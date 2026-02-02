"""
Configuration module for the data processing application.
Loads environment variables and defines application settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys and Credentials
CARFAX_API_KEY = os.getenv('CARFAX_API_KEY')
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
BRIGHT_DATA_API_KEY = os.getenv('BRIGHT_DATA_API_KEY')
BRIGHT_DATA_DATASET_ID = os.getenv('BRIGHT_DATA_DATASET_ID')
BRIGHT_DATA_ZONE = os.getenv('BRIGHT_DATA_ZONE')
BRIGHT_DATA_PROXY_PASS = os.getenv('BRIGHT_DATA_PROXY_PASS')
BRIGHT_DATA_CUSTOMER_ID = os.getenv('BRIGHT_DATA_CUSTOMER_ID')

# Application Configuration
TARGET_URLS = [
    "https://example.com/listings",  # Replace with actual target URLs
    # Add more URLs as needed
]
GEO_RADIUS_MILES = 250  # Maximum geographic radius in miles
HOME_ZIP_CODE = "60025"  # Glenview, IL
PHONE_NUMBER = "+1234567890"  # Phone number to receive SMS alerts (Twilio-formatted)

# Email Configuration for Daily Digest
FROM_EMAIL = "barnfind@yourdomain.com"  # Replace with your verified SendGrid sender
TO_EMAIL = "your-email@example.com"  # Replace with your email address

# Workflow Logic
CRITERIA = {
    # Types to ALWAYS exclude (unless very specific override logic applies)
    "excluded_types": [
        "motorcycle", "scooter", "bike", "boat", "trailer", "rv", "camper", "motorhome",
        "atv", "snowmobile", "parting out", "part out", "parts only", "shell", "chassis",
        "golf cart", "snow plow"
    ],
    
    # Types to ALWAYS Reject (Deal Breakers)
    "deal_breakers": [
        "severe rust", "frame rot", "rusted out", "frame damage", "serious rust",
        "salvage title", "rebuilt title", "branded title"
    ],

    # High Value (Tier 1) - Priority
    "high_value_makes": [
        "toyota", "honda", "subaru", "gmc", "chevrolet", "ford" # specifically trucks/suvs
    ],
    
    # High Value Specific Models
    "high_value_models": [
        "tacoma", "tundra", "sienna", "highlander", "rav-4", "rav4", "prius", "c-hr",
        "crv", "accord", "insight", "fit", "odyssey",
        "gladiator", "wrangler", "grand cherokee"
    ],
    
    # Low Value (Tier 3) - Only buy if < $800 or extremely cheap
    "low_value_models": [
        "altima", "versa", "quest", "leaf", "rogue", "maxima", 
        "focus", "fusion", "taurus", "escape", "edge", "explorer", 
        "aveo", "traverse", "tracker", "equinox", "impala", "malibu", "spark", "cruze",
        "journey", "durango", "caliber", "avenger", "dart",
        "lancer", "eclipse", "mirage",
        "rodeo", "rendezvous", "century", "lesabre", "lucerne",
        "veracruz", "elantra", "tiburon", "sonata", "ascent",
        "grand prix", "torrent",
        "rio", "forte", "soul",
        "compass", "liberty", "commander", "patriot",
        "grand marquis", "crown victoria", "range rover"
    ]
}
