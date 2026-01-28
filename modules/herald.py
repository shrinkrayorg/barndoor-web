"""
Herald module for notifications and communications.
Sends SMS alerts via Twilio for high-score listings and manages daily digest.
Sends email digests via SendGrid.
"""
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


class Herald:
    """
    Herald class responsible for heralding/announcing results and sending notifications.
    Uses Twilio for SMS alerts and maintains a daily digest for medium-score items.
    Uses SendGrid for email digest reports.
    """
    
    def __init__(self, config):
        """
        Initialize the Herald module with configuration.
        
        Args:
            config (dict): Configuration dictionary containing Twilio and SendGrid credentials
        """
        self.config = config
        
        # Extract credentials and settings from config
        self.twilio_sid = config.get('twilio_sid')
        self.twilio_token = config.get('twilio_token')
        self.sendgrid_api_key = config.get('sendgrid_api_key')
        self.from_number = config.get('twilio_from_number')
        self.to_number = config.get('notification_phone')
        self.from_email = config.get('sendgrid_from_email')
        self.to_email = config.get('notification_email')
        
        self.daily_digest = []
        
        # Initialize Twilio client if credentials are provided
        self.client = None
        if self.twilio_sid and self.twilio_token:
            try:
                self.client = Client(self.twilio_sid, self.twilio_token)
            except Exception as e:
                print(f"Warning: Could not initialize Twilio client: {e}")
        else:
             print("Twilio credentials missing in config.")
        
        # Initialize SendGrid client if API key is provided
        self.sg_client = None
        if self.sendgrid_api_key:
            try:
                self.sg_client = SendGridAPIClient(self.sendgrid_api_key)
            except Exception as e:
                print(f"Warning: Could not initialize SendGrid client: {e}")
    
    def send_sms(self, message):
        """
        Send an SMS message via Twilio.
        
        Args:
            message: Message text to send
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.client:
            print("Twilio client not initialized. Skipping SMS.")
            return False
        
        if not self.to_number:
            print("No recipient phone number configured. Skipping SMS.")
            return False
        
        try:
            # If no from_number specified, Twilio will use default
            message_params = {
                'body': message,
                'to': self.to_number
            }
            
            if self.from_number:
                message_params['from_'] = self.from_number
            
            msg = self.client.messages.create(**message_params)
            print(f"SMS sent successfully: {msg.sid}")
            return True
            
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False
    
    def send_email(self, subject, html_content, plain_content=None):
        """
        Send an email via SendGrid.
        
        Args:
            subject: Email subject line
            html_content: HTML body content
            plain_content: Plain text alternative (optional)
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.sg_client:
            print("SendGrid client not initialized. Skipping email.")
            return False
        
        if not self.from_email or not self.to_email:
            print("Email addresses not configured. Skipping email.")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if plain_content:
                message.plain_text_content = Content("text/plain", plain_content)
            
            response = self.sg_client.send(message)
            print(f"Email sent successfully: {response.status_code}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def format_alert_message(self, listing):
        """
        Format a listing into an SMS alert message.
        
        Args:
            listing: Dictionary containing listing data
            
        Returns:
            str: Formatted message text
        """
    def format_alert_message(self, listing):
        """
        Format a listing into an SMS alert message.
        """
        title = listing.get('title', 'Unknown Vehicle')
        price = listing.get('price', 0)
        score = listing.get('score', 0)
        url = listing.get('listing_url', 'No URL')
        
        # Tags indicator
        tags = listing.get('tags', [])
        tag_str = ""
        if 'fresh_listing' in tags: tag_str += "🔥FRESH "
        if 'high_value_make' in tags or 'high_value_model' in tags: tag_str += "💎GEM "
        
        # Phone Numbers
        phone_numbers = listing.get('phone_numbers', [])
        contact_info = ""
        if phone_numbers:
            contact_info = f"\n📞 CALL: {', '.join(phone_numbers)}"
        
        # Truncate title if too long
        if len(title) > 30:
            title = title[:27] + '...'
        
        # Format
        message = f"{tag_str}{title} - ${price:,} (Score: {score}){contact_info}\n{url}"
        return message
    
    def format_digest_email(self):
        """
        Format the daily digest as an HTML email.
        
        Returns:
            tuple: (html_content, plain_content)
        """
        if not self.daily_digest:
            return None, None
        
        # Sort by score descending
        sorted_listings = sorted(
            self.daily_digest,
            key=lambda x: x.get('score', 0),
            reverse=True
        )
        
        # Build HTML content
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }
                h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
                .summary { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .listing { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; background-color: #fafafa; }
                .listing-title { font-size: 18px; font-weight: bold; color: #2980b9; margin-bottom: 5px; }
                .score { display: inline-block; background-color: #3498db; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
                .price { font-size: 20px; color: #27ae60; font-weight: bold; margin: 10px 0; }
                .details { color: #7f8c8d; font-size: 14px; }
                .tags { margin-top: 10px; }
                .tag { display: inline-block; background-color: #95a5a6; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; margin-right: 5px; }
                .link { display: inline-block; margin-top: 10px; padding: 8px 15px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }
                .footer { margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚗 Barnfind Daily Digest</h1>
                <div class="summary">
                    <strong>Summary:</strong> {count} vehicles found with scores between 70-89
                </div>
        """.format(count=len(sorted_listings))
        
        # Add each listing
        for i, listing in enumerate(sorted_listings, 1):
            title = listing.get('title', 'Unknown Vehicle')
            price = listing.get('price', 0)
            score = listing.get('score', 0)
            location = listing.get('location', 'Unknown')
            mileage = listing.get('mileage', 0)
            url = listing.get('listing_url', '#')
            tags = listing.get('tags', [])
            
            html += f"""
                <div class="listing">
                    <div class="listing-title">{i}. {title}</div>
                    <div class="score">Score: {score}</div>
                    <div class="price">${price:,}</div>
                    <div class="details">
                        📍 {location} | 🛣️ {mileage:,} miles
                    </div>
            """
            
            if tags:
                html += '<div class="tags">'
                for tag in tags:
                    html += f'<span class="tag">{tag}</span>'
                html += '</div>'
            
            html += f'<a href="{url}" class="link">View Listing →</a>'
            html += '</div>'
        
        html += """
                <div class="footer">
                    <p>This is your automated daily digest from Barnfind.</p>
                    <p>High-scoring vehicles (90+) are sent via SMS immediately.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Build plain text version
        plain = f"BARNFIND DAILY DIGEST\n\n{len(sorted_listings)} vehicles found with scores 70-89\n\n"
        for i, listing in enumerate(sorted_listings, 1):
            plain += f"{i}. {listing.get('title', 'Unknown')}\n"
            plain += f"   Score: {listing.get('score', 0)} | Price: ${listing.get('price', 0):,}\n"
            plain += f"   Location: {listing.get('location', 'Unknown')} | Mileage: {listing.get('mileage', 0):,}\n"
            plain += f"   URL: {listing.get('listing_url', '#')}\n\n"
        
        return html, plain
    
    def send_daily_digest_email(self):
        """
        Send the daily digest via SendGrid email.
        
        Returns:
            bool: True if email sent successfully
        """
        if not self.daily_digest:
            print("Daily digest is empty, no email to send")
            return False
        
        html_content, plain_content = self.format_digest_email()
        
        if not html_content:
            return False
        
        subject = f"🚗 Barnfind Daily Digest - {len(self.daily_digest)} Vehicles Found"
        success = self.send_email(subject, html_content, plain_content)
        
        if success:
            print(f"Daily digest email sent with {len(self.daily_digest)} listings")
        
        return success
    
    def process_listing(self, listing):
        """
        Process a listing and send appropriate notification based on score.
        
        Args:
            listing: Dictionary containing listing data with score
        """
        score = listing.get('score', 0)
        
        if score >= 90:
            # High score: Send immediate SMS alert
            message = self.format_alert_message(listing)
            self.send_sms(message)
            print(f"⚡ HIGH SCORE ALERT sent for: {listing.get('title', 'Unknown')}")
            
        elif 70 <= score < 90:
            # Medium score: Add to daily digest
            self.daily_digest.append(listing)
            print(f"📋 Added to daily digest: {listing.get('title', 'Unknown')} (Score: {score})")
        
        else:
            # Low score: No action
            print(f"ℹ️  Low score, no alert: {listing.get('title', 'Unknown')} (Score: {score})")
    
    def get_daily_digest(self):
        """
        Get the current daily digest list.
        
        Returns:
            list: List of medium-score listings
        """
        return self.daily_digest
    
    def clear_daily_digest(self):
        """
        Clear the daily digest list.
        """
        count = len(self.daily_digest)
        self.daily_digest = []
        print(f"Daily digest cleared ({count} items removed)")
    
    def execute(self, processed_listings):
        """
        Execute the herald's main notification process.
        
        Args:
            processed_listings: List of processed listing dictionaries
        """
        for listing in processed_listings:
            self.process_listing(listing)
