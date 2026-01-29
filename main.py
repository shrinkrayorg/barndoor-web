import argparse
"""
Main execution script for the Barnfind data processing application.
Orchestrates the Hunter, Vetter, Ghost, and Herald modules for automated vehicle market analysis.
Runs on a schedule: every 10 minutes for pipeline execution, midnight for daily digest.
"""
from tinydb import TinyDB, Query
from database.config_db import ConfigDB
from datetime import datetime, timedelta
import schedule
import time
import sys
import random
import os
from dotenv import load_dotenv
import functools

# Load env vars immediately
load_dotenv()

# Force immediate log flushing for UI visibility
print = functools.partial(print, flush=True)

class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush() # Ensure immediate write
    def flush(self):
        for f in self.files:
            f.flush()

# Redirect stdout/stderr to both console and log file for UI visibility
try:
    log_file = os.path.join(os.path.dirname(__file__), 'barnfind.log')
    f = open(log_file, 'a')
    original_stdout = sys.stdout
    sys.stdout = Tee(sys.stdout, f)
    sys.stderr = Tee(sys.stderr, f)
except Exception as e:
    print(f"⚠️ Logging redirection failed: {e}")


# Global instances (persistent across scheduled runs)
db = None
listings_table = None
ghost = None
hunter = None
vetter = None
herald = None
account_creator = None
active_config = None
session_start_time = 0
session_rotation_interval = 0
mongo_client = None
mongo_db = None


def initialize_modules():
    """
    Initialize all modules and database connections.
    Called once at startup.
    """
    global db, listings_table, ghost, hunter, vetter, herald, account_creator, active_config, mongo_client, mongo_db
    
    
    # Import modules here to catch ImportError within main try/except block
    from modules import Hunter, Vetter, Ghost, Herald
    
    print("=" * 60)
    print("🚗 BARNFIND - Automated Vehicle Market Analysis")
    print("=" * 60)
    
    # Load configuration
    print("\n[0/4] Loading Active Profile...")
    config_db = ConfigDB()
    active_config = config_db.get_active_config()
    
    if not active_config:
        print("❌ CRITICAL ERROR: No active profile selected.")
        print("   Please run 'streamlit run dashboard.py', go to Access Portal, and select an active profile.")
        sys.exit(1)
        
    profile_name = active_config.get('profile_name') or "Local Settings"
    print(f"   ✅ Loaded Profile: {profile_name}")
    
    # Initialize database
    print("\n[0.5/4] initializing Database System (v3.0)...")
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("   ⚠️  MONGO_URI not found in environment variables.")
    else:
        print(f"   📡 MONGO_URI detected (Length: {len(mongo_uri)})")
    
    if mongo_uri:
        try:
            import certifi
            from pymongo import MongoClient
            mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
            mongo_db = mongo_client['barndoor']
            # Send a ping to confirm a successful connection
            mongo_client.admin.command('ping')
            print("   ✅ Connected to MongoDB!")
            
            # Initialize Adapter for listings_table
            class MongoAdapter:
                def __init__(self, collection):
                    self.collection = collection
                def get_by_url(self, url):
                    res = self.collection.find_one({'listing_url': url})
                    return [res] if res else []
                def insert(self, doc):
                    self.collection.insert_one(doc)
                def update_by_url(self, url, data):
                    self.collection.update_one({'listing_url': url}, {'$set': data})
                def search(self, query):
                    return [] # Fallback for legacy calls
            
            listings_table = MongoAdapter(mongo_db['listings'])
            db = mongo_client # Standard closeable handle for finally blocks
            print("   ☁️  Using MongoDB Adapter")
            
        except Exception as e:
            print(f"   ❌ MongoDB Connection Failed: {e}")
            mongo_db = None
            
    if mongo_db is None:
        print("   📂 Using TinyDB (Local File Storage)")
        db = TinyDB('database/ledger.json')
        listings_table = db.table('listings')
    
    # Initialize Ghost for browser session management
    print("\n[1/4] Initializing Ghost (Browser Session Manager)...")
    ghost = Ghost(config=active_config)
    ghost.execute()
    
    # Init Session Rotation (5-25 mins)
    global session_start_time, session_rotation_interval
    session_start_time = time.time()
    session_rotation_interval = random.randint(5 * 60, 25 * 60)
    print(f"   ⏱️  Session Rotation active. Next swap in {int(session_rotation_interval/60)} mins.")
    
    # Initialize Hunter with Ghost integration
    print("\n[2/4] Initializing Hunter (Data Collection)...")
    hunter = Hunter(ghost=ghost, config=active_config)
    
    # Initialize Vetter
    print("\n[3/4] Initializing Vetter (Validation & Scoring)...")
    # Initialize Vetter
    print("\n[3/4] Initializing Vetter (Validation & Scoring)...")
    vetter = Vetter(config=active_config)
    
    # Initialize Herald
    print("\n[4/4] Initializing Herald (Notifications)...")
    herald = Herald(config=active_config)
    
    print("\n✅ Initialization Complete! Starting Scheduler...")
    # Initialize AccountCreator (accessible but not auto-running)
    print("\n[OPTIONAL] AccountCreator available via Ghost module")
    # Access via: ghost.get_account_creator() when needed
    
    print("\n" + "=" * 60)
    print("All modules initialized successfully!")
    print("=" * 60)


