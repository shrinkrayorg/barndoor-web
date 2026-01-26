import requests
import json

try:
    print("Testing http://localhost:5050/api/listings ...")
    r = requests.get('http://localhost:5050/api/listings')
    print(f"Status Code: {r.status_code}")
    data = r.json()
    if r.status_code != 200:
        print(f"Error from Server: {data.get('error')}")
    else:
        print(f"Total: {data.get('total')}")
        print(f"Listings count: {len(data.get('listings', []))}")
        if len(data.get('listings', [])) > 0:
            print("Sample item:", data['listings'][0]['title'])
    # Test Homepage
    print("\nTesting Homepage Content...")
    r_home = requests.get('http://localhost:5050/')
    if "(Live)" in r_home.text:
        print("✅ Homepage is serving NEW version (Live marker found)")
    else:
        print("❌ Homepage is serving OLD version")
except Exception as e:
    print(f"Failed: {e}")
