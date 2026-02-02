"""
Barndoor Analytics Dashboard
Interactive Streamlit application for exploring and filtering vehicle listings.

Usage:
    streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import re
import time
from database.config_db import ConfigDB
from modules.network import NetworkManager

# Page configuration
st.set_page_config(
    page_title="Barndoor Analytics Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# HELPER FUNCTIONS
# ==========================================

@st.cache_data
def load_data():
    """Load listings from the TinyDB ledger.json file."""
    ledger_path = Path('database/ledger.json')
    if not ledger_path.exists():
        return pd.DataFrame()
    
    try:
        with open(ledger_path, 'r') as f:
            data = json.load(f)
        
        # TinyDB stores data in tables
        if 'listings' in data:
            listings = data['listings']
            if isinstance(listings, dict):
                listings = list(listings.values())
        else:
            listings = []
        
        if not listings:
            return pd.DataFrame()
        
        df = pd.DataFrame(listings)
        
        # Ensure numeric columns
        numeric_cols = ['price', 'mileage', 'score']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def extract_make_from_title(title):
    """Extract car make from title text."""
    if not title: return 'Unknown'
    makes = ['toyota', 'honda', 'subaru', 'nissan', 'ford', 'chevy', 'chevrolet',
             'dodge', 'mitsubishi', 'buick', 'hyundai', 'kia', 'jeep', 'gmc',
             'bmw', 'mercedes', 'audi', 'volkswagen', 'mazda', 'lexus', 'acura',
             'ram', 'tesla', 'porsche', 'jaguar', 'land rover', 'volvo']
    title_lower = title.lower()
    for make in makes:
        if make in title_lower:
            return make.capitalize()
    return 'Unknown'

# ==========================================
# PAGE RENDERERS
# ==========================================

def render_data_explorer():
    """Render the main data explorer page."""
    # Initialize Network Manager
    net_manager = NetworkManager()
    

    # --- HEADER ---
    st.markdown("## 🔎 Data Explorer")
    
    # --- SIDEBAR: SCANNER CONTROLS ---
    st.sidebar.subheader("📡 Scanner Controls")
    
    # Auto-Run Toggle
    config_db = ConfigDB()
    current_config = config_db.get_config()
    
    # Check current status from scan_status.json
    status_msg = "Idle"
    is_active = False
    try:
         with open("database/scan_status.json", "r") as f:
             status_data = json.load(f)
             is_active = status_data.get("active", False)
             status_msg = status_data.get("status", "Idle")
             pct = status_data.get("percent", 0)
    except:
         pct = 0
         
    if is_active:
        st.sidebar.info(f"RUNNING: {status_msg} ({pct}%)")
        st.sidebar.progress(pct / 100)
    else:
        st.sidebar.success(f"STATUS: {status_msg}")

    # Auto-Run Switch
    auto_run = st.sidebar.checkbox("✅ Enable Auto-Run (Every 10m)", value=current_config.get("auto_scrape_enabled", True))
    
    if auto_run != current_config.get("auto_scrape_enabled", True):
        current_config["auto_scrape_enabled"] = auto_run
        config_db.update_config(current_config)
        st.rerun()

    col_btn1, col_btn2 = st.sidebar.columns(2)
    with col_btn1:
        if st.button("🚀 Scan FB", type="primary", disabled=is_active, use_container_width=True):
            import subprocess
            import os
            try:
                # Trigger main.py in manual mode
                subprocess.Popen(["python3", "main.py", "--manual", "--source", "facebook", "--once"])
                st.toast("Facebook Scan Initiated!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
                
    with col_btn2:
        if st.button("🚀 Scan CL", disabled=is_active, use_container_width=True):
             import subprocess
             try:
                 subprocess.Popen(["python3", "main.py", "--manual", "--source", "craigslist", "--once"])
                 st.toast("Craigslist Scan Initiated!")
                 time.sleep(1)
                 st.rerun()
             except Exception as e:
                 st.sidebar.error(f"Error: {e}")

    st.sidebar.markdown("---")
    
    # --- SEARCH CONFIGURATION ---
    with st.sidebar.expander("🎯 Search Configuration", expanded=True):
        st.write("**Where should the Seeker look?**")
        st.info("ℹ️ Enter a City, State or Zip Code.")
        
        # Get existing targets
        current_context = current_config.get('target_urls', '')
        if isinstance(current_context, list): current_context = ",".join(current_context)
        
        new_context = st.text_area(
            "Target Location / Context",
            value=current_context,
            placeholder="Chicago, IL",
            height=68
        )
        
        if st.button("Save Configuration", use_container_width=True):
            current_config['target_urls'] = new_context # Storing as string now mainly
            current_config['location'] = new_context # Also update location key if used
            config_db.update_config(current_config)
            st.success("Saved!")
            st.rerun()
            
    st.sidebar.markdown("---")

    # --- FILTERS ---
    st.sidebar.subheader("Filters")
    df = load_data()
    
    if df.empty:
        st.warning("No listings found in database. Run the scanner.")
    else:
        # Preprocessing
        if 'make' not in df.columns:
            df['make'] = df['title'].apply(extract_make_from_title)
            
        # Source Filter
        sources = df['source'].unique().tolist() if 'source' in df.columns else []
        selected_sources = st.sidebar.multiselect("Sources", options=sources, default=sources)
        
        # Keyword Search
        keyword = st.sidebar.text_input("🔍 Search Keyword")
        
        # Ranges
        min_p = int(df['price'].min()) if not df.empty else 0
        max_p = int(df['price'].max()) if not df.empty else 100000
        # Sanity check
        if min_p < 0: min_p = 0
        if max_p < min_p: max_p = min_p + 1000
        
        price_range = st.sidebar.slider("💰 Price Range", min_value=0, max_value=max_p, value=(min_p, max_p))
        
        # Apply filters
        filtered_df = df.copy()
        if selected_sources:
             filtered_df = filtered_df[filtered_df['source'].isin(selected_sources)]
        if keyword:
             filtered_df = filtered_df[filtered_df['description'].str.contains(keyword, case=False, na=False) | df['title'].str.contains(keyword, case=False, na=False)]
        
        filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]
        
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Listings", len(df))
        c2.metric("Filtered", len(filtered_df))
        c3.metric("Avg Price", f"${int(filtered_df['price'].mean())}" if not filtered_df.empty else "N/A")
        
        # Display
        st.subheader(f"Listings ({len(filtered_df)})")
        
        # Show recent first
        if not filtered_df.empty:
            filtered_df = filtered_df.sort_values(by='score', ascending=False) if 'score' in filtered_df.columns else filtered_df
            
        for _, row in filtered_df.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                # Image
                img_url = None
                if isinstance(row.get('images'), list) and row.get('images'):
                     img_url = row['images'][0]
                elif isinstance(row.get('images'), str) and row.get('images').startswith('http'):
                     img_url = row['images']
                     
                with cols[0]:
                    if img_url:
                        st.image(img_url, use_column_width=True)
                    else:
                        st.text("No Image")
                
                with cols[1]:
                    st.markdown(f"**[{row.get('title') or 'Unknown'}]({row.get('listing_url')})**")
                    st.markdown(f"**${row.get('price', 0):,}** • {row.get('mileage', 0):,} mi • {row.get('location', 'Unknown')}")
                    
                    desc = str(row.get('description', ''))[:150] + "..." if row.get('description') else "No description."
                    st.caption(desc)
                    st.caption(f"Source: {row.get('source')} | Listed: {row.get('hours_since_listed', '?')}h ago")
                
                st.markdown("---")

    # --- SPECTATOR TILE REMOVED (No longer applicable for API mode) ---


    # --- MAIN CONTENT AREA ---
    # We can also put a big watcher at the top if requested
    
def main():
    render_data_explorer()
    
    # Add a dedicated Spectator Page or Overlay if requested?
    # For now, sidebar is safest to not break layout.

if __name__ == "__main__":
    main()
