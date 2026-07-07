"""
Test script for Henrik Dev API integration + ETL pipeline.

Usage:
    python test_henrik.py                   # Fetch + save + ETL a match
    python test_henrik.py --fetch-only      # Only fetch and save JSON
    python test_henrik.py --etl-only FILE   # Only run ETL on a saved file
"""

import asyncio
import aiohttp
import json
import os
import sys

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

# Loaded from the environment / .env — never hardcode the key (see .env.example).
API_KEY = config.require("HENRIK_API_KEY")
BASE_URL = "https://api.henrikdev.xyz"
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")


async def fetch_and_save(name: str = "Friday", tag: str = "PlayZ") -> str | None:
    """Fetch a match from Henrik API and save to disk. Returns filepath."""
    headers = {"Authorization": API_KEY}

    async with aiohttp.ClientSession(headers=headers) as session:
        # Get account region
        acc_url = f"{BASE_URL}/valorant/v1/account/{name}/{tag}"
        print(f"Fetching account info: {acc_url}")
        async with session.get(acc_url) as acc_res:
            if acc_res.status != 200:
                print(f"Error fetching account: {acc_res.status} {await acc_res.text()}")
                return None
            acc_data = await acc_res.json()
            region = acc_data["data"]["region"]
            print(f"Player region: {region}")

        # Fetch matches
        url = f"{BASE_URL}/valorant/v3/matches/{region}/{name}/{tag}?size=1"
        print(f"Fetching matches: {url}")

        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                print(await response.text())
                return None

            data = await response.json()
            matches = data.get("data", [])
            print(f"Retrieved {len(matches)} matches.")

            if not matches:
                return None

            latest_match = matches[0]
            match_id = latest_match["metadata"]["matchid"]

            os.makedirs(DATA_DIR, exist_ok=True)
            filepath = os.path.join(DATA_DIR, f"{match_id}_henrik.json")
            with open(filepath, "w") as f:
                json.dump(latest_match, f, indent=2)
            print(f"Saved to {filepath}")
            return filepath


def run_etl(filepath: str):
    """Run the ETL pipeline on a saved match file."""
    from etl import process_match_file
    print(f"\nRunning ETL on: {filepath}")
    process_match_file(filepath)


async def main():
    args = sys.argv[1:]

    if "--etl-only" in args:
        idx = args.index("--etl-only")
        if idx + 1 < len(args):
            run_etl(args[idx + 1])
        else:
            print("Usage: python test_henrik.py --etl-only <filepath>")
        return

    fetch_only = "--fetch-only" in args
    filepath = await fetch_and_save()

    if filepath and not fetch_only:
        run_etl(filepath)


if __name__ == "__main__":
    asyncio.run(main())
