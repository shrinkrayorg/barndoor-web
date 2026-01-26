import json

try:
    with open('database/ledger.json', 'r') as f:
        data = json.load(f)
    
    listings = data.get('listings', {})
    print(f"Type of listings: {type(listings)}")
    
    if isinstance(listings, dict):
        for k, v in listings.items():
            if not isinstance(v, dict):
                print(f"⚠️ FOUND BAD ENTRY! Key: {k}, Type: {type(v)}, Value: {v}")
            else:
                # pass
                pass
        print("Scan complete.")
    else:
        print(f"Listings is not a dict! It is: {listings}")

except Exception as e:
    print(f"Error: {e}")
