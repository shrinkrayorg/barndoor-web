import requests
import json
import os
import subprocess
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_TOKEN = os.getenv('BRIGHT_DATA_API_KEY')
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

def setup_proxy():
    print("🪄 Starting 'Magic' Proxy Setup...")
    
    if not API_TOKEN:
        print("❌ Error: BRIGHT_DATA_API_KEY not found in .env")
        return False

    target_zone = "barndoor_residential"
    found = False

    # 1. Search for ANY Residential Zone (Probe common names)
    print("🔍 Probing for common Residential zones...")
    
    common_names = ['barndoor', 'barndoor_residential', 'residential', 'serp', 'unblocker', 'scraping', 'unlocker', 'res']
    
    for probe_name in common_names:
        try:
            print(f"   Probing '{probe_name}'...")
            res = requests.get(f'https://api.brightdata.com/zone?zone={probe_name}', headers=HEADERS)
            
            if res.status_code == 200:
                zone_data = res.json()
                # Double check it is actually a zone object and not error
                if isinstance(zone_data, dict) and 'name' in zone_data:
                    target_zone = zone_data['name']
                    print(f"✅ Found existing zone: {target_zone}")
                    found = True
                    break
                elif isinstance(zone_data, list) and len(zone_data) > 0:
                     target_zone = zone_data[0]['name']
                     print(f"✅ Found existing zone: {target_zone}")
                     found = True
                     break
            elif res.status_code == 404:
                continue # Not this one
            else:
                pass # Other error
                
        except Exception:
            pass

    # 2. Create if not exists
    if not found:
        print(f"🆕 Creating new zone: {target_zone}...")
        
        # Construct raw JSON string strictly
        json_body = json.dumps({
            "zone": {"name": target_zone, "network": "residential"},
            "plan": "pay_as_you_go"
        })
        
        curl_cmd = [
            "curl", "-X", "POST", "https://api.brightdata.com/zone",
            "-H", f"Authorization: Bearer {API_TOKEN}",
            "-H", "Content-Type: application/json",
            "-d", json_body,
            "--silent", "--show-error"
        ]
        
        try:
            print(f"   Running CURL: {' '.join(curl_cmd[:6])} ... [masked]")
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   Result: {result.stdout}")
                if "name" in result.stdout and target_zone in result.stdout:
                     print("✅ Zone created successfully (via CURL)!")
                     found = True
                elif "zone already exists" in result.stdout.lower():
                     found = True
            else:
                print(f"❌ CURL Failed: {result.stderr}")

        except Exception as e:
            print(f"❌ Subprocess Error: {e}")
            
    # 3. Get Credentials for the Zone
    if found:
        print("🔑 Retrieving credentials...")
        # Get zone info to find password
        res = requests.get(f'https://api.brightdata.com/zone?zone={target_zone}', headers=HEADERS)
        
        if res.status_code == 200:
            zone_info = res.json()
            # The structure is usually a list or dict. 
            # If requesting specific zone, might be a single dict or look inside list.
            
            # Helper to find our zone in the response
            my_zone = None
            if isinstance(zone_info, list):
                for z in zone_info:
                    if z['name'] == target_zone:
                         my_zone = z
                         break
            else:
                my_zone = zone_info
            
            if my_zone:
                # Construct credentials
                # Host: brd.superproxy.io
                # Port: 22225
                # User: brd-customer-<customer_id>-zone-<zone_name>
                # Pass: <zone_password>
                
                # Check if we have password
                password = my_zone.get('password')
                # Check for customer_id (sometimes in 'account_id' or embedded in username example)
                # Usually we can get the full username from "ips" endpoint or just construct it if we knew customer_id.
                
                # Retrieve explicit access parameters
                # There isn't always a direct "get credentials" endpoint, but 'zone' info usually has 'password'.
                # For Username, we need the Customer ID. That is part of the API Token owner? 
                
                # Alternative: GET /api/customer/account to get customer ID.
                cust_res = requests.get('https://api.brightdata.com/customer', headers=HEADERS)
                customer_id = ""
                if cust_res.status_code == 200:
                    cust_data = cust_res.json()
                    customer_id = cust_data.get('customer_id') or cust_data.get('id')
                
                if not customer_id:
                     print("⚠️ Could not retrieve Customer ID. Check permissions.")
                     return False
                     
                # Magic: Target US location via username parameters
                # We can add -city-chicago later if needed, but -country-us is safe/standard
                username = f"brd-customer-{customer_id}-zone-{target_zone}-country-us"
                host = "brd.superproxy.io"
                port = 22225
                
                print(f"📝 Config:")
                print(f"   Host: {host}")
                print(f"   Port: {port}")
                print(f"   User: {username}")
                print(f"   Pass: {'*' * 5}")
                
                # 4. Save to Settings
                settings_path = Path('database/settings.json')
                if settings_path.exists():
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                else:
                    settings = {}
                
                # Ensure network section
                if 'network' not in settings: settings['network'] = {}
                
                settings['network']['mode'] = 'proxy'
                settings['network']['proxy_host'] = host
                settings['network']['proxy_port'] = port
                settings['network']['proxy_user'] = username
                settings['network']['proxy_pass'] = password
                
                with open(settings_path, 'w') as f:
                    json.dump(settings, f, indent=4)
                    
                print("💾 Saved credentials to database/settings.json")
                print("🎉 MAGIC SETUP COMPLETE!")
                return True
                
            else:
                print("❌ Zone details not found in API response.")
                return False
        else:
            print(f"❌ Failed to get zone details: {res.status_code}")
            return False

    return False

if __name__ == "__main__":
    setup_proxy()
