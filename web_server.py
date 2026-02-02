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
import requests

load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'barndoor-secret-key-change-this'

PROJECT_DIR = Path(__file__).parent
# DB_PATH = PROJECT_DIR / "database" / "ledger.json" # Legacy
SETTINGS_PATH = PROJECT_DIR / "database" / "settings.json"
USERS_PATH = PROJECT_DIR / "database" / "users.json"
PROFILES_PATH = PROJECT_DIR / "database" / "profiles.json"
LOG_PATH = PROJECT_DIR / "barnfind.log"
PID_FILE = PROJECT_DIR / "barnfind.pid"

# Database Configuration
try:
    # Get MongoDB URI from environment (supports Vercel's MONGO_URI and Railway's MONGO_URL)
    mongo_uri = os.getenv('MONGO_URI') or os.getenv('MONGO_URL')
    
    if not mongo_uri:
        # Fallback for local dev if .env is missing
        mongo_uri = "mongodb://localhost:27017/"
        print("⚠️  MONGO_URI not set, using localhost default")
        
    client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
    # Connect to 'barnfind' database
    db = client['barnfind']
    print(f"✅ Connected to MongoDB: {mongo_uri.split('@')[-1] if '@' in mongo_uri else 'localhost'}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    # Initialize dummy db/collection for avoiding crash on import, but auth will fail
    client = None
    db = None


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



# --- Profile Management Helpers ---
def get_profiles_data():
    if not PROFILES_PATH.exists():
        return {"profiles": [], "active_profile_id": None}
    try:
        with open(PROFILES_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"profiles": [], "active_profile_id": None}

def save_profiles_data(data):
    with open(PROFILES_PATH, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/api/profiles', methods=['GET'])
def list_profiles():
    """List all Facebook profiles."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_profiles_data())


@app.route('/api/profiles/add', methods=['POST'])
def add_profile():
    """Add a new Facebook profile."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    profiles_data = get_profiles_data()
    
    # Check duplicate
    if any(p['username'] == username for p in profiles_data['profiles']):
        return jsonify({'error': 'Profile already exists'}), 400
    
    # Create simple ID
    import uuid
    new_id = str(uuid.uuid4())[:8]
    
    new_profile = {
        "id": new_id,
        "username": username,
        "password": password,
        "added_at": datetime.now().isoformat()
    }
    
    profiles_data['profiles'].append(new_profile)
    
    # If first profile, auto-activate
    if not profiles_data['active_profile_id']:
        profiles_data['active_profile_id'] = new_id
        
    save_profiles_data(profiles_data)
    
    return jsonify({'success': True, 'profile': new_profile})


@app.route('/api/profiles/delete', methods=['POST'])
def delete_profile():
    """Delete a Facebook profile."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    profile_id = request.json.get('id')
    profiles_data = get_profiles_data()
    
    initial_count = len(profiles_data['profiles'])
    profiles_data['profiles'] = [p for p in profiles_data['profiles'] if p['id'] != profile_id]
    
    if len(profiles_data['profiles']) < initial_count:
        # If we deleted the active one, reset active
        if profiles_data['active_profile_id'] == profile_id:
             profiles_data['active_profile_id'] = None
             if profiles_data['profiles']:
                 # Auto-activate next available
                 profiles_data['active_profile_id'] = profiles_data['profiles'][0]['id']
                 
        save_profiles_data(profiles_data)
        return jsonify({'success': True})
        
    return jsonify({'error': 'Profile not found'}), 404


@app.route('/api/profiles/activate', methods=['POST'])
def activate_profile():
    """Set the active Facebook profile."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    profile_id = request.json.get('id')
    profiles_data = get_profiles_data()
    
    # Validate exist
    if not any(p['id'] == profile_id for p in profiles_data['profiles']):
        return jsonify({'error': 'Profile not found'}), 404
        
    profiles_data['active_profile_id'] = profile_id
    save_profiles_data(profiles_data)
    
    return jsonify({'success': True})


# --- PROXY MANAGEMENT ---
PROXY_HISTORY_PATH = PROJECT_DIR / "database" / "proxy_history.json"

def get_proxy_history():
    if not PROXY_HISTORY_PATH.exists():
        return {"history": []}
    try:
        with open(PROXY_HISTORY_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"history": []}

def save_proxy_history(data):
    try:
        with open(PROXY_HISTORY_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving proxy history: {e}")

@app.route('/api/proxy/info', methods=['GET'])
def get_proxy_info():
    """Get current proxy settings and history."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Get active settings
    settings = {}
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
            
    net_conf = settings.get('network', {})
    active_mode = net_conf.get('mode', 'direct')
    proxy_user = net_conf.get('proxy_user', '')
    
    # Extract current Zip from username if present
    # Format: ...-country-us-postal-12345
    current_zip = ""
    if '-postal-' in proxy_user:
        try:
            parts = proxy_user.split('-postal-')
            if len(parts) > 1:
                current_zip = parts[1].split('-')[0]
        except: pass
        
    history = get_proxy_history().get('history', [])
    
    return jsonify({
        'enabled': active_mode == 'proxy',
        'zipcode': current_zip,
        'history': history
    })

@app.route('/api/proxy/current-ip', methods=['GET'])
def get_current_ip():
    """Get current IP address and geolocation through proxy."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Load settings to check proxy config
        settings = {}
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
        
        net_conf = settings.get('network', {})
        proxy_enabled = net_conf.get('mode') == 'proxy'
        
        # Build proxy dict if enabled
        proxies = None
        if proxy_enabled:
            proxy_user = net_conf.get('proxy_user', '')
            proxy_pass = net_conf.get('proxy_password', '')
            proxy_host = net_conf.get('proxy_host', 'brd.superproxy.io')
            proxy_port = net_conf.get('proxy_port', 33335)
            
            if proxy_user and proxy_pass:
                proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
                proxies = {'http': proxy_url, 'https': proxy_url}
        
        # Fetch IP and geolocation from ipapi.co
        response = requests.get(
            'https://ipapi.co/json/',
            proxies=proxies,
            timeout=10,
            verify=False  # Bright Data uses SSL interception
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'ip': data.get('ip'),
                'city': data.get('city'),
                'region': data.get('region'),
                'postal': data.get('postal'),
                'country': data.get('country_name'),
                'proxy_enabled': proxy_enabled
            })
        else:
            return jsonify({
                'success': False,
                'error': f'HTTP {response.status_code}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/proxy/update', methods=['POST'])
def update_proxy():
    """Update proxy settings (Zipcode & Toggle)."""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    enabled = data.get('enabled', False)
    zipcode = data.get('zipcode', '').strip()
    
    # Load settings
    settings = {}
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
    
    if 'network' not in settings: settings['network'] = {}
    
    # Toggle Mode
    settings['network']['mode'] = 'proxy' if enabled else 'direct'
    
    # Always update the configured proxy user if we have a base user string
    # This ensuring that even if disabled, the "Set" button saves the preference.
    original_user = settings['network'].get('proxy_user', '')
    
    # Fallback if settings file is new/empty
    if not original_user: 
        # try to find from env or use a placeholder that user must fix later
        # But usually setup_proxy_magic sets this.
        # If empty, we can't really "construct" it without the customer ID.
        pass

    if original_user and zipcode:
        try:
            # 1. Strip existing location suffixes
            base_part = original_user
            if '-country-' in original_user:
                base_part = original_user.split('-country-')[0]
            
            # 2. Rebuild with new zip
            new_user = f"{base_part}-country-us-postal-{zipcode}"
            settings['network']['proxy_user'] = new_user

            # 3. Update History
            hist_data = get_proxy_history()
            history = hist_data.get('history', [])
            # Remove if exists (move to top)
            if zipcode in history:
                history.remove(zipcode)
            history.insert(0, zipcode)
            # Keep max 5
            hist_data['history'] = history[:5]
            save_proxy_history(hist_data)
        except Exception as e:
            print(f"Error updating proxy history: {e}")
        
    elif original_user and not zipcode:
        # If user cleared the zip, revert to country-us only?
        # optionally handle clearing specific targeting
        pass

    # Save Settings
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    return jsonify({'success': True})


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
    """Get recent logs from the scraper."""
    try:
        # Read the actual scraper logs, not the web server logs
        scraper_log = PROJECT_DIR / "main.stdout.log"
        if not scraper_log.exists():
            return jsonify({'logs': 'No scraper logs yet - start a scan to begin'})
        
        with open(scraper_log, 'r', encoding='utf-8', errors='replace') as f:
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
        results = []
        
        # 1. Try MongoDB
        if mongo_db is not None:
            try:
                query = {}
                if status_filter:
                    query['status'] = status_filter
                cursor = mongo_db.listings.find(query)
                for doc in cursor:
                    doc['id'] = str(doc['_id'])
                    del doc['_id']
                    if 'status' not in doc: doc['status'] = 'active'
                    results.append(doc)
            except Exception as mongo_err:
                print(f"MongoDB Fetch Error: {mongo_err}")

        # 2. Try TinyDB (Always merge or fallback if MongoDB empty)
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        if local_db_path.exists():
            try:
                with open(local_db_path, 'r') as f:
                    data = json.load(f)
                
                listings_map = data.get('listings', {})
                for doc_id, listing in listings_map.items():
                    # Set ID and Default Status
                    listing['id'] = str(doc_id)
                    if 'status' not in listing:
                        listing['status'] = 'active'
                    
                    # Filter by status if requested
                    if status_filter and listing['status'] != status_filter:
                        continue
                    
                    # Avoid duplicates if already in results from MongoDB
                    if not any(r.get('listing_url') == listing.get('listing_url') for r in results):
                        results.append(listing)
            except Exception as tiny_err:
                print(f"TinyDB Fetch Error: {tiny_err}")
                
        return jsonify({'listings': results, 'total': len(results)})

    except Exception as e:
        print(f"Error serving listings: {e}") 
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/delete', methods=['POST'])
def delete_listings():
    """Bulk soft-delete listings by ID or URL (MongoDB with TinyDB fallback)."""
    try:
        payload = request.json
        ids_to_delete = payload.get('ids', []) 
        
        if not ids_to_delete:
             return jsonify({'success': True, 'count': 0})
             
        deleted_count = 0
        ids_set = set(str(i) for i in ids_to_delete)
        
        # 1. Try MongoDB
        if mongo_db is not None:
            try:
                for identifier in ids_to_delete:
                    id_str = str(identifier)
                    res = None
                    if ObjectId.is_valid(id_str):
                        res = mongo_db.listings.update_one(
                            {'_id': ObjectId(id_str)},
                            {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                        )
                    if not res or res.modified_count == 0:
                        res = mongo_db.listings.update_one(
                            {'original_id': id_str},
                            {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                        )
                    if not res or res.modified_count == 0:
                        res = mongo_db.listings.update_one(
                            {'listing_url': id_str},
                            {'$set': {'status': 'deleted', 'deleted_at': datetime.now().isoformat()}}
                        )
                    if res and res.modified_count > 0:
                        deleted_count += 1
            except Exception as mongo_err:
                print(f"MongoDB Delete Error: {mongo_err}")

        # 2. Try TinyDB (Fallback/Sync)
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        if local_db_path.exists():
            try:
                with open(local_db_path, 'r') as f:
                    data = json.load(f)
                
                listings_map = data.get('listings', {})
                tiny_deleted = 0
                for lid_str in ids_set:
                    # Match by Key
                    if lid_str in listings_map:
                        if listings_map[lid_str].get('status') != 'deleted':
                            listings_map[lid_str]['status'] = 'deleted'
                            listings_map[lid_str]['deleted_at'] = datetime.now().isoformat()
                            tiny_deleted += 1
                    else:
                        # Match by URL
                        for item_id, item in listings_map.items():
                            if item.get('listing_url') == lid_str:
                                if item.get('status') != 'deleted':
                                    item['status'] = 'deleted'
                                    item['deleted_at'] = datetime.now().isoformat()
                                    tiny_deleted += 1
                                break
                
                if tiny_deleted > 0:
                    with open(local_db_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    deleted_count = max(deleted_count, tiny_deleted) # crude way to report
            except Exception as tiny_err:
                print(f"TinyDB Delete Error: {tiny_err}")
                
        return jsonify({'success': True, 'count': deleted_count})
            
    except Exception as e:
        print(f"Error deleting listings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/bulk_status', methods=['POST'])
def bulk_update_status():
    """Update status for multiple listings by ID (MongoDB with TinyDB fallback)."""
    try:
        payload = request.json
        ids_to_update = payload.get('ids', [])
        new_status = payload.get('status')
        
        if not ids_to_update or not new_status:
            return jsonify({'success': True, 'count': 0})
            
        updated_count = 0
        ids_set = set(str(i) for i in ids_to_update)
        update_data = {'status': new_status}
        if new_status == 'tickle':
            update_data['tickle_at'] = datetime.now().isoformat()

        # 1. Try MongoDB
        if mongo_db is not None:
            try:
                for id_str in ids_to_update:
                    res = None
                    if ObjectId.is_valid(str(id_str)):
                        res = mongo_db.listings.update_one(
                            {'_id': ObjectId(str(id_str))},
                            {'$set': update_data}
                        )
                    if not res or res.modified_count == 0:
                        res = mongo_db.listings.update_one(
                            {'$or': [{'original_id': str(id_str)}, {'listing_url': str(id_str)}]},
                            {'$set': update_data}
                        )
                    if res and res.modified_count > 0:
                        updated_count += 1
            except Exception as mongo_err:
                print(f"MongoDB Bulk Update Error: {mongo_err}")

        # 2. Try TinyDB (Sync)
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        if local_db_path.exists():
            try:
                with open(local_db_path, 'r') as f:
                    data = json.load(f)
                
                listings_map = data.get('listings', {})
                tiny_updated = 0
                for lid_str in ids_set:
                    if lid_str in listings_map:
                        listings_map[lid_str].update(update_data)
                        tiny_updated += 1
                    else:
                        for item_id, item in listings_map.items():
                            if item.get('listing_url') == lid_str:
                                item.update(update_data)
                                tiny_updated += 1
                                break
                
                if tiny_updated > 0:
                    with open(local_db_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    updated_count = max(updated_count, tiny_updated)
            except Exception as tiny_err:
                print(f"TinyDB Bulk Update Error: {tiny_err}")
                
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
        
        # Command construction - USE SAFE LAUNCHER
        cmd = ["python3", "-u", "safe_launcher.py", "--manual"]
        if hours:
            cmd.extend(["--hours", str(hours)])
        if source:
            cmd.extend(["--source", str(source)])
            
        print(f"🚀 Triggering Manual Scrape via Safer Launcher: {' '.join(cmd)}")
        
        print(f"🚀 Triggering Manual Scrape: {' '.join(cmd)}")
        
        # Run in background with file logging for UI debugging
        log_path = PROJECT_DIR / 'database' / 'debug_launcher.log'
        # ensure db dir exists
        log_path.parent.mkdir(exist_ok=True)
        
        # Open in append mode (or write to clear? let's use 'w' to capture fresh run)
        log_file = open(log_path, 'w')
        
        subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            cwd=str(PROJECT_DIR)
        )
        
        return jsonify({
            'success': True, 
            'message': f"Started manual scrape (Freshness: {hours or 'All'} hours, Source: {source or 'All'})"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/log')
def get_debug_log():
    try:
        log_path = PROJECT_DIR / 'database' / 'debug_launcher.log'
        if log_path.exists():
            return log_path.read_text(encoding='utf-8', errors='replace')
        return "No debug log found."
    except Exception as e:
        return f"Error reading log: {e}"
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

        success = False
        # 1. Try MongoDB
        if mongo_db is not None:
            try:
                res = mongo_db.listings.update_one(
                    {'listing_url': url},
                    {'$set': update_data}
                )
                if res.modified_count > 0:
                    success = True
            except: pass
            
        # 2. Try TinyDB
        local_db_path = PROJECT_DIR / "database" / "ledger.json"
        if local_db_path.exists():
            try:
                with open(local_db_path, 'r') as f:
                    data = json.load(f)
                listings_map = data.get('listings', {})
                tiny_success = False
                for item_id, item in listings_map.items():
                    if item.get('listing_url') == url:
                        item.update(update_data)
                        tiny_success = True
                        break
                if tiny_success:
                    with open(local_db_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    success = True
            except: pass
            
        if success:
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


@app.route('/facebook_marketplace/listings', methods=['GET'])
def get_facebook_listings():
    """
    Public API endpoint to retrieve Facebook Marketplace listings.
    Internal API, secured via session or open if meant for external consumption (assuming internal/local for now).
    """
    try:
        # 1. Parse Parameters
        try:
            limit = int(request.args.get('limit', 100))
            if limit > 500: limit = 500
        except:
            limit = 100
            
        cursor = request.args.get('cursor')
        sort = request.args.get('sort', 'posted_at_desc')
        max_age_minutes = request.args.get('max_age_minutes')
        
        # 2. Build Query
        query = {}
        
        # Filter by Source
        query['source'] = 'facebook_marketplace'
        
        # Filter by freshness (max_age_minutes)
        if max_age_minutes:
            try:
                minutes = int(max_age_minutes)
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
                # Ensure we strictly filter by posted_at or processed_at
                # Note: 'posted_at' is ISO string in our schema
                query['posted_at'] = {'$gte': cutoff_time.isoformat()}
            except:
                pass
                
        # Cursor Pagination (Keyset Pagination on posted_at)
        if cursor:
            # Cursor is expected to be the last seen 'posted_at' value
            # Since we sort DESC, we want values LESS THAN the cursor
            if 'posted_at' in query:
                 # Merge with existing range if any (complex, but simple case: $lt)
                 existing = query['posted_at']
                 if isinstance(existing, dict):
                     existing['$lt'] = cursor
                 else:
                     query['posted_at'] = {'$lt': cursor}
            else:
                query['posted_at'] = {'$lt': cursor}

        # 3. Execute Query
        if db is not None:
            collection = db['listings']
            
            # Sort direction
            sort_dir = -1 # Descending
            if 'asc' in sort: sort_dir = 1
            
            # Fetch
            cursor_obj = collection.find(query).sort('posted_at', sort_dir).limit(limit)
            results = list(cursor_obj)
        else:
            # Fallback to empty if DB not connected
            results = []

        # 4. Format Response
        items = []
        last_posted_at = None
        
        for doc in results:
            # Transform _id to string
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            
            # Track cursor
            last_posted_at = doc.get('posted_at')
            
            items.append(doc)
            
        # 5. Construct Next Cursor
        next_cursor = last_posted_at if len(items) == limit else None
        
        response = {
            "meta": {
                "count": len(items),
                "cursor": next_cursor,
                "params": {
                    "limit": limit,
                    "sort": sort,
                    "max_age_minutes": max_age_minutes
                }
            },
            "items": items
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500


# --- Scanner Control APIs ---
@app.route('/api/scanner/start', methods=['POST'])
def start_scanner():
    """
    Trigger a manual scan. 
    On Vercel/Railway, this triggers the Bright Data job.
    """
    try:
        source = request.json.get('source', 'facebook')
        # In a real serverless setup, we'd trigger a cloud function or just run the light logic here.
        # Since we are using Bright Data API, this is lightweight!
        
        # We can import and run the specific manager method directly
        from modules.bright_data import BrightDataManager
        import threading
        
        def run_background_scan():
            try:
                print(f"🚀 Starting background scan for {source}...")
                mgr = BrightDataManager()
                # Default location/context
                # TODO: Get from database/config
                mgr.fetch_listings(location="Chicago, IL") 
            except Exception as e:
                print(f"❌ Background scan failed: {e}")

        # Run in thread so request returns immediately
        threading.Thread(target=run_background_scan).start()

        return jsonify({"status": "started", "message": f"{source} scan initiated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/status', methods=['GET'])
def get_scanner_status():
    # Simple mock status or check DB for recent activity
    # For now, just return Idle/Running based on a file lock or simplified logic
    return jsonify({"status": "idle", "last_run": "Just now"})

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
