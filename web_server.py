#!/usr/bin/env python3
"""
Barndoor Web Server
Flask backend for the modern Material Design interface.
"""
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from werkzeug.utils import secure_filename
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import certifi

load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'barndoor-secret-key-change-this'

PROJECT_DIR = Path(__file__).parent
# DB_PATH = PROJECT_DIR / "database" / "ledger.json" # Legacy
SETTINGS_PATH = PROJECT_DIR / "database" / "settings.json"
USERS_PATH = PROJECT_DIR / "database" / "users.json"
LOG_PATH = PROJECT_DIR / "barnfind.log"
PID_FILE = PROJECT_DIR / "barnfind.pid"

# MongoDB Connection
MONGO_URI = os.getenv('MONGO_URI')
mongo_client = None
mongo_db = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        mongo_db = mongo_client['barndoor']
        # Send a ping to confirm a successful connection
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB!")
    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")


def get_users():
    if not USERS_PATH.exists():
        return {"users": []}
    with open(USERS_PATH, 'r') as f:
        return json.load(f)

def save_users(users_data):
    with open(USERS_PATH, 'w') as f:
        json.dump(users_data, f, indent=4)


def is_service_running():
    """Check if the Barndoor service is running."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        result = subprocess.run(['ps', '-p', str(pid)], capture_output=True)
        return result.returncode == 0
    except:
        return False


def send_email(to_email, subject, content):
    """Send email via SendGrid."""
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key or api_key == 'your_sendgrid_api_key_here':
        print(f"MOCK EMAIL to {to_email}: [{subject}] {content}")
        return True

    message = Mail(
        from_email='noreply@barndoor.me',
        to_emails=to_email,
        subject=subject,
        html_content=content)
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


@app.route('/api/ops/seed_db')
def seed_database():
    """Seeds MongoDB with data from the local ledger.json file."""
    try:
        # Define path explicitly since it might be commented out globally
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        
        if not local_db_path.exists():
            return jsonify({'error': 'Local ledger.json not found'}), 404
            
        if mongo_db is None:
             return jsonify({'error': 'No MongoDB connection'}), 500

        with open(local_db_path, 'r') as f:
            data = json.load(f)
            
        listings_map = data.get('listings', {})
        count = 0
        
        for doc_id, listing in listings_map.items():
            # Inject string ID
            listing['original_id'] = str(doc_id)
            if 'status' not in listing:
                listing['status'] = 'active'
            
            # Upsert based on original_id or URL to prevent duplicates
            mongo_db.listings.replace_one(
                {'original_id': str(doc_id)},
                listing,
                upsert=True
            )
            count += 1
            
        return jsonify({'success': True, 'count': count, 'message': f'Seeded {count} listings to MongoDB'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form.get('username')
        pw = request.form.get('password')
        
        users_data = get_users()
        user = next((u for u in users_data['users'] if u['email'] == email), None)
        
        if user and user['password'] == pw: # Note: In production use hashing
            if user['status'] != 'approved':
                return render_template('login.html', error="Your account is pending approval.")
            
            session['logged_in'] = True
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user access requests."""
    if request.method == 'POST':
        email = request.form.get('email')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Default name from email since we removed the field
        full_name = email.split('@')[0].title()
        
        users_data = get_users()
        if any(u['email'] == email for u in users_data['users']):
            return render_template('login.html', error="Email already registered", signup_mode=True)
        
        new_user = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": "user",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        users_data['users'].append(new_user)
        save_users(users_data)
        
        # send_email confirmation to user
        subject = "Thank you for your interest in Barndoor"
        content = """
        <p>Thank you for your interest in Barndoor, the premium classic car finder across the heartland.</p>
        <p>Your request has been added to our waiting list. Our team will review your request and get back to you at our soonest availability.</p>
        <p>Thank you</p>
        """
        send_email(email, subject, content)
        
        return render_template('login.html', message="Request submitted! We will review and get back to you.")
    
    return render_template('login.html', signup_mode=True)


@app.route('/admin/users')
def users_admin():
    """Serve the user management interface."""
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('users_admin.html')


@app.route('/api/users')
def list_users():
    """List all users for admin."""
    if not session.get('logged_in') or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(get_users())


