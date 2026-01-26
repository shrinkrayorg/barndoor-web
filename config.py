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

# Application Configuration
TARGET_URLS = [
    "https://example.com/listings",  # Replace with actual target URLs
    # Add more URLs as needed
]
GEO_RADIUS_MILES = 250  # Maximum geographic radius in miles
HOME_ZIP_CODE = "00000"  # Replace with actual home ZIP code
PHONE_NUMBER = "+1234567890"  # Phone number to receive SMS alerts (Twilio-formatted)

# Email Configuration for Daily Digest
FROM_EMAIL = "barnfind@yourdomain.com"  # Replace with your verified SendGrid sender
TO_EMAIL = "your-email@example.com"  # Replace with your email address
