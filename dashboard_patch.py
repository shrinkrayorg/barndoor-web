
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from database.config_db import ConfigDB

def render_access_portal():
    """Render the configuration settings page."""
    st.markdown("## ⚙️ Access Portal (Settings)")
    st.info("Configure your search parameters and system preferences here.")
    
    config_db = ConfigDB()
    current_config = config_db.get_config()
    
    with st.form("settings_form"):
        st.subheader("📍 Search Configuration")
        st.caption("Define your baseline market location and radius")
        
        col1, col2 = st.columns(2)
        
        with col1:
            location = st.text_input(
                "City, State Label",
                value=current_config.get("search_location", "Glenview, IL"),
                help="The central point for your search radius."
            )
            
        with col2:
            zip_code = st.text_input(
                "Zip Code",
                value=current_config.get("search_zip_code", "60025"),
                help="The zip code used for API queries."
            )
            
        radius = st.number_input(
            "Default Radius (miles)",
            min_value=10,
            max_value=500,
            value=int(current_config.get("search_radius", 250)),
            step=10
        )
        
        st.markdown("---")
        st.subheader("💰 Vehicle Value Tiers")
        st.caption("Categorize makes/models to determine base value scores. Enter one per line or separated by commas.")
        
        tier1 = st.text_area(
            "High Value (Tier 1)",
            value=", ".join(current_config.get("value_tiers", {}).get("tier_1", [])),
            height=100,
            help="These receive the highest score bonus (+40 pts)"
        )
        
        tier2 = st.text_area(
            "Mid Value (Tier 2)",
            value=", ".join(current_config.get("value_tiers", {}).get("tier_2", [])),
            height=100,
            help="These receive a moderate score bonus (+20 pts)"
        )
        
        tier3 = st.text_area(
            "Low Value (Tier 3)",
            value=", ".join(current_config.get("value_tiers", {}).get("tier_3", [])),
            height=100,
            help="These receive a small score bonus (+5 pts)"
        )
        
        st.markdown("---")
        
        if st.form_submit_button("Save Configuration", type="primary"):
            # Process Tiers
            t1_list = [x.strip().lower() for x in tier1.replace('\n', ',').split(',') if x.strip()]
            t2_list = [x.strip().lower() for x in tier2.replace('\n', ',').split(',') if x.strip()]
            t3_list = [x.strip().lower() for x in tier3.replace('\n', ',').split(',') if x.strip()]
            
            new_config = {
                "search_location": location,
                "search_zip_code": zip_code,
                "search_radius": radius,
                "value_tiers": {
                    "tier_1": t1_list,
                    "tier_2": t2_list,
                    "tier_3": t3_list
                }
            }
            
            # Update Config
            config_db.update_config(new_config)
            st.success("✅ Configuration saved successfully! Run the main application to apply changes.")
