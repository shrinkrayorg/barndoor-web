#!/usr/bin/env python3
"""
Barndoor Setup Script
Interactive configuration wizard and application launcher.

This script guides you through:
1. Configure API keys (.env file)
2. Configure application settings (config.py)
3. Create Facebook account (optional)
4. Launch the main application

Usage:
    python3 setup.py
"""
import os
import sys
import subprocess


def print_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step_number, description):
    """Print a step indicator."""
    print(f"\n[STEP {step_number}] {description}")
    print("-" * 60)


def configure_env():
    """Configure the .env file with API keys."""
    print_step(1, "Configure API Keys (.env)")
    
    print("\nEnter your API credentials:")
    print("(Press Enter to skip and use placeholder values)")
    
    carfax_api_key = input("\n  CARFAX API Key: ").strip() or "your_carfax_api_key_here"
    twilio_sid = input("  Twilio SID: ").strip() or "your_twilio_sid_here"
    twilio_token = input("  Twilio Token: ").strip() or "your_twilio_token_here"
    sendgrid_api_key = input("  SendGrid API Key: ").strip() or "your_sendgrid_api_key_here"
    
    # Write to .env file
    env_content = f"""# API Keys and Credentials
CARFAX_API_KEY={carfax_api_key}
TWILIO_SID={twilio_sid}
TWILIO_TOKEN={twilio_token}
SENDGRID_API_KEY={sendgrid_api_key}
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n✅ .env file configured successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Error writing .env file: {e}")
        return False


def configure_config_py():
    """Configure the config.py file with application settings."""
    print_step(2, "Configure Application Settings (config.py)")
    
    print("\nEnter your application configuration:")
    
    # Target URLs
    print("\n  Target URLs (comma-separated list of marketplace URLs):")
    print("  Example: https://example.com/cars,https://another.com/vehicles")
    target_urls_input = input("  > ").strip()
    
    if target_urls_input:
        target_urls = [url.strip() for url in target_urls_input.split(',')]
    else:
        target_urls = ["https://example.com/listings"]
    
    # Geographic settings
    home_zip_code = input("\n  Home ZIP Code: ").strip() or "00000"
    
    # Contact information
    phone_number = input("  Phone Number (format: +1234567890): ").strip() or "+1234567890"
    from_email = input("  From Email (verified in SendGrid): ").strip() or "barnfind@yourdomain.com"
    to_email = input("  To Email (your email): ").strip() or "your-email@example.com"
    
    # Read current config.py
    try:
        with open('config.py', 'r') as f:
            config_content = f.read()
    except Exception as e:
        print(f"\n❌ Error reading config.py: {e}")
        return False
    
    # Update config.py content
    # Replace TARGET_URLS
    urls_str = ",\n    ".join([f'"{url}"' for url in target_urls])
    new_urls_section = f"""TARGET_URLS = [
    {urls_str}
]"""
    
    # Find and replace sections
    import re
    
    # Replace TARGET_URLS section
    config_content = re.sub(
        r'TARGET_URLS = \[.*?\]',
        new_urls_section,
        config_content,
        flags=re.DOTALL
    )
    
    # Replace individual values
    config_content = re.sub(
        r'HOME_ZIP_CODE = ".*?"',
        f'HOME_ZIP_CODE = "{home_zip_code}"',
        config_content
    )
    
    config_content = re.sub(
        r'PHONE_NUMBER = ".*?"',
        f'PHONE_NUMBER = "{phone_number}"',
        config_content
    )
    
    config_content = re.sub(
        r'FROM_EMAIL = ".*?"',
        f'FROM_EMAIL = "{from_email}"',
        config_content
    )
    
    config_content = re.sub(
        r'TO_EMAIL = ".*?"',
        f'TO_EMAIL = "{to_email}"',
        config_content
    )
    
    # Write updated config.py
    try:
        with open('config.py', 'w') as f:
            f.write(config_content)
        print("\n✅ config.py configured successfully!")
        
        # Show summary
        print("\n📋 Configuration Summary:")
        print(f"  • Target URLs: {len(target_urls)} URL(s)")
        print(f"  • Home ZIP: {home_zip_code}")
        print(f"  • Phone: {phone_number}")
        print(f"  • Email: {to_email}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error writing config.py: {e}")
        return False


def create_facebook_account():
    """Optionally run the account creation script."""
    print_step(3, "Create Facebook Account (Optional)")
    
    print("\nWould you like to create a new Facebook account?")
    print("This will launch the interactive account creator.")
    
    response = input("\nCreate account? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n🚀 Launching account creator...")
        print("=" * 60)
        
        try:
            # Run the account creation script
            result = subprocess.run(
                ['python3', 'create_account_interactive.py'],
                check=False
            )
            
            if result.returncode == 0:
                print("\n✅ Account creation completed!")
            else:
                print("\n⚠️  Account creation exited")
            
            return True
        except Exception as e:
            print(f"\n❌ Error running account creator: {e}")
            return False
    else:
        print("\n⏭️  Skipped account creation")
        return True


def launch_application():
    """Optionally launch the main application."""
    print_step(4, "Launch Barndoor Application")
    
    print("\nWould you like to launch the Barndoor application now?")
    print("This will start the automated vehicle market analysis system.")
    
    response = input("\nLaunch application? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n🚀 Launching Barndoor...")
        print("=" * 60)
        print("\n📌 Press Ctrl+C to stop the application\n")
        
        try:
            # Run the main application
            subprocess.run(['python3', 'main.py'], check=False)
        except KeyboardInterrupt:
            print("\n\n🛑 Application stopped by user")
        except Exception as e:
            print(f"\n❌ Error running application: {e}")
        
        return True
    else:
        print("\n⏭️  Skipped application launch")
        print("\n💡 To launch manually later, run: python3 main.py")
        return True


def main():
    """Main setup workflow."""
    print_header("🚗 Barndoor Setup Wizard")
    
    print("\nWelcome to the Barndoor setup wizard!")
    print("This tool will help you configure and launch the application.")
    
    input("\nPress Enter to begin...")
    
    # Step 1: Configure .env
    if not configure_env():
        print("\n❌ Setup failed at Step 1")
        sys.exit(1)
    
    # Step 2: Configure config.py
    if not configure_config_py():
        print("\n❌ Setup failed at Step 2")
        sys.exit(1)
    
    # Step 3: Create Facebook account (optional)
    if not create_facebook_account():
        print("\n⚠️  Setup continued with warnings at Step 3")
    
    # Step 4: Launch application (optional)
    launch_application()
    
    # Final message
    print_header("✅ Setup Complete")
    
    print("\nYour Barndoor application is configured and ready!")
    print("\n📚 Quick Reference:")
    print("  • Launch app: python3 main.py")
    print("  • Web interface: python3 web_server.py (then visit http://localhost:5050)")
    print("  • Create account: python3 create_account_interactive.py")
    print("  • macOS app: Double-click Barndoor.app.command")
    
    print("\n" + "=" * 60)
    print("Happy hunting! 🚗")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
