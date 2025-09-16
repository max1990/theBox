#!/usr/bin/env python3
"""
Tiny environment loader for TheBox
This script loads environment variables from mvp/env/.thebox.env before any other imports
Usage: python scripts/load_env.py <your_script.py>
"""

import sys
import os
from pathlib import Path

def load_thebox_env():
    """Load environment variables from mvp/env/.thebox.env"""
    # Get the path to the .thebox.env file
    env_file = Path(__file__).parent.parent / "mvp" / "env" / ".thebox.env"
    
    if env_file.exists():
        # Load using python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")
            return True
        except ImportError:
            # Fallback: manual parsing
            print("python-dotenv not available, using manual parsing")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"\'')
            print(f"Loaded environment from {env_file} (manual parsing)")
            return True
    else:
        print(f"Warning: Environment file not found at {env_file}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_env.py <your_script.py>")
        sys.exit(1)
    
    # Load environment
    load_thebox_env()
    
    # Run the target script
    target_script = sys.argv[1]
    if not os.path.exists(target_script):
        print(f"Error: Target script not found: {target_script}")
        sys.exit(1)
    
    # Execute the target script
    exec(open(target_script).read())