def check_and_rotate_session():
    """
    Enforce intermittent session rotation (5-25 mins).
    Closes and re-opens browser to evade detection.
    """
    global ghost, hunter, session_start_time, session_rotation_interval, active_config
    
    elapsed = time.time() - session_start_time
    if elapsed > session_rotation_interval:
        print(f"\n🔄 SESSION ROTATION TRIGGERED (Active {int(elapsed/60)}m / Limit {int(session_rotation_interval/60)}m)")
        print("   Throwing off detection algorithms...")
        
        # 1. Close Old
        try:
            ghost.close()
        except: pass
        
        
        # 2. Wait (Long Pause)
        wait_time = random.uniform(5 * 60, 25 * 60) # 5 to 25 minutes
        print(f"   Sleeping for {int(wait_time/60)} minutes to cool down...")
        print("   (This extensive pause is to evade bot detection)")
        time.sleep(wait_time)
        
        # 3. Open New
        print("   Starting Fresh Ghost Session...")
        ghost = Ghost(config=active_config)
        ghost.execute()
        
        # 4. Update References
        if hunter:
            hunter.ghost = ghost
            
        # 5. Reset Timer
        session_start_time = time.time()
        session_rotation_interval = random.randint(5 * 60, 25 * 60)
        print(f"   ✅ Session Rotated. Next swap in {int(session_rotation_interval/60)} mins.")


