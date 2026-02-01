# Getting Bright Data Proxy Credentials

Follow these steps to update your proxy credentials:

## Step 1: Log into Bright Data
1. Go to https://brightdata.com/cp/zones
2. Log in with your account

## Step 2: Find Your Residential Proxy Zone
1. Look for a zone with type **"Residential"** or **"ISP"**
2. Common zone names: `barndoor`, `residential`, `scraping`, etc.
3. Click on the zone to open its details

## Step 3: Get Your Credentials
You need TWO pieces of information:

### Zone Name
- Found at the top of the zone details page
- Example: `barndoor` or `residential_proxy`

### Zone Password
- Look for "Access parameters" or "Credentials" section
- Click "Show" or the eye icon to reveal the password
- It's usually a random string like: `a1b2c3d4e5f6`

### Customer ID (Optional)
- Found in the "Username" field
- Format: `brd-customer-XXXXX-zone-ZONENAME`
- The `XXXXX` part is your customer ID
- If you already have it in settings, you can skip this

## Step 4: Update Credentials
Run this command in your terminal:

```bash
cd /Users/gabrielgaft/Desktop/Barndoor/project_barnfind
python3 update_proxy_creds.py
```

The script will ask you for:
1. Zone Name
2. Zone Password  
3. Customer ID (optional - press Enter to use existing)

## Step 5: Test Connection
After updating, verify it works:

```bash
python3 test_proxy.py
```

You should see:
- ✅ Proxy IP: [some IP]
- ✅ Location: [city, state]
- ✅ Facebook loaded successfully

## Troubleshooting

**If you don't have any zones:**
You may need to create one in Bright Data:
1. Click "Add Zone" or "Create Zone"
2. Choose "Residential" type
3. Name it "barndoor"
4. Save and get the credentials

**If you get 407 errors after updating:**
The zone might be out of credit or disabled. Check your Bright Data account balance.