@app.route('/api/users/status', methods=['POST'])
def update_user_status():
    """Approve or deny a user request."""
    if not session.get('logged_in') or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    email = data.get('email')
    status = data.get('status')
    
    users_data = get_users()
    user = next((u for u in users_data['users'] if u['email'] == email), None)
    
    if user:
        user['status'] = status
        save_users(users_data)
        
        # Send notification email
        if status == 'approved':
            subject = "Access Granted - Barndoor"
            content = f"<p>Hello {user['full_name']},</p><p>We are happy to inform you that your request for access to Barndoor has been approved. You can now log in to your profile.</p>"
        else:
            subject = "Update regarding your Barndoor request"
            content = f"<p>Hello {user['full_name']},</p><p>Thank you for your interest in Barndoor. At this time, we are unable to grant you access to the platform.</p>"
            
        send_email(email, subject, content)
        return jsonify({'success': True})
    
    return jsonify({'error': 'User not found'}), 404


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    """Serve the main interface."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html', mode='active')


@app.route('/settings')
def settings_page():
    """Serve the settings interface."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('settings.html')


@app.route('/portal')
def portal_page():
    """Serve the Access Portal iframe."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('portal.html')


@app.route('/profile')
def profile_page():
    """Serve the user profile interface."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('profile.html')


@app.route('/api/auth/forgot', methods=['POST'])
def request_password_reset():
    """Handle forgot password requests."""
    email = request.json.get('email')
    
    users_data = get_users()
    user = next((u for u in users_data['users'] if u['email'] == email), None)
    
    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'success': True})
        
    # Generate 6 digit code
    import random
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Save code and expiry (15 mins)
    user['reset_token'] = code
    # Store timestamp as ISO string
    user['reset_expires'] = (datetime.now().timestamp() + 900) 
    save_users(users_data)
    
    # Send email
    subject = "Password Reset Code - Barndoor"
    content = f"""
    <p>Hello,</p>
    <p>You requested to reset your password. Use the code below to complete the process:</p>
    <h2 style="font-size: 24px; letter-spacing: 5px; background: #eee; padding: 10px; display: inline-block;">{code}</h2>
    <p>This code expires in 15 minutes.</p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    send_email(email, subject, content)
    
    return jsonify({'success': True})


@app.route('/api/auth/reset', methods=['POST'])
def reset_password_confirm():
    """Verify code and reset password."""
    data = request.json
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('password')
    
    users_data = get_users()
    user = next((u for u in users_data['users'] if u['email'] == email), None)
    
    if not user:
        return jsonify({'error': 'Invalid request'}), 400
        
    # Check token
    stored_token = user.get('reset_token')
    expires = user.get('reset_expires', 0)
    
    if not stored_token or stored_token != code:
        return jsonify({'error': 'Invalid code'}), 400
        
    if datetime.now().timestamp() > expires:
        return jsonify({'error': 'Code expired'}), 400
        
    # Update password
    user['password'] = new_password
    # Clear token
    del user['reset_token']
    del user['reset_expires']
    
    save_users(users_data)
    
    return jsonify({'success': True})


@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    """Update user profile information."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    email = data.get('email')
    full_name = data.get('full_name')
    new_password = data.get('password')
    
    users_data = get_users()
    user_email = session.get('user_email')
    user = next((u for u in users_data['users'] if u['email'] == user_email), None)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    # Check if new email is already taken by someone else
    if email and email != user_email:
        if any(u['email'] == email for u in users_data['users']):
            return jsonify({'error': 'Email already in use'}), 400
        user['email'] = email
        session['user_email'] = email # update session
        
    if full_name:
        user['full_name'] = full_name
        session['user_name'] = full_name # update session
        
    if new_password:
        user['password'] = new_password
        
    save_users(users_data)
    return jsonify({'success': True})


