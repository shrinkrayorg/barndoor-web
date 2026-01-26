"""
Account Manager Module
Manages multiple Facebook identities (sessions).
Allows saving, listing, and switching between different accounts.
"""
import json
import os
import shutil
from pathlib import Path

class AccountManager:
    def __init__(self):
        self.base_dir = Path('database')
        self.sessions_dir = self.base_dir / 'sessions'
        self.active_session_file = self.base_dir / 'session.json'
        
        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _extract_user_info(self, cookies):
        """Extract user ID from cookies."""
        uid = None
        for cookie in cookies:
            if cookie.get('name') == 'c_user':
                uid = cookie.get('value')
                break
        return uid

    def save_new_session(self, cookies):
        """
        Save a new session.
        1. Saves to database/sessions/session_{uid}.json
        2. Sets as active session.
        """
        uid = self._extract_user_info(cookies)
        if not uid:
            print("❌ No User ID found in cookies. Cannot save.")
            return False
            
        filename = f"session_{uid}.json"
        file_path = self.sessions_dir / filename
        
        data = {
            'uid': uid,
            'cookies': cookies,
            'last_updated': str(os.path.getmtime(self.active_session_file) if self.active_session_file.exists() else 0) 
        }
        
        # 1. Save to unique file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"✅ Saved session for user {uid}")
        
        # 2. Set as active
        self.set_active_account(uid)
        return True

    def list_accounts(self):
        """
        List all available accounts.
        Returns: List of dicts {'uid': str, 'path': Path}
        """
        accounts = []
        if not self.sessions_dir.exists():
            return []
            
        for file_path in self.sessions_dir.glob('session_*.json'):
            try:
                # Extract UID from filename or content
                # filename format: session_{uid}.json
                start = 'session_'
                end = '.json'
                name = file_path.name
                if name.startswith(start) and name.endswith(end):
                    uid = name[len(start):-len(end)]
                    accounts.append({'uid': uid, 'path': str(file_path)})
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        return accounts

    def set_active_account(self, uid):
        """
        Set the active account by copying the specific session file to session.json.
        """
        source = self.sessions_dir / f"session_{uid}.json"
        
        if not source.exists():
            print(f"❌ Session file for {uid} not found.")
            return False
            
        # Copy to active location
        try:
            shutil.copy(source, self.active_session_file)
            print(f"✅ Switched active account to {uid}")
            return True
        except Exception as e:
            print(f"❌ Error switching account: {e}")
            return False

    def get_active_uid(self):
        """Get the UID of the currently active session."""
        if not self.active_session_file.exists():
            return None
            
        try:
            with open(self.active_session_file, 'r') as f:
                data = json.load(f)
                # Try to get from root 'uid' if we added it, or extract from cookies
                if 'uid' in data:
                    return data['uid']
                return self._extract_user_info(data.get('cookies', []))
        except:
            return None
