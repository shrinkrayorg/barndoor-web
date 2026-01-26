#!/usr/bin/env python3
"""
Barndoor GUI Application
A regular macOS application with a window interface for controlling Barndoor.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import time
import json
from pathlib import Path


class BarnfindGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚗 Barndoor - Vehicle Market Analysis")
        self.root.geometry("600x500")
        
        self.project_dir = Path(__file__).parent
        self.db_path = self.project_dir / "database" / "ledger.json"
        self.log_path = self.project_dir / "barnfind.log"
        self.pid_file = self.project_dir / "barnfind.pid"
        
        self.setup_ui()
        self.update_status()
        
        # Auto-refresh status every 5 seconds
        self.auto_refresh()
    
    def setup_ui(self):
        """Create the user interface."""
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🚗 Barndoor",
            font=("Helvetica", 24, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Main content area
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status section
        status_frame = tk.LabelFrame(main_frame, text="Service Status", padx=10, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(
            status_frame,
            text="⏸ Service Stopped",
            font=("Helvetica", 14),
            fg="orange"
        )
        self.status_label.pack()
        
        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = tk.Button(
            button_frame,
            text="▶️  Start Service",
            command=self.start_service,
            bg="#27ae60",
            fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.stop_btn = tk.Button(
            button_frame,
            text="⏹  Stop Service",
            command=self.stop_service,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 12, "bold"),
            padx=20,
            pady=10,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Statistics section
        stats_frame = tk.LabelFrame(main_frame, text="Statistics", padx=10, pady=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Label(
            stats_frame,
            text="Loading statistics...",
            font=("Courier", 11),
            justify=tk.LEFT,
            anchor="w"
        )
        self.stats_text.pack(fill=tk.X)
        
        # Logs section
        logs_frame = tk.LabelFrame(main_frame, text="Recent Logs", padx=10, pady=10)
        logs_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            logs_frame,
            height=10,
            font=("Courier", 9),
            bg="#f8f9fa",
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Refresh logs button
        refresh_btn = tk.Button(
            logs_frame,
            text="🔄 Refresh Logs",
            command=self.update_logs,
            cursor="hand2"
        )
        refresh_btn.pack(pady=(5, 0))
    
    def is_service_running(self):
        """Check if the Barnfind service is running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            result = subprocess.run(
                ['ps', '-p', str(pid)],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def update_status(self):
        """Update the status display."""
        if self.is_service_running():
            self.status_label.config(text="✅ Service Running", fg="#27ae60")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="⏸ Service Stopped", fg="#e67e22")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        
        self.update_stats()
        self.update_logs()
    
    def update_stats(self):
        """Update statistics display."""
        try:
            if not self.db_path.exists():
                self.stats_text.config(text="No data yet - start the service to begin")
                return
            
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            listings = data.get('listings', {})
            total = len(listings.get('1', []))
            
            # Get last run time from logs
            last_run = "Never"
            if self.log_path.exists():
                with open(self.log_path, 'r') as f:
                    for line in reversed(f.readlines()[-100:]):
                        if "PIPELINE RUN" in line:
                            try:
                                last_run = line.split("PIPELINE RUN - ")[1].strip()
                            except:
                                pass
                            break
            
            stats = f"""Total Listings: {total}
Last Run: {last_run}
Status: {"Running" if self.is_service_running() else "Stopped"}"""
            
            self.stats_text.config(text=stats)
        except Exception as e:
            self.stats_text.config(text=f"Error loading stats: {e}")
    
    def update_logs(self):
        """Update logs display."""
        try:
            if not self.log_path.exists():
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, "No logs yet - start the service to begin\n")
                return
            
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                recent = ''.join(lines[-50:])  # Last 50 lines
            
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, recent)
            self.log_text.see(tk.END)  # Scroll to bottom
        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error loading logs: {e}\n")
    
    def start_service(self):
        """Start the Barnfind service."""
        def run():
            try:
                # Start the service
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
                
                # Update UI
                self.root.after(0, lambda: messagebox.showinfo(
                    "Service Started",
                    "Barndoor service is now running!\n\nThe pipeline will execute every 10 minutes."
                ))
                self.root.after(0, self.update_status)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"Failed to start service:\n{e}"
                ))
        
        threading.Thread(target=run, daemon=True).start()
    
    def stop_service(self):
        """Stop the Barnfind service."""
        def run():
            try:
                if self.pid_file.exists():
                    with open(self.pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    subprocess.run(['kill', str(pid)])
                    self.pid_file.unlink()
                    
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Service Stopped",
                        "Barndoor service has been stopped."
                    ))
                    self.root.after(0, self.update_status)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"Failed to stop service:\n{e}"
                ))
        
        threading.Thread(target=run, daemon=True).start()
    
    def auto_refresh(self):
        """Auto-refresh status every 5 seconds."""
        self.update_status()
        self.root.after(5000, self.auto_refresh)


def main():
    root = tk.Tk()
    app = BarnfindGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
