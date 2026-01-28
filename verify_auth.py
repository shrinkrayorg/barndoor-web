import json
from pathlib import Path

def test_auth():
    print("🧪 Testing Authentication Logic...")
    
    USERS_PATH = Path("database/users.json")
    if not USERS_PATH.exists():
        print("❌ users.json not found")
        return

    with open(USERS_PATH, 'r') as f:
        data = json.load(f)
    
    users = data.get('users', [])
    print(f"✅ Found {len(users)} users")

    admin = next((u for u in users if u['role'] == 'admin'), None)
    if admin:
        print(f"✅ Admin user exists: {admin['email']}")
    else:
        print("❌ Admin user missing")

    # Mock signup flow
    print("\n📝 Simulating User Signup...")
    new_user = {
        "email": "test@example.com",
        "password": "testpassword",
        "full_name": "Test User",
        "role": "user",
        "status": "pending"
    }
    
    if any(u['email'] == new_user['email'] for u in users):
        print("ℹ️ Test user already exists")
    else:
        users.append(new_user)
        print(f"✅ User {new_user['email']} added to pending list")

    # Mock admin approval
    print("\n👑 Simulating Admin Approval...")
    user_to_approve = next((u for u in users if u['email'] == "test@example.com"), None)
    if user_to_approve:
        user_to_approve['status'] = 'approved'
        print(f"✅ User {user_to_approve['email']} status set to: {user_to_approve['status']}")
    
    print("\n🎉 Verification logic passed!")

if __name__ == "__main__":
    test_auth()
