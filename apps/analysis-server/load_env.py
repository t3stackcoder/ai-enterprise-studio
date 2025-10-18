"""
Load environment variables from .env file
Import this at the top of files that need env vars
"""
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}, using defaults")
