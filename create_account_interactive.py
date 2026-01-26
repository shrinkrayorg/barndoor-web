"""
Example script for creating Facebook accounts using the AccountCreator.
This demonstrates how to use the account creation functionality.

Usage:
    python create_account_interactive.py

Note: 
    - Ensure Ghost module is initialized first
    - Have your verification phone ready to receive SMS codes
    - Facebook may detect automation - use responsibly
"""
from modules import Ghost
import getpass


def main():
    """Interactive account creation workflow."""
    print("=" * 60)
    print("🎭 Facebook Account Creator")
    print("=" * 60)
    print()
    
    # Initialize Ghost
    print("Initializing browser session...")
    ghost = Ghost()
    ghost.execute()
    
    # Get user input
    print("\nEnter account details:")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    phone_number = input("Phone Number (format: +1234567890): ").strip()
    
    # Confirm
    print("\n" + "=" * 60)
    print("Account Details:")
    print(f"Name: {first_name} {last_name}")
    print(f"Email: {email}")
    print(f"Phone: {phone_number}")
    print("=" * 60)
    
    confirm = input("\nProceed with account creation? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Account creation cancelled")
        ghost.close()
        return
    
    # Create account
    print("\n🔨 Creating account...")
    creator = ghost.get_account_creator()
    success = creator.create_account(first_name, last_name, email, password, phone_number)
    
    if success:
        print("✅ Account creation initiated!")
        print("\n📱 Check your phone for verification code...")
        
        # Wait for verification code
        verification_code = input("\nEnter verification code: ").strip()
        
        if verification_code:
            print("🔒 Verifying phone number...")
            verified = creator.verify_phone_number(verification_code)
            
            if verified:
                print("✅ Account verified successfully!")
            else:
                print("❌ Verification failed")
        else:
            print("⚠️  No verification code entered")
    else:
        print("❌ Account creation failed")
    
    # Cleanup
    print("\n🧹 Closing browser...")
    ghost.close()
    print("✓ Done")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
