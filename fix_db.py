import json
from tinydb import TinyDB, Query

db = TinyDB('database/ledger.json')
table = db.table('listings')
listings = table.all()

print(f"Fixing {len(listings)} listings...")

fixed = 0
for item in listings:
    if item.get('title') == "Unknown":
        desc = item.get('description', '')
        lines = [l.strip() for l in desc.split('\n') if l.strip()]
        
        price = item.get('price', 0)
        new_title = "Unknown"
        
        for line in lines:
            # Skip price like lines
            if line.startswith('$') or str(price) in line:
                continue
            # Skip obvious location/meta info
            if "miles" in line.lower() or "dealership" in line.lower() or "oklahoma" in line.lower():
                continue
            
            # Take the first line that survives as likely title
            new_title = line
            break
            
        if new_title != "Unknown":
            table.update({'title': new_title}, doc_ids=[item.doc_id])
            print(f"✅ Fixed: {new_title}")
            fixed += 1

print(f"Done! Fixed {fixed} items.")
