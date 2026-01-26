"""
Example script demonstrating how to use the AccountCreator from Ghost module.
This creates a new Facebook account and verifies it with an SMS code.
"""
from modules.ghost import Ghost

def create_facebook_account():
    """
    Example function to create a new Facebook account.
    """
    # Initialize Ghost
    ghost = Ghost()
    ghost.execute()
    
    # Get AccountCreator instance
    account_creator = ghost.get_account_creator()
    
    # Account details (replace with actual values)
    first_name = "John"
    last_name = "Doe"
    email = "johndoe@example.com"
    password = "SecurePassword123!"
    phone_number = "+15551234567"
    
    # Create the account
    print("Creating Facebook account...")
    success = account_creator.create_account(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        phone_number=phone_number
    )
    
    if success:
        print("\n✅ Account creation initiated!")
        print("📱 Check your phone for the verification code")
        
        # Wait for user to receive SMS
        verification_code = input("\nEnter the verification code from SMS: ")
        
        # Verify the phone number
        verified = account_creator.verify_phone_number(verification_code)
        
        if verified:
            print("\n🎉 Account created and verified successfully!")
        else:
            print("\n❌ Verification failed")
    else:
        print("\n❌ Account creation failed")
    
    # Cleanup
    ghost.close()


if __name__ == "__main__":
    create_facebook_account()
