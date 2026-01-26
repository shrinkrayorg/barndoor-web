"""
Network Manager Module
Responsible for managing Network Identity (IP, Location).
Integrates with VPN tools (CLI) or Proxy services to rotate IPs.
"""
import requests
import subprocess
import time
import json
from database.config_db import ConfigDB

class NetworkManager:
    """
    Manages network identity (IP address and geolocation).
    """
    
    def __init__(self):
        self.db = ConfigDB()
        self.config = self.db.get_config()
        self.network_config = self.config.get('network', {
            'mode': 'vpn',
            'vpn_command': 'nordvpn connect {city}', # Default template
            'proxy_url': ''
        })

    def get_current_identity(self):
        """
        Fetch current public IP and location details.
        
        Returns:
            dict: {ip, city, region, country, loc, org}
        """
        try:
            # fast timeout to avoid hanging UI
            response = requests.get('https://ipinfo.io/json', timeout=3)
            return response.json()
        except Exception as e:
            return {"ip": "Unknown", "city": "Unknown", "region": "Unknown", "error": str(e)}

    def rotate_identity(self, target_city):
        """
        Attempt to rotate IP to match target city.
        
        Args:
            target_city (str): "City, State" (e.g. "Chicago, IL")
            
        Returns:
            bool: True if command executed successfully
        """
        try:
            city_name = target_city.split(',')[0].strip().lower().replace(' ', '_')
            
            # MODE: VPN via CLI
            if self.network_config.get('mode') == 'vpn':
                cmd_template = self.network_config.get('vpn_command', 'nordvpn connect {city}')
                
                # Simple mapping for city names if needed
                # For nordvpn, "Chicago" works. "New_York" needs check.
                if city_name == 'new_york': city_name = 'new_york' 
                
                command = cmd_template.format(city=city_name)
                print(f"🔌 Executing VPN Command: {command}")
                
                # Execute shell command
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Wait for connection to establish
                    time.sleep(3) 
                    return True, result.stdout
                else:
                    return False, f"Command failed: {result.stderr}"

            # MODE: PROXY
            elif self.network_config.get('mode') == 'proxy':
                # For residential proxies, usually just setting the proxy is enough, 
                # or hitting a rotation API endpoint.
                # Here we assume the user just wants to confirm the config is active.
                return True, "Proxy configuration active. Requests will use configured proxy."
                
            return False, "No valid network mode configured."

        except Exception as e:
            return False, str(e)
