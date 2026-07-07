"""
Legacy test script for Riot API ingestion.

NOTE: This project currently uses the Henrik Dev API (see worker.py + test_henrik.py).
This file is retained for reference if you switch to the official Riot API later.

The Riot API key below is likely expired — get a new one from https://developer.riotgames.com/
"""

import asyncio
import os
import sys
import json

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

# This import will fail because worker.py no longer has RiotAPIClient
# Uncomment and update if you add Riot API support back
# from worker import RiotAPIClient, RateLimitConfig

API_KEY = config.get("RIOT_API_KEY", "")  # Get from Riot Developer Portal (.env)
REGION = "na"
ACCOUNT_REGION = "americas"


async def main():
    print("⚠️  This test script is for the official Riot API.")
    print("   The project currently uses Henrik Dev API.")
    print("   Run test_henrik.py instead.")
    print()
    print("   If you want to use the Riot API directly:")
    print("   1. Get an API key from https://developer.riotgames.com/")
    print("   2. Implement a RiotAPIClient in worker.py")
    print("   3. Update this script with the new import")


if __name__ == "__main__":
    asyncio.run(main())
