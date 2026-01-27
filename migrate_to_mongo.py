
import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load .env from current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    # Fallback to the one provided in chat if env var not set yet (for immediate run)
    MONGO_URI = "mongodb+srv://shrinkrayorg_db_user:tVKHLRillubh3uEd@cluster0.8kbvvam.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

DB_NAME = "barndoor"
COLLECTION_NAME = "listings"
LOCAL_DB_PATH = "database/ledger.json"

def migrate():
    print("🚀 Starting migration from TinyDB to MongoDB...")
    
    # 1. Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        # Ping to check connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return

    # 2. Read Local Data
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"❌ Local database not found at {LOCAL_DB_PATH}")
        return

    with open(LOCAL_DB_PATH, 'r') as f:
        data = json.load(f)
        
    listings_map = data.get('listings', {})
    print(f"📖 Found {len(listings_map)} listings in local ledger.json")

    # 3. Transform and Insert
    new_docs = []
    for doc_id, listing in listings_map.items():
        # TinyDB uses the key as ID, MongoDB uses _id.
        # We will use the TinyDB ID string as the MongoDB _id to preserve identity if possible,
        # or just add it as a field 'tinydb_id' and let Mongo generate _id.
        # Let's try to keep it simple: Add 'original_id' and let Mongo handle _id.
        
        listing['original_id'] = str(doc_id)
        
        # Ensure status exists
        if 'status' not in listing:
            listing['status'] = 'active'
            
        new_docs.append(listing)

    if new_docs:
        # clear existing to avoid duplicates during dev testing? No, let's just insert.
        # actually, let's use replace_one with upsert based on listing_url to prevent dupes
        
        inserted_count = 0
        updated_count = 0
        
        for doc in new_docs:
            url = doc.get('listing_url')
            if url:
                result = collection.replace_one(
                    {'listing_url': url}, 
                    doc, 
                    upsert=True
                )
                if result.upserted_id:
                    inserted_count += 1
                else:
                    updated_count += 1
            else:
                # If no URL, just insert (rare)
                collection.insert_one(doc)
                inserted_count += 1
                
        print(f"✅ Migration Complete!")
        print(f"   Inserted: {inserted_count}")
        print(f"   Updated:  {updated_count}")
    else:
        print("⚠️ No listings found to migrate.")

if __name__ == "__main__":
    migrate()
