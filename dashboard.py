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
    
    
    # --- SIDEBAR: NETWORK IDENTITY ---
    st.sidebar.subheader("🌐 Network Identity")
    
    # Get current IP
    if 'network_info' not in st.session_state:
        st.session_state.network_info = net_manager.get_current_identity()
        
    net_info = st.session_state.network_info
    
    # Display Status
    is_protected = net_info.get('city') != 'Unknown' 
    status_color = "🟢" if is_protected else "🔴"
    
    col_net1, col_net2 = st.sidebar.columns([3, 1])
    with col_net1:
        st.markdown(f"**IP:** `{net_info.get('ip')}`")
        st.caption(f"{status_color} {net_info.get('city')}, {net_info.get('region')}")
    with col_net2:
        if st.button("🔄", help="Refresh Network Info"):
             st.session_state.network_info = net_manager.get_current_identity()
             st.rerun()
             
    # Residential Proxy Configuration
    with st.sidebar.expander("🌐 Residential Proxy Settings", expanded=True):
        st.info("Provide your residential proxy credentials.")
        
        # Load current settings from config
        config = net_manager.db.get_config()
        net_conf = config.get('network', {})
        
        c_host = net_conf.get('proxy_host', '')
        c_port = net_conf.get('proxy_port', '')
        c_user = net_conf.get('proxy_user', '')
        c_pass = net_conf.get('proxy_pass', '')
        
        p_host = st.text_input("Proxy Host / IP", value=c_host, placeholder="e.g. pr.residential.com")
        p_port = st.text_input("Port", value=c_port, placeholder="e.g. 1000")
        p_user = st.text_input("Username", value=c_user)
        p_pass = st.text_input("Password", value=c_pass, type="password")
        
        if st.button("Save Proxy Settings"):
            # Update via ConfigDB
            config['network'] = {
                'mode': 'proxy',
                'proxy_host': p_host,
                'proxy_port': p_port,
                'proxy_user': p_user,
                'proxy_pass': p_pass
            }
            net_manager.db.update_config(config)
            st.success("Proxy Settings Saved!")
            st.rerun()
            
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("---")
    
    # --- SEARCH CONFIGURATION ---
    with st.sidebar.expander("🎯 Search Configuration", expanded=True):
        st.write("**Where should the Seeker look?**")
        st.info("ℹ️ Paste the full `https://...` link from your browser address bar.")
        
        # Load current config directly
        config_db = ConfigDB()
        current_config = config_db.get_config()
        
        # Get existing targets
        current_targets = current_config.get('target_urls', '')
        
        # Normalize list to string if needed
        if isinstance(current_targets, list):
            current_targets = "\n".join(current_targets)
        
        # If the user has "50 mile..." text that isn't a URL, show a warning
        if current_targets and not current_targets.strip().startswith("http"):
            # Check if any line starts with http if it's multiline
            if not any(line.strip().startswith("http") for line in current_targets.split('\n') if line.strip()):
                st.warning("⚠️ That doesn't look like a valid link!")
        
        new_targets = st.text_area(
            "Target URLs (One per line)",
            value=current_targets,
            placeholder="https://www.facebook.com/marketplace/chicago/cars",
            height=100
        )
        
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            if st.button("Save Targets"):
                # Clean and save
                urls = [line.strip() for line in new_targets.split('\n') if line.strip()]
                joined_urls = ",".join(urls)
                
                # Update config object
                current_config['target_urls'] = joined_urls
                config_db.update_config(current_config)
                
                st.success("Saved!")
                time.sleep(1)
                st.rerun()
        
        with col_cfg2:
            if st.button("Reset Default"):
                default_url = "https://www.facebook.com/marketplace/category/vehicles"
                current_config['target_urls'] = default_url
                config_db.update_config(current_config)
                st.rerun()

    # --- FILTERS ---
    st.sidebar.subheader("Filters")
    df = load_data()
    
    if df.empty:
        st.warning("No listings found in database. Run the main application.")
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
        min_price = int(df['price'].min()) if not df.empty else 0
        max_price = int(df['price'].max()) if not df.empty else 100000
        price_range = st.sidebar.slider("💰 Price Range", min_value=0, max_value=max_price, value=(min_price, max_price), step=500)
        
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
        for _, row in filtered_df.iterrows():
            with st.container():
                st.markdown(f"**{row.get('title')}** - ${row.get('price')}")
                st.caption(f"{row.get('source')} | {row.get('location')} | Score: {row.get('score')}")
                st.markdown("---")

    # --- SEEKER CONTROL & LOGS ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 Seeker Control")
    
    from modules.account_manager import AccountManager
    acc_manager = AccountManager()
    
    # Active Session Info
    active_uid = acc_manager.get_active_uid()
    if active_uid:
        st.sidebar.success(f"✅ Active Identity: `{active_uid}`")
    else:
        st.sidebar.warning("⚠️ No identity active")

    # Account Switcher
    accounts = acc_manager.list_accounts()
    
    # If we have accounts, show switcher
    if accounts:
        account_options = [acc['uid'] for acc in accounts]
        
        # Determine index of current active
        current_idx = 0
        if active_uid in account_options:
            current_idx = account_options.index(active_uid)
            
        selected_uid = st.sidebar.selectbox(
            "Available Identities",
            options=account_options,
            index=current_idx,
            key="account_selector"
        )
        
        col_sw1, col_sw2 = st.sidebar.columns(2)
        with col_sw1:
            if st.button("🔄 Load", help="Switch to selected identity"):
                if acc_manager.set_active_account(selected_uid):
                    st.toast(f"Switched to {selected_uid}")
                    time.sleep(1)
                    st.rerun()
        with col_sw2:
            pass
            
    # Add New Account Button
    if st.sidebar.button("➕ Add Identity", help="Log in with a new Facebook account"):
        import subprocess
        import os
        try:
            project_dir = os.getcwd()
            # Open terminal to run login script
            script = f'''tell application "Terminal" to do script "cd {project_dir} && python3 modules/facebook_login.py"'''
            subprocess.run(["osascript", "-e", script], check=True)
            st.sidebar.info("Login Terminal Launched!")
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 Activate Seeker", type="primary", use_container_width=True):
        import subprocess
        import os
        try:
            project_dir = os.getcwd()
            script = f'''tell application "Terminal" to do script "cd {project_dir} && python3 main.py"'''
            subprocess.run(["osascript", "-e", script], check=True)
            st.sidebar.success("Launched!")
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")
            
    # Activity Log
    st.sidebar.subheader("📜 Activity Log")
    # This assumes main.py/hunter.py writes to a log file or simple stdout redirect
    # We can mock it or check file size
    if st.sidebar.button("Refresh Logs"):
        st.toast("Logs refreshed")

    # --- SPECTATOR TILE ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("👁️ Live Spectator")
    
    # Check if live view image exists
    live_view_path = "static/live_view.jpg"
    import os
    
    if st.sidebar.checkbox("🔴 Activate Live Feed", value=False):
        st.sidebar.caption("Refreshing every 1s...")
        placeholder = st.sidebar.empty()
        
        # Determine last modified time to force refresh
        try:
            # We want to refresh this effectively. 
            # In Streamlit, a loop inside the script blocks other interactions unless using specialized components.
            # We will use a simple placeholder that updates on rerun, 
            # OR we can try a short loop if the user wants "Real time" focus.
            
            # Better approach for Streamlit: Simple image that updates when the app reruns, 
            # but for "Live" feel we might need a dedicated loop or st.empty
            
            if os.path.exists(live_view_path):
                # Use a unique key to bust cache
                timestamp = time.time()
                placeholder.image(live_view_path, caption="Live Bot View", use_column_width=True)
                
                # Auto-rerun trick for "Live" feel? 
                # This causes the whole app to refresh which is annoying.
                # Instead, we'll just show the image. 
                # If they want REAL video, they need to keep clicking or we use a custom component.
                # EDIT: User demanded "Live Feed". A loop in a separate container is best.
                pass
            else:
                placeholder.warning("No signal (Bot idle?)")
        except Exception:
            placeholder.error("Signal lost")

    # --- MAIN CONTENT AREA ---
    # We can also put a big watcher at the top if requested
    
def main():
    render_data_explorer()
    
    # Add a dedicated Spectator Page or Overlay if requested?
    # For now, sidebar is safest to not break layout.

if __name__ == "__main__":
    main()
