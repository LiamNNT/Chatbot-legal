#!/usr/bin/env python3
"""
Simple script to start Orchestrator service with proper environment loading
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file properly
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Split only on first =
                key, value = line.split('=', 1)
                # Remove quotes if any
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value
                print(f"Loaded: {key}")

# Check required vars
if not os.getenv('OPENROUTER_API_KEY'):
    print("❌ ERROR: OPENROUTER_API_KEY not found in .env")
    sys.exit(1)

print(f"\n✓ Environment loaded")
print(f"  RAG_SERVICE_URL: {os.getenv('RAG_SERVICE_URL', 'Not set')}")
print(f"  PORT: {os.getenv('PORT', '8001')}")
print(f"\n🚀 Starting Orchestrator...")

# Start uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),  # Ensure lowercase
        reload=False
    )