@app.route('/api/status')
def get_status():
    """Get current service status and statistics."""
    try:
        running = is_service_running()
        
        # Get statistics
        stats = {
            'total_listings': 0,
            'last_run': 'Never',
            'status': 'running' if running else 'stopped'
        }
        
        if mongo_db is not None:
             stats['total_listings'] = mongo_db.listings.count_documents({})
        
        # Get last run from logs
        if LOG_PATH.exists():
            with open(LOG_PATH, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-100:]):
                    if "PIPELINE RUN" in line:
                        try:
                            timestamp = line.split("PIPELINE RUN - ")[1].strip()
                            stats['last_run'] = timestamp
                        except:
                            pass
                        break
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update deal quality settings."""
    if request.method == 'POST':
        try:
            updates = request.json
            current_settings = {}
            
            # Load existing
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r') as f:
                    try:
                        current_settings = json.load(f)
                    except:
                        pass # Corrupt file, start fresh
            
            # Merge updates
            current_settings.update(updates)
            
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(current_settings, f, indent=4)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET request
    try:
        if not SETTINGS_PATH.exists():
            # Return defaults if file doesn't exist
            # (In a real app, maybe creating the file here is better, 
            # but we created it manually in the task step)
            return jsonify({}) 
        
        with open(SETTINGS_PATH, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs')
def get_logs():
    """Get recent logs."""
    try:
        if not LOG_PATH.exists():
            return jsonify({'logs': 'No logs yet - start the service to begin'})
        
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
            recent = ''.join(lines[-100:])
        
        return jsonify({'logs': recent})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
def start_service():
    """Start the Barndoor service."""
    try:
        if is_service_running():
            return jsonify({'error': 'Service already running'}), 400
        
        process = subprocess.Popen(
            ['python3', 'main.py'],
            cwd=str(PROJECT_DIR),
            stdout=open(LOG_PATH, 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        return jsonify({'success': True, 'message': 'Service started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_service():
    """Stop the Barndoor service."""
    try:
        if not PID_FILE.exists():
            return jsonify({'error': 'Service not running'}), 400
        
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        subprocess.run(['kill', str(pid)])
        PID_FILE.unlink()
        
        return jsonify({'success': True, 'message': 'Service stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/tickle')
def tickle_page():
    """Serve the Tickle Sheet interface using the Dashboard layout."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html', mode='tickle')


