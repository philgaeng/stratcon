#!/usr/bin/env python3
"""
Utility to load environment variables from env.local file.
"""

import os
from pathlib import Path


def load_env_local():
    """Load environment variables from env.local file in project root."""
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / "env.local"
    
    if not env_file.exists():
        return False
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                # Only set if not already set (don't override existing env vars)
                if key and not os.getenv(key):
                    os.environ[key] = value
    
    return True


if __name__ == "__main__":
    load_env_local()
    print("✅ Environment variables loaded from env.local")
    print(f"   AWS_REGION: {os.getenv('AWS_REGION', 'NOT SET')}")
    print(f"   AWS_ACCESS_KEY_ID: {'SET' if os.getenv('AWS_ACCESS_KEY_ID') else 'NOT SET'}")
    print(f"   AWS_SECRET_ACCESS_KEY: {'SET' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
    print(f"   SES_SENDER_EMAIL: {os.getenv('SES_SENDER_EMAIL', 'NOT SET')}")

