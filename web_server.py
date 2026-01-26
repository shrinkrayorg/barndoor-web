#!/usr/bin/env python3
"""
Barndoor Web Server
Flask backend for the modern Material Design interface.
"""
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'barndoor-secret-key-change-this'

# Simple Auth Check
USERNAME = "admin"
PASSWORD = "password"  # You should change this or load from env

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "database" / "ledger.json"
SETTINGS_PATH = PROJECT_DIR / "database" / "settings.json"
LOG_PATH = PROJECT_DIR / "barnfind.log"
PID_FILE = PROJECT_DIR / "barnfind.pid"


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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        
        if user == USERNAME and pw == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
def index():
    """Serve the main interface."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')


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
        
        if DB_PATH.exists():
            with open(DB_PATH, 'r') as f:
                data = json.load(f)
                listings = data.get('listings', {})
                # Count all listings
                # listings is a dict of id -> listing
                total = len(listings)
                stats['total_listings'] = total
        
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
            new_settings = request.json
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(new_settings, f, indent=4)
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
    """Serve the Tickle Sheet interface."""
    return render_template('tickle.html')


@app.route('/api/listings')
def get_listings():
    """Get listings filtered by status."""
    status_filter = request.args.get('status')
    
    try:
        if not DB_PATH.exists():
            return jsonify({'listings': []})
        
        with open(DB_PATH, 'r') as f:
            data = json.load(f)
        
        all_listings = []
        listings_map = data.get('listings', {})
        
        # Iterate over ITEMS to get the ID
        for doc_id, listing in listings_map.items():
            # Inject ID for frontend use
            listing['id'] = doc_id 
            
            # Default status is 'active' if not present
            current_status = listing.get('status', 'active')
            
            # If filter is requested, match it
            if status_filter:
                if current_status == status_filter:
                    all_listings.append(listing)
            else:
                all_listings.append(listing)
        
        return jsonify({'listings': all_listings, 'total': len(all_listings)})
    except Exception as e:
        print(f"Error serving listings: {e}") 
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/delete', methods=['POST'])
def delete_listings():
    """Bulk delete listings by ID."""
    try:
        payload = request.json
        ids_to_delete = payload.get('ids', []) 
        
        if not ids_to_delete:
             return jsonify({'success': True, 'count': 0})
             
        if not DB_PATH.exists():
             return jsonify({'error': 'DB not found'}), 404
             
        with open(DB_PATH, 'r+') as f:
            data = json.load(f)
            listings = data.get('listings', {})
            deleted_count = 0
            
            for id_str in ids_to_delete:
                # Ensure string type as JSON keys are strings
                id_key = str(id_str)
                if id_key in listings:
                    del listings[id_key]
                    deleted_count += 1
            
            # Save back
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
            
        return jsonify({'success': True, 'count': deleted_count})
            
    except Exception as e:
        print(f"Error deleting listings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_status', methods=['POST'])
def update_status():
    """Update listing status (archive, sold, deleted)."""
    try:
        payload = request.json
        url = payload.get('url')
        new_status = payload.get('status')
        
        if not DB_PATH.exists():
            return jsonify({'error': 'DB not found'}), 404
            
        with open(DB_PATH, 'r+') as f:
            data = json.load(f)
            updated = False
            
            # Search and update
            listings = data.get('listings', {})
            for listing in listings.values():
                if listing.get('listing_url') == url:
                    listing['status'] = new_status
                    if new_status == 'tickle': # User requested "Tickle File"
                        listing['tickle_at'] = datetime.now().isoformat()
                    updated = True
                    break
            
            if updated:
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Listing not found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications')
def get_notifications():
    """Check for due tickle reminders and return details."""
    try:
        if not DB_PATH.exists():
            return jsonify({'count': 0, 'items': []})
            
        with open(DB_PATH, 'r') as f:
            data = json.load(f)
            
        due_items = []
        now = datetime.now()
        
        for platform in data.get('listings', {}).values():
            for listing in platform:
                if listing.get('status') == 'archived' and listing.get('archived_at'):
                    archived = datetime.fromisoformat(listing['archived_at'])
                    # Check if 7 days passed
                    if (now - archived).days >= 7:
                        due_items.append({
                            'title': listing.get('title', 'Unknown Vehicle'),
                            'location': listing.get('location', 'Unknown Location'),
                            'url': listing.get('listing_url'),
                            'archived_at': listing.get('archived_at')
                        })
                        
        return jsonify({'count': len(due_items), 'items': due_items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the server
    print("🚗 Barndoor Web Server")
    print("=" * 50)
    print("Opening in browser...")
    print("=" * 50)
    
    # Open browser automatically
    import webbrowser
    import threading
    
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://localhost:5050')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask
    app.run(host='127.0.0.1', port=5050, debug=False)
