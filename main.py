"""
Main execution script for the Barnfind data processing application.
Orchestrates the Hunter, Vetter, Ghost, and Herald modules for automated vehicle market analysis.
Runs on a schedule: every 10 minutes for pipeline execution, midnight for daily digest.
"""
from modules import Hunter, Vetter, Ghost, Herald
from tinydb import TinyDB, Query
from database.config_db import ConfigDB
from datetime import datetime
import schedule
import time
import sys
import random


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


def initialize_modules():
    """
    Initialize all modules and database connections.
    Called once at startup.
    """
    global db, listings_table, ghost, hunter, vetter, herald, account_creator, active_config
    
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
        
    print(f"   ✅ Loaded Profile: {active_config.get('profile_name')}")
    
    # Initialize database
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


def run_pipeline():
    """
    Scheduled job that runs the entire pipeline.
    Checks rotation policy before execution.
    """
    check_and_rotate_session()
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Starting Pipeline Run...")
    
    # Initialize database locally to ensure fresh read/write (avoid cache issues with web server)
    db = TinyDB('database/ledger.json')
    listings_table = db.table('listings')
    
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
            
        target_urls = active_config.get('target_urls', '').split(',')
        target_urls = [url.strip() for url in target_urls if url.strip()]
        
        if not target_urls:
            print("⚠️ No target URLs configured in active profile.")
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
        raw_listings = hunter.execute(target_urls)
        
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
            # Add timestamp
            listing['processed_at'] = datetime.now().isoformat()
            
            # Normalize URL for deduplication (strip query params)
            raw_url = listing.get('listing_url', '')
            clean_url = raw_url.split('?')[0] if raw_url else ''
            listing['listing_url'] = clean_url  # Save clean URL
            
            # Check if listing already exists (by partial URL match)
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
                print(f"  ✓ Saved: {listing.get('title', 'Unknown')}")
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
                
                listings_table.update(update_data, Listing.listing_url == clean_url)
                print(f"  ↻ Updated: {listing.get('title', 'Unknown')} (Seen in {len(history)+1} batches)")
        
        # Step 4: Herald sends notifications
        print("\n📢 STEP 4: Processing notifications...")
        herald.execute(processed_listings)
        
    finally:
        db.close()
        print("   🔒 DB Closed for this run.")


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
    
    # Schedule the pipeline to run every 10 minutes
    schedule.every(10).minutes.do(run_pipeline)
    
    # Schedule the daily digest to run at midnight
    schedule.every().day.at("00:00").do(send_daily_digest)
    
    # Schedule the first social activity at a random interval
    schedule_next_social_activity()
    
    print("\n📅 SCHEDULER STARTED")
    print("=" * 60)
    print("⏰ Pipeline runs every 10 minutes")
    print("📧 Daily digest email sent at midnight")
    print("🎭 Social activity runs at random intervals (1-4 hours)")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Run pipeline immediately on startup
    print("\n🚀 Running initial pipeline...")
    run_pipeline()
    
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
    main()
