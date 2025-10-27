#!/usr/bin/env python3
"""
Setup script for UCL OAuth Backend
Run this script to set up the backend environment
"""

import os
import sys
import subprocess

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print("✅ Python version is compatible")

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def create_env_file():
    """Create .env file from template"""
    env_file = ".env"
    env_example = "env.example"
    
    if os.path.exists(env_file):
        print(f"✅ {env_file} already exists")
        return
    
    if not os.path.exists(env_example):
        print(f"❌ {env_example} not found")
        sys.exit(1)
    
    # Copy example to .env
    with open(env_example, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print(f"✅ Created {env_file} from template")
    print("⚠️  Please edit .env file with your actual UCL API credentials")

def check_firebase_config():
    """Check if Firebase service account file exists"""
    firebase_file = "firebase-service-account.json"
    
    if os.path.exists(firebase_file):
        print("✅ Firebase service account file found")
    else:
        print("⚠️  Firebase service account file not found")
        print("   Please download it from Firebase Console > Project Settings > Service Accounts")
        print("   and place it as 'firebase-service-account.json' in the backend directory")

def main():
    """Main setup function"""
    print("🚀 Setting up UCL OAuth Backend...")
    print()
    
    check_python_version()
    install_dependencies()
    create_env_file()
    check_firebase_config()
    
    print()
    print("🎉 Setup complete!")
    print()
    print("Next steps:")
    print("1. Edit .env file with your UCL API credentials")
    print("2. Add firebase-service-account.json file")
    print("3. Run: python app.py")
    print()
    print("To get UCL API credentials:")
    print("1. Visit https://uclapi.com/")
    print("2. Create an account and register your app")
    print("3. Get your client_id and client_secret")

if __name__ == "__main__":
    main()