@app.route('/api/listings')
def get_listings():
    """Get listings filtered by status from MongoDB."""
    status_filter = request.args.get('status')
    
    try:
        # 1. MongoDB Strategy
        if mongo_db is not None:
            query = {}
            if status_filter:
                query['status'] = status_filter
                
            cursor = mongo_db.listings.find(query)
            
            results = []
            for doc in cursor:
                doc['id'] = str(doc['_id'])
                del doc['_id']
                if 'status' not in doc: doc['status'] = 'active'
                results.append(doc)
            return jsonify({'listings': results, 'total': len(results)})

        # 2. Local Ledger Strategy (Fallback)
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        if local_db_path.exists():
            with open(local_db_path, 'r') as f:
                data = json.load(f)
            
            # TinyDB structure: {"listings": {"ID": {...}, "ID": {...}}}
            listings_map = data.get('listings', {})
            results = []
            
            for doc_id, listing in listings_map.items():
                listing['id'] = str(doc_id)
                # Default status to 'active' if missing
                if 'status' not in listing:
                    listing['status'] = 'active'
                
                # Filter by status if requested
                if status_filter:
                   if listing['status'] != status_filter:
                       continue
                
                results.append(listing)
                
            return jsonify({'listings': results, 'total': len(results)})
            
        return jsonify({'listings': [], 'total': 0})

    except Exception as e:
        print(f"Error serving listings: {e}") 
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/delete', methods=['POST'])
def delete_listings():
    """Bulk soft-delete listings by ID or URL (MongoDB)."""
    try:
        payload = request.json
        ids_to_delete = payload.get('ids', []) 
        
        if not ids_to_delete:
             return jsonify({'success': True, 'count': 0})
             
        if mongo_db is None:
             return jsonify({'error': 'No Database Connection'}), 500
        
        deleted_count = 0
        
        for identifier in ids_to_delete:
            id_str = str(identifier)
            res = None
            
            # 1. Try by ObjectId
            if ObjectId.is_valid(id_str):
                res = mongo_db.listings.update_one(
                    {'_id': ObjectId(id_str)},
                    {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                )
            
            # 2. Try by 'original_id' (legacy migration ID)
            if not res or res.modified_count == 0:
                 res = mongo_db.listings.update_one(
                     {'original_id': id_str},
                     {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                 )
                 
            # 3. Try by URL fallback
            if not res or res.modified_count == 0:
                res = mongo_db.listings.update_one(
                    {'listing_url': id_str},
                    {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                )
            
            if res and res.modified_count > 0:
                deleted_count += 1
        
        return jsonify({'success': True, 'count': deleted_count})
            
    except Exception as e:
        print(f"Error deleting listings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/bulk_status', methods=['POST'])
def bulk_update_status():
    """Update status for multiple listings by ID (MongoDB)."""
    try:
        payload = request.json
        ids_to_update = payload.get('ids', [])
        new_status = payload.get('status')
        
        if not ids_to_update or not new_status:
            return jsonify({'success': True, 'count': 0})
            
        if mongo_db is None:
             return jsonify({'error': 'No Database Connection'}), 500
             
        updated_count = 0
        
        update_data = {'status': new_status}
        if new_status == 'tickle':
            update_data['tickle_at'] = datetime.now().isoformat()
            
        for id_str in ids_to_update:
             res = None
             # Try ObjectId
             if ObjectId.is_valid(id_str):
                 res = mongo_db.listings.update_one(
                     {'_id': ObjectId(id_str)},
                     {'$set': update_data}
                 )
            
             # Try original_id
             if not res or res.modified_count == 0:
                 res = mongo_db.listings.update_one(
                     {'original_id': str(id_str)},
                     {'$set': update_data}
                 )
                 
             if res and res.modified_count > 0:
                 updated_count += 1
        
        return jsonify({'success': True, 'count': updated_count})
            
    except Exception as e:
        print(f"Error bulk updating listings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ops/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger a manual scrape with optional parameters."""
    try:
        data = request.json or {}
        hours = data.get('hours')
        source = data.get('source')
        
        # Command construction
        cmd = ["python3", "-u", "main.py", "--manual"]
        if hours:
            cmd.extend(["--hours", str(hours)])
        if source:
            cmd.extend(["--source", str(source)])
            
        print(f"🚀 Triggering Manual Scrape: {' '.join(cmd)}")
        
        print(f"🚀 Triggering Manual Scrape: {' '.join(cmd)}")
        
        # Run in background.
        # We use None for stdout/stderr to inherit from parent (Flask app),
        # so output shows up in Railway logs.
        subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR)
        )
        
        return jsonify({
            'success': True, 
            'message': f"Started manual scrape (Freshness: {hours or 'All'} hours, Source: {source or 'All'})"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/update_status', methods=['POST'])
def update_status():
    """Update listing status (archive, sold, deleted) via URL (MongoDB)."""
    try:
        payload = request.json
        url = payload.get('url')
        new_status = payload.get('status')
        
        if mongo_db is None:
             return jsonify({'error': 'No Database Connection'}), 500
            
        update_data = {'status': new_status}
        if new_status == 'tickle': # User requested "Tickle File"
            update_data['tickle_at'] = datetime.now().isoformat()

        res = mongo_db.listings.update_one(
            {'listing_url': url},
            {'$set': update_data}
        )
        
        if res.modified_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Listing not found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications')
def get_notifications():
    """Check for due tickle reminders and return details (MongoDB)."""
    try:
        if mongo_db is None:
            return jsonify({'count': 0, 'items': []})
            
        # Find listings with status 'tickle'
        cursor = mongo_db.listings.find({'status': 'tickle'})
        
        due_items = []
        now = datetime.now()
        
        for listing in cursor:
            if listing.get('tickle_at'):
                try:
                    tickle_date = datetime.fromisoformat(listing['tickle_at'])
                    # Check if exactly one week (7 days) has passed
                    if (now - tickle_date).days >= 7:
                        due_items.append({
                            'title': listing.get('title', 'Unknown Vehicle'),
                            'location': listing.get('location', 'Unknown Location'),
                            'url': listing.get('listing_url'),
                            'tickle_at': listing.get('tickle_at')
                        })
                except:
                    continue
                        
        return jsonify({'count': len(due_items), 'items': due_items})
                        
        return jsonify({'count': len(due_items), 'items': due_items})
    except Exception as e:
        print(f"Notification error: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/veterans')
def veterans_page():
    """Serve the Veteran Buying Page."""
    return render_template('veterans.html')


@app.route('/api/submit_veteran_vehicle', methods=['POST'])
def submit_veteran_vehicle():
    """Handle vehicle submissions from veterans."""
    try:
        data = request.form.to_dict()
        files = request.files.getlist('photos')
        
        # Log submission
        app.logger.info(f"Veteran submission: {data}")
        
        # Save photos
        upload_folder = PROJECT_DIR / "uploads" / "veterans"
        os.makedirs(upload_folder, exist_ok=True)
        saved_files = []
        

        # Handle Competitor Offer Photo
        offer_file = request.files.get('offer_photo')
        offer_path = None
        if offer_file and offer_file.filename:
            filename = secure_filename(offer_file.filename)
            ts = int(datetime.now().timestamp())
            filename = f"{ts}_OFFER_{filename}"
            save_path = upload_folder / filename
            offer_file.save(save_path)
            offer_path = str(save_path)

        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Add timestamp to avoid collisions
                ts = int(datetime.now().timestamp())
                filename = f"{ts}_{filename}"
                save_path = upload_folder / filename
                file.save(save_path)
                saved_files.append(str(save_path))
        
        # Send Alert Email to Admin (Mock Admin Email)
        admin_email = "admin@barndoor.me" 
        subject = f"🎖 Veteran Vehicle: {data.get('year')} {data.get('make')} {data.get('model')}"
        
        has_offer = "YES" if offer_path else "NO"
        
        content = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #33691e;">New Veteran Vehicle Submission</h2>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Vehicle Details</h3>
                <p><strong>Vehicle:</strong> {data.get('year')} {data.get('make')} {data.get('model')}</p>
                <p><strong>Mileage:</strong> {data.get('mileage')}</p>
                <p><strong>Color:</strong> {data.get('color')}</p>
                <p><strong>Condition:</strong> {data.get('condition')}/10</p>
                <p><strong>Photos Uploaded:</strong> {len(saved_files)}</p>
                <p><strong>Competitor Offer Attached:</strong> {has_offer}</p>
            </div>
            
            <div style="background: #e8f5e9; padding: 15px; border-radius: 5px;">
                <h3 style="margin-top: 0;">Veteran Contact</h3>
                <p><strong>Name:</strong> {data.get('owner_name')}</p>
                <p><strong>Email:</strong> {data.get('owner_email')}</p>
                <p><strong>Phone:</strong> {data.get('owner_phone')}</p>
            </div>
        </div>
        """
        send_email(admin_email, subject, content)
        
        # Send Confirmation to Veteran
        vet_subject = "We received your vehicle submission - Barndoor"
        vet_content = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #333;">
            <h2>Submission Received</h2>
            <p>Dear {data.get('owner_name')},</p>
            <p>We have received your submission for the <strong>{data.get('year')} {data.get('make')} {data.get('model')}</strong>.</p>
            <p>Our team is currently reviewing the details against our buying criteria. If your vehicle matches what we are looking for, we will reach out to you shortly with our guaranteed offer.</p>
            <br>
            <p>Thank you for your service.</p>
            <p>The Barndoor Team</p>
        </div>
        """
        send_email(data.get('owner_email'), vet_subject, vet_content)
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        app.logger.error(f"Error submitting veteran form: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ops/progress', methods=['GET'])
def get_scan_progress():
    """Get current scan progress."""
    try:
        status_file = PROJECT_DIR / 'database' / 'scan_status.json'
        if status_file.exists():
            with open(status_file, 'r') as f:
                data = json.load(f)
            
            # Check if stale (> 10 mins old)
            updated = datetime.fromisoformat(data.get('updated_at'))
            if (datetime.now() - updated).total_seconds() > 600:
                data['active'] = False
                data['status'] = "Idle (Stale)"
            
            return jsonify(data)
        else:
            return jsonify({'active': False, 'status': 'Idle', 'percent': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    # Ensure database dir exists
    (PROJECT_DIR / 'database').mkdir(exist_ok=True)
    
    # Run the server
    print("🚗 Barndoor Web Server")
    print("=" * 50)

    # Use the PORT environment variable provided by Railway/Render
    # Default to 5050 for local development
    port = int(os.environ.get("PORT", 5050))
    
    # Only open browser if running locally (not in cloud)
    if not os.environ.get('RAILWAY_ENVIRONMENT') and not os.environ.get('DYNO'):
        print("Opening in browser...")
        import webbrowser
        import threading
        
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{port}')
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask
    # bind to 0.0.0.0 to ensure external access in Docker/Railway
    app.run(host='0.0.0.0', port=port, debug=False)
