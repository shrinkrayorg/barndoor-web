import json
from pathlib import Path

def save_creds():
    settings_path = Path('database/settings.json')
    
    # Load existing or create new
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            try:
                settings = json.load(f)
            except:
                settings = {}
    else:
        settings = {}
        settings_path.parent.mkdir(exist_ok=True, parents=True)

    # Credentials from User's CURL command
    # curl -i --proxy brd.superproxy.io:33335 --proxy-user brd-customer-hl_2379ea97-zone-barndoor:7h3o8lfn4qh2 ...
    
    host = "brd.superproxy.io"
    port = 33335
    
    # Base username from curl
    base_user = "brd-customer-hl_2379ea97-zone-barndoor"
    # Append geolocation targeting (CHICAGO)
    final_user = f"{base_user}-country-us-city-chicago"
    
    password = "7h3o8lfn4qh2"
    
    # Update Network Section
    if 'network' not in settings:
        settings['network'] = {}
        
    settings['network']['mode'] = 'proxy'
    settings['network']['proxy_host'] = host
    settings['network']['proxy_port'] = port
    settings['network']['proxy_user'] = final_user
    settings['network']['proxy_pass'] = password
    
    # Write back
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=4)
        
    print(f"✅ Configuration Saved!")
    print(f"   Host: {host}:{port}")
    print(f"   User: {final_user}")
    print("   Mode: Residential Proxy (US Targeted)")

if __name__ == "__main__":
    save_creds()
