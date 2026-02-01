#!/usr/bin/env python3
"""
Interactive script to update Bright Data proxy credentials
"""
import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent / "database" / "settings.json"

print("=" * 60)
print("🔧 Bright Data Proxy Credential Updater")
print("=" * 60)
print()
print("Please log into https://brightdata.com/cp/zones")
print("and locate your Residential Proxy Zone.")
print()

# Get zone name
zone_name = input("Enter Zone Name (e.g., 'barndoor', 'residential'): ").strip()
if not zone_name:
    print("❌ Zone name required")
    exit(1)

# Get password
zone_password = input("Enter Zone Password: ").strip()
if not zone_password:
    print("❌ Password required")
    exit(1)

# Optional: Get customer ID (it's usually in the username format)
print()
print("The username format is usually: brd-customer-XXXXXXXXXX-zone-ZONENAME")
customer_id = input("Enter Customer ID (or press Enter to use existing): ").strip()

# Load existing settings
with open(SETTINGS_PATH) as f:
    settings = json.load(f)

# Update network config
if 'network' not in settings:
    settings['network'] = {}

settings['network']['mode'] = 'proxy'
settings['network']['proxy_host'] = 'brd.superproxy.io'
settings['network']['proxy_port'] = 33335
settings['network']['proxy_pass'] = zone_password

# Build username
if customer_id:
    settings['network']['proxy_user'] = f"brd-customer-{customer_id}-zone-{zone_name}"
else:
    # Keep existing customer ID if present
    existing_user = settings['network'].get('proxy_user', '')
    if 'brd-customer-' in existing_user:
        # Extract customer ID
        parts = existing_user.split('-')
        if len(parts) >= 3:
            existing_customer = parts[2]
            settings['network']['proxy_user'] = f"brd-customer-{existing_customer}-zone-{zone_name}"
        else:
            print("⚠️  Could not parse existing customer ID. Please provide it.")
            exit(1)
    else:
        print("❌ Need customer ID to build username")
        exit(1)

# Save
with open(SETTINGS_PATH, 'w') as f:
    json.dump(settings, f, indent=4)

print()
print("✅ Proxy credentials updated successfully!")
print(f"   Zone: {zone_name}")
print(f"   User: {settings['network']['proxy_user']}")
print()
print("Run test_proxy.py to verify the connection:")
print("   python3 test_proxy.py")
