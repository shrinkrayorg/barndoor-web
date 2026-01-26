#!/usr/bin/env python3
"""
Barnfind Menu Bar App
macOS menu bar application for controlling the Barnfind service.
"""
import rumps
import subprocess
import os
import json
from datetime import datetime
from pathlib import Path


class BarnfindApp(rumps.App):
    """
    macOS Menu Bar application for Barnfind.
    """
    
    def __init__(self):
        super(BarnfindApp, self).__init__(
            "🚗 Barnfind",
            icon=None,
            quit_button=None
        )
        
        self.project_dir = Path(__file__).parent
        self.db_path = self.project_dir / "database" / "ledger.json"
        self.log_path = self.project_dir / "barnfind.log"
        self.pid_file = self.project_dir / "barnfind.pid"
        
        # Menu items
        self.status_item = rumps.MenuItem("Status: Checking...", callback=None)
        self.separator1 = rumps.separator
        self.start_item = rumps.MenuItem("▶️  Start Service", callback=self.start_service)
        self.stop_item = rumps.MenuItem("⏹  Stop Service", callback=self.stop_service)
        self.restart_item = rumps.MenuItem("🔄 Restart Service", callback=self.restart_service)
        self.separator2 = rumps.separator
        self.stats_item = rumps.MenuItem("📊 Statistics", callback=self.show_stats)
        self.logs_item = rumps.MenuItem("📋 View Logs", callback=self.view_logs)
        self.separator3 = rumps.separator
        self.quit_item = rumps.MenuItem("Quit Barnfind", callback=self.quit_app)
        
        self.menu = [
            self.status_item,
            self.separator1,
            self.start_item,
            self.stop_item,
            self.restart_item,
            self.separator2,
            self.stats_item,
            self.logs_item,
            self.separator3,
            self.quit_item
        ]
        
        # Update status on launch
        self.update_status()
    
    def is_service_running(self):
        """Check if the Barnfind service is running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is running
            result = subprocess.run(
                ['ps', '-p', str(pid)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def update_status(self):
        """Update the status menu item."""
        if self.is_service_running():
            self.status_item.title = "Status: ✅ Running"
            self.start_item.set_callback(None)
            self.stop_item.set_callback(self.stop_service)
            self.title = "🚗"
        else:
            self.status_item.title = "Status: ⏸ Stopped"
            self.start_item.set_callback(self.start_service)
            self.stop_item.set_callback(None)
            self.title = "🚗💤"
    
    def start_service(self, _):
        """Start the Barnfind service."""
        try:
            # Start the service in background
            process = subprocess.Popen(
                ['python3', 'main.py'],
                cwd=str(self.project_dir),
                stdout=open(self.log_path, 'a'),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            rumps.notification(
                title="Barnfind Started",
                subtitle="Service is now running",
                message="Vehicle monitoring active"
            )
            
            self.update_status()
            
        except Exception as e:
            rumps.alert(
                title="Error Starting Service",
                message=str(e)
            )
    
    def stop_service(self, _):
        """Stop the Barnfind service."""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Kill the process
                subprocess.run(['kill', str(pid)])
                
                # Remove PID file
                self.pid_file.unlink()
                
                rumps.notification(
                    title="Barnfind Stopped",
                    subtitle="Service has been stopped",
                    message="Vehicle monitoring paused"
                )
            
            self.update_status()
            
        except Exception as e:
            rumps.alert(
                title="Error Stopping Service",
                message=str(e)
            )
    
    def restart_service(self, _):
        """Restart the Barnfind service."""
        self.stop_service(None)
        import time
        time.sleep(2)
        self.start_service(None)
    
    def show_stats(self, _):
        """Show statistics from the database."""
        try:
            if not self.db_path.exists():
                rumps.alert(
                    title="No Data",
                    message="Database not found. Run the service first."
                )
                return
            
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            listings = data.get('listings', {})
            total_listings = len(listings.get('1', []))  # TinyDB structure
            
            # Get latest run info from logs
            latest_run = "Never"
            if self.log_path.exists():
                with open(self.log_path, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "PIPELINE RUN" in line:
                            # Extract timestamp from log
                            try:
                                timestamp = line.split("PIPELINE RUN - ")[1].split("\n")[0]
                                latest_run = timestamp
                            except:
                                pass
                            break
            
            message = f"""
Total Listings: {total_listings}
Last Run: {latest_run}
Service Status: {"Running" if self.is_service_running() else "Stopped"}
            """
            
            rumps.alert(
                title="📊 Barnfind Statistics",
                message=message.strip()
            )
            
        except Exception as e:
            rumps.alert(
                title="Error Loading Stats",
                message=str(e)
            )
    
    def view_logs(self, _):
        """Open logs in Console app."""
        try:
            if self.log_path.exists():
                subprocess.run(['open', '-a', 'Console', str(self.log_path)])
            else:
                rumps.alert(
                    title="No Logs",
                    message="Log file not found. Service hasn't run yet."
                )
        except Exception as e:
            rumps.alert(
                title="Error Opening Logs",
                message=str(e)
            )
    
    def quit_app(self, _):
        """Quit the menu bar app (optionally stop service)."""
        if self.is_service_running():
            response = rumps.alert(
                title="Barnfind is Running",
                message="Do you want to stop the service before quitting?",
                ok="Stop & Quit",
                cancel="Quit Only"
            )
            
            if response == 1:  # OK clicked
                self.stop_service(None)
        
        rumps.quit_application()


if __name__ == "__main__":
    app = BarnfindApp()
    app.run()
