#!/usr/bin/env python3
"""
Setup script for Advanced Futures Trading Bot
"""

import os
import sys
import shutil
from cryptography.fernet import Fernet

def setup_environment():
    """Set up the complete bot environment"""
    print("🚀 Setting up Advanced Futures Trading Bot...")
    
    # Create required directories
    directories = ['data', 'logs', 'config', 'database', 'exchanges', 'bot']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Check for .env file
    if not os.path.exists('.env'):
        # Create .env file with proper encryption key
        encryption_key = Fernet.generate_key().decode()
        
        with open('.env', 'w') as f:
            f.write("# Advanced Futures Trading Bot Configuration\n")
            f.write("# Required Settings\n")
            f.write("TELEGRAM_TOKEN=\n")
            f.write("ADMIN_ID=\n\n")
            f.write("# Security\n")
            f.write(f"ENCRYPTION_KEY={encryption_key}\n\n")
            f.write("# Trading Settings\n")
            f.write("DEFAULT_LEVERAGE=10\n")
            f.write("MAX_LEVERAGE=50\n")
            f.write("DEFAULT_POSITION_SIZE_PERCENT=5.0\n\n")
            f.write("# OAuth Configuration (Optional)\n")
            f.write("OAUTH_CALLBACK_URL=https://yourdomain.com/oauth/callback\n")
            f.write("KUCOIN_CLIENT_ID=\n")
            f.write("KUCOIN_CLIENT_SECRET=\n")
        
        print("✅ Created .env file with secure encryption key")
    
    # Check for required packages
    try:
        import dotenv
        import telegram
        import cryptography
        print("✅ Required packages are installed")
    except ImportError:
        print("⚠️ Installing required packages...")
        os.system(f"{sys.executable} -m pip install -r requirements.txt")
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your TELEGRAM_TOKEN and ADMIN_ID")
    print("2. Get your Telegram bot token from @BotFather")
    print("3. Get your Telegram user ID from @userinfobot")
    print("4. Run the bot with: python main.py")
    print("\n🔐 Security: Your encryption key has been automatically generated")
    print("💡 Tip: Start with testnet exchanges for safe practice!")

if __name__ == "__main__":
    setup_environment()
