import json
import re
import os

DB_PATH = 'database/ledger.json'
BACKUP_PATH = 'database/ledger.json.bak'

def fix_mileage():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    # Create backup
    with open(DB_PATH, 'r') as f:
        data = json.load(f)
    
    with open(BACKUP_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Backup created at {BACKUP_PATH}")

    listings = data.get('listings', {})
    updated_count = 0

    for lid, item in listings.items():
        desc = item.get('description', '')
        current_mileage = item.get('mileage', 0)
        
        # Pattern 1: Explicit "Driven X miles" (strongest signal)
        match = re.search(r'Driven\s+([0-9,]+)\s+miles', desc, re.IGNORECASE)
        
        # Pattern 2: "Odmeteter: X miles" or similar
        if not match:
            match = re.search(r'Odometer[:\s]+([0-9,]+)', desc, re.IGNORECASE)

        if match:
            raw_miles = match.group(1).replace(',', '')
            try:
                new_miles = int(raw_miles)
                
                # Logic: Update if current is 0 OR new mileage is significantly different/better
                # For now, let's treat "Driven" as source of truth if it exists
                if new_miles > 0 and new_miles != current_mileage:
                    print(f"ID {lid} ({item.get('title')}): {current_mileage} -> {new_miles} (Found: '{match.group(0)}')")
                    item['mileage'] = new_miles
                    updated_count += 1
            except ValueError:
                pass
        
    if updated_count > 0:
        with open(DB_PATH, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Successfully updated {updated_count} listings.")
    else:
        print("No listings required updates.")

if __name__ == "__main__":
    fix_mileage()