def run_pipeline(manual_mode=False, max_hours=None, source_filter=None):
    """
    Scheduled job that runs the entire pipeline.
    Checks rotation policy before execution.
    Args:
        manual_mode (bool): If True, bypasses some checks.
        max_hours (float): If set, filters listings by age.
        source_filter (str): If set, only scrapes URLs containing this string.
    """
    global listings_table, mongo_db, db
    # Initialize Status File for UI Progress immediately
    try:
        import json
        from pathlib import Path
        import traceback
        status_file = Path('database/scan_status.json')
        with open(status_file, 'w') as f:
            json.dump({
                'active': True,
                'status': 'Initializing...',
                'percent': 0,
                'current': 0,
                'total': 0,
                'source': source_filter or 'All',
                'updated_at': datetime.now().isoformat()
            }, f)
    except Exception as e:
        print(f"⚠️ Failed to init status file: {e}")

    try:
        check_and_rotate_session()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Starting Pipeline Run...")
    except Exception as e:
        print(f"⚠️ Session rotation warning: {e}")

    # Database selection already handled in initialize_modules()
    if listings_table is None:
        print("⚠️ Warning: listings_table not initialized. Re-initializing...")
        db = TinyDB('database/ledger.json')
        listings_table = db.table('listings')
    
    if mongo_db is not None:
        print("   💽 Using MongoDB Adapter")
    else:
        print("   📂 Using TinyDB (Local File Storage)")
    
    try:
        # === STEP 1: HUNT ===
        print("🔍 Phase 1: HUNTING")
        # Check if target URLs exist, if not, Auto-Configure
        if not active_config.get('target_urls'):
            print("   ⚠️ No target URLs found. Initiating Auto-Configuration...")
            new_url = hunter.auto_configure(active_config.get('location', {}))
            if new_url:
                active_config['target_urls'] = new_url
                # Persist if needed, or just use in memory for session
        raw_target_urls = active_config.get('target_urls', '')
        if isinstance(raw_target_urls, list):
            target_urls = [u.strip() for u in raw_target_urls if isinstance(u, str) and u.strip()]
        else:
            target_urls = [u.strip() for u in str(raw_target_urls).split(',') if u.strip()]
        target_urls = [url.strip() for url in target_urls if url.strip()]
        
        # Apply Source Filter
        if source_filter:
            print(f"   🎯 Filtering targets by source: '{source_filter}'")
            target_urls = [url for url in target_urls if source_filter.lower() in url.lower()]

        if not target_urls:
            print("⚠️ No target URLs configured (or none matched source filter).")
            return
            
        # --- BATCH TRACKING (HURRICANE PROTOCOL) ---
        hurricane_names = [
            "Arthur", "Bertha", "Cristobal", "Dolly", "Edouard", "Fay", "Gustav", 
            "Hanna", "Ike", "Josephine", "Kyle", "Laura", "Marco", "Nana", "Omar", 
            "Paloma", "Rene", "Sally", "Teddy", "Vicky", "Wilfred"
        ]
        # Simple rotation based on hour of day or random
        import random
        batch_name = f"Batch {random.choice(hurricane_names)}-{datetime.now().strftime('%H%M')}"
        batch_id = datetime.now().strftime('%Y%m%d%H%M%S')
        print(f"🌪️ Starting {batch_name} (ID: {batch_id})")
        
        # Use Hunter's execute method with batch info
        # Hunter must accept batch_id/name and tag listings
        raw_listings = hunter.execute(target_urls, max_hours=max_hours)
        
        # Inject Batch Info into listings before vetting
        for l in raw_listings:
            l['batch_id'] = batch_id
            l['batch_name'] = batch_name
        
        if not raw_listings:
            print("⚠️  No listings found.")
            return
        
        # === STEP 2: VET ===
        print("\n✓ STEP 2: Vetting and scoring listings...")
        processed_listings = vetter.execute(raw_listings)
        
        if not processed_listings:
            print("⚠️  No listings passed vetting.")
            return
        
        # Step 3: Save to database
        print("\n💾 STEP 3: Saving approved listings to database...")
        for listing in processed_listings:
            # Add timestamp and default status
            listing['processed_at'] = datetime.now().isoformat()
            if 'status' not in listing:
                listing['status'] = 'active'
                
            # Calculate absolute listed_at time
            hours_ago = listing.get('hours_since_listed')
            if hours_ago is not None:
                try:
                    listed_dt = datetime.now() - timedelta(hours=float(hours_ago))
                    listing['listed_at'] = listed_dt.isoformat()
                except:
                    listing['listed_at'] = listing['processed_at']
            else:
                listing['listed_at'] = listing['processed_at']
            
            # Normalize URL for deduplication (strip query params)
            raw_url = listing.get('listing_url', '')
            clean_url = raw_url.split('?')[0] if raw_url else ''
            listing['listing_url'] = clean_url  # Save clean URL
            
            # Check if listing already exists (by partial URL match)
            # Support both TinyDB and our MongoAdapter
            existing_results = []
            
            if hasattr(listings_table, 'get_by_url'):
                 existing_results = listings_table.get_by_url(clean_url)
            else:
                 # Fallback for standard TinyDB
                 Listing = Query()
                 existing_results = listings_table.search(Listing.listing_url == clean_url)
            
            if not existing_results:
                # Add 'batch_history' field
                listing['batch_history'] = [{
                    'batch_id': listing.get('batch_id'), 
                    'batch_name': listing.get('batch_name'),
                    'price': listing.get('price')
                }]
                listings_table.insert(listing)
                print(f"  ✓ Saved (New): {listing.get('title', 'Unknown')}")
            else:
                # Update existing listing
                existing_item = existing_results[0]
                history = existing_item.get('batch_history', [])
                
                current_batch_id = listing.get('batch_id')
                if not any(h.get('batch_id') == current_batch_id for h in history):
                    history.append({
                        'batch_id': current_batch_id, 
                        'batch_name': listing.get('batch_name'),
                        'price': listing.get('price')
                    })
                
                update_data = {
                    'price': listing.get('price'),
                    'score': listing.get('score'),
                    'last_seen': datetime.now().isoformat(),
                    'batch_id': current_batch_id,
                    'batch_name': listing.get('batch_name'),
                    'batch_history': history
                }
                
                if hasattr(listings_table, 'update_by_url'):
                    listings_table.update_by_url(clean_url, update_data)
                else:
                    listings_table.update(update_data, Listing.listing_url == clean_url)
                    
                print(f"  ↻ Updated: {listing.get('title', 'Unknown')} (Seen in {len(history)+1} batches)")
        
        # Step 4: Herald sends notifications
        print("\n📢 STEP 4: Processing notifications...")
        herald.execute(processed_listings)
        
    finally:
        # DB closure is now handled globally in main() finally block to support scheduling
        pass


