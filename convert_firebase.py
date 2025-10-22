#!/usr/bin/env python3
"""
Convert Firebase service account JSON to environment variable format
Run this script to convert your firebase-service-account.json to a single-line string
"""

import json
import sys
import os

def convert_firebase_config():
    """Convert Firebase service account JSON to environment variable format"""
    
    firebase_file = "firebase-service-account.json"
    
    if not os.path.exists(firebase_file):
        print(f"❌ {firebase_file} not found")
        print("Please download it from Firebase Console > Project Settings > Service Accounts")
        return
    
    try:
        # Read the JSON file
        with open(firebase_file, 'r') as f:
            firebase_config = json.load(f)
        
        # Convert to single-line string
        config_string = json.dumps(firebase_config)
        
        print("✅ Firebase service account converted successfully!")
        print()
        print("Add this to your environment variables:")
        print("=" * 50)
        print(f"FIREBASE_SERVICE_ACCOUNT={config_string}")
        print("=" * 50)
        print()
        print("For Railway/Render deployment:")
        print("1. Copy the line above")
        print("2. Paste it in your platform's environment variables")
        print("3. Make sure to include the entire string (it's very long)")
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in firebase-service-account.json")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    convert_firebase_config()
