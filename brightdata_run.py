import time
import requests

API_KEY = "8771d02e-b647-462a-a811-4e7de1f03cfd"
DATASET_ID = "gd_lvt9iwuh6fbcwmx1a"

URLS = [
  "https://www.facebook.com/marketplace/item/981001136298403/",
  "https://www.facebook.com/marketplace/item/1073152470446177/",
]

TRIGGER_URL = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={DATASET_ID}"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = [{"url": u} for u in URLS]

r = requests.post(TRIGGER_URL, headers=HEADERS, json=payload)
if not r.ok:
    print(f"Error triggering dataset: {r.status_code} - {r.text}")
r.raise_for_status()
snapshot_id = r.json()["snapshot_id"]
print("snapshot_id:", snapshot_id)

RESULT_URL = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

while True:
  res = requests.get(RESULT_URL, headers=HEADERS)
  if res.status_code == 200:
    data = res.json()
    print(data)
    with open("brightdata_results.json", "w") as f:
      import json
      json.dump(data, f, indent=2)
    print("Saved: brightdata_results.json")
    break
  if res.status_code == 202:
    time.sleep(8)
    continue
  print("Error:", res.status_code, res.text)
  break