def send_daily_digest():
    """
    Send the daily digest email and clear the digest.
    This function is called by the scheduler at midnight.
    """
    print("\n" + "=" * 60)
    print(f"📧 DAILY DIGEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        digest_count = len(herald.get_daily_digest())
        
        if digest_count > 0:
            print(f"\n📨 Sending daily digest email with {digest_count} listings...")
            success = herald.send_daily_digest_email()
            
            if success:
                print("✅ Daily digest email sent successfully!")
                herald.clear_daily_digest()
            else:
                print("⚠️  Failed to send daily digest email")
        else:
            print("ℹ️  Daily digest is empty, no email to send")
            
    except Exception as e:
        print(f"\n❌ Error sending daily digest: {e}")
        import traceback
        traceback.print_exc()


def run_social_activity():
    """
    Run random social activity to simulate human behavior.
    This function is called by the scheduler at random intervals.
    """
    print("\n" + "=" * 60)
    print(f"🎭 SOCIAL ACTIVITY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        if ghost:
            print("\n🤖 Running random social activity for human-like behavior...")
            success = ghost.run_random_social_activity()
            
            if success:
                print("✅ Social activity completed successfully!")
            else:
                print("⚠️  Social activity did not complete")
                
    except Exception as e:
        print(f"\n❌ Error running social activity: {e}")
        import traceback
        traceback.print_exc()


def schedule_next_social_activity():
    """
    Schedule the next social activity at a random interval (1-4 hours).
    This simulates unpredictable human behavior.
    """
    import random
    
    # Random interval between 1 and 4 hours
    hours = random.uniform(1, 4)
    minutes = int(hours * 60)
    
    # Schedule the next run
    schedule.every(minutes).minutes.do(run_social_activity).tag('social')
    
    print(f"📅 Next social activity scheduled in {hours:.1f} hours")


def create_facebook_account(first_name, last_name, email, password, phone_number):
    """
    Create a new Facebook account using the AccountCreator.
    This function should be called manually or from a separate script.
    
    Args:
        first_name: First name for the account
        last_name: Last name for the account
        email: Email address
        password: Password
        phone_number: Phone number for verification
        
    Returns:
        bool: True if account creation initiated successfully
    """
    print("\n" + "=" * 60)
    print(f"🎭 ACCOUNT CREATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        if not ghost:
            print("⚠️  Ghost module not initialized. Please run initialize_modules() first.")
            return False
        
        # Get AccountCreator from Ghost
        creator = ghost.get_account_creator()
        
        print(f"\n🔨 Creating account for {first_name} {last_name}...")
        success = creator.create_account(first_name, last_name, email, password, phone_number)
        
        if success:
            print("✅ Account creation initiated! Check for verification code.")
            print("💡 To verify: call verify_phone_number(code) with the SMS code you receive")
            return True
        else:
            print("❌ Account creation failed")
            return False
            
    except Exception as e:
        print(f"\\n❌ Error creating account: {e}")
        import traceback
        traceback.print_exc()
        return False



def main():
    """

    Main execution function with scheduler.
    Runs the pipeline every 10 minutes and sends daily digest at midnight.
    Also runs random social activity to simulate human behavior.
    """
    # Initialize all modules
    initialize_modules()
    # CLI flags
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--once', action='store_true', help='Run pipeline once and exit (no scheduler loop).')
    parser.add_argument('--manual', action='store_true', help='Indicate a manual run.')
    parser.add_argument('--hours', type=float, default=None, help='Filter by hours since listed.')
    parser.add_argument('--source', type=str, default=None, help='Filter by source (facebook or craigslist).')
    args, _ = parser.parse_known_args()

    
    if args.once or args.manual:
        print(f"\n🚀 Running one-shot pipeline (Manual: {args.manual}, Max Hours: {args.hours}, Source: {args.source})...")
        run_pipeline(manual_mode=args.manual, max_hours=args.hours, source_filter=args.source)
        return

    # Schedule the pipeline to run every 10 minutes
    # We define a wrapper to check the auto-run flag
    def scheduled_job():
        # Check settings for auto-run flag
        try:
            settings_path = Path("database/settings.json")
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    if not settings.get('auto_scrape_enabled', True):
                        print("\n⏸️  Auto-run skipped (Disabled in Settings)")
                        return
        except Exception:
            pass # Default to running if check fails
            
        run_pipeline()

    schedule.every(10).minutes.do(scheduled_job)
    
    # Schedule the daily digest to run at midnight
    schedule.every().day.at("00:00").do(send_daily_digest)
    
    # Schedule the first social activity at a random interval
    schedule_next_social_activity()
    
    print("\n📅 SCHEDULER STARTED")
    print("=" * 60)
    print("⏰ Pipeline runs every 10 minutes (if enabled)")
    print("📧 Daily digest email sent at midnight")
    print("🎭 Social activity runs at random intervals (1-4 hours)")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Run pipeline immediately on startup ONLY if not disabled
    # (Optional: or just wait for first schedule. Let's run once to be safe, 
    # but check flag first)
    print("\n🚀 Checking initial pipeline run...")
    scheduled_job()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            
            # After a social activity runs, clear it and schedule the next one
            if not schedule.get_jobs('social'):
                schedule_next_social_activity()
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if ghost:
            ghost.close()
        if db:
            db.close()
        print("✓ Cleanup complete")
        print("\n" + "=" * 60)
        print("Barnfind execution complete!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # WRITE ERROR TO STATUS FILE SO UI SEES IT
        try:
            import json
            from pathlib import Path
            from datetime import datetime
            status_file = Path('database/scan_status.json')
            with open(status_file, 'w') as f:
                json.dump({
                    'active': False,
                    'status': f"Error: {str(e)}", 
                    'percent': 0,
                    'updated_at': datetime.now().isoformat()
                }, f)
        except:
             pass
