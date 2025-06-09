#!/usr/bin/env python3
"""
Utility script to generate a valid Fernet encryption key
"""

from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

def generate_encryption_key():
    """Generate a new Fernet encryption key and save to .env file"""
    load_dotenv()
    
    # Generate a new key
    key = Fernet.generate_key().decode()
    
    # Check if .env file exists
    env_file = '.env'
    if os.path.exists(env_file):
        # Read existing content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Check if ENCRYPTION_KEY already exists
        key_exists = False
        new_lines = []
        for line in lines:
            if line.startswith('ENCRYPTION_KEY='):
                new_lines.append(f'ENCRYPTION_KEY={key}\n')
                key_exists = True
            else:
                new_lines.append(line)
        
        # Add key if it doesn't exist
        if not key_exists:
            new_lines.append(f'ENCRYPTION_KEY={key}\n')
        
        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
    else:
        # Create new .env file with key
        with open(env_file, 'w') as f:
            f.write(f'ENCRYPTION_KEY={key}\n')
    
    print(f"✅ Generated new encryption key: {key}")
    print(f"✅ Key saved to {env_file}")

if __name__ == "__main__":
    generate_encryption_key()
