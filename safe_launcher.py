import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
import runpy

# Setup status file path
PROJECT_DIR = Path(__file__).parent
STATUS_FILE = PROJECT_DIR / 'database' / 'scan_status.json'

def write_error(error_msg):
    try:
        STATUS_FILE.parent.mkdir(exist_ok=True)
        with open(STATUS_FILE, 'w') as f:
            json.dump({
                'active': False,
                'status': f"Startup Error: {error_msg}",
                'percent': 0,
                'updated_at': datetime.now().isoformat()
            }, f)
        print(f"❌ Wrote error to status file: {error_msg}")
    except Exception as e:
        print(f"Failed to write status file: {e}")

if __name__ == "__main__":
    print("🛡️ Safe Launcher: Starting main.py...")
    
    # Initialize status as "Booting..." to prove launcher is running
    try:
        STATUS_FILE.parent.mkdir(exist_ok=True)
        with open(STATUS_FILE, 'w') as f:
            json.dump({
                'active': True,
                'status': "Booting...",
                'percent': 0,
                'updated_at': datetime.now().isoformat()
            }, f)
    except Exception:
        pass

    try:
        # Execute main.py as the main script
        # Pass through all arguments
        sys.argv[0] = str(PROJECT_DIR / 'main.py')
        runpy.run_path(str(PROJECT_DIR / 'main.py'), run_name='__main__')
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ CRITICAL CRASH IN MAIN.PY: {error_msg}")
        traceback.print_exc()
        write_error(error_msg)
        sys.exit(1)
    except SystemExit as e:
        if e.code != 0:
            write_error(f"System Exit: {e.code}")
        raise
