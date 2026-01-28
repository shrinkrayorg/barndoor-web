

import json
from tinydb import TinyDB, Query

db = TinyDB('database/ledger.json')
table = db.table('listings')
all_items = table.all()

unknown_locs = [i for i in all_items if i.get('location') == 'Unknown']
print(f"Total items: {len(all_items)}")
print(f"Items with Unknown location: {len(unknown_locs)}")

if unknown_locs:
    item = unknown_locs[-1]
    print("\n--- Failed Item ---")
    print(f"Title: {item.get('title')}")
    print(f"URL: {item.get('listing_url')}")
    print(f"Source: {item.get('source')}")
    print(json.dumps(item, indent=2))
else:
    print("No items with Unknown location found.")
