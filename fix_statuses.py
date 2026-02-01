#!/usr/bin/env python3
"""
Quick script to update all listing statuses from 'deleted' to 'active'
"""
from pymongo import MongoClient
import certifi
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.barndoor

#  Update all listings with status='deleted' to status='active'
result = db.listings.update_many(
    {'status': 'deleted'},
    {'$set': {'status': 'active'}}
)

print(f"✅ Updated {result.modified_count} listings from 'deleted' to 'active'")

# Verify
active_count = db.listings.count_documents({'status': 'active'})
deleted_count = db.listings.count_documents({'status': 'deleted'})

print(f"📊 Current status:")
print(f"   Active: {active_count}")
print(f"   Deleted: {deleted_count}")
