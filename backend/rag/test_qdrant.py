import os
import sys

from qdrant_client import QdrantClient
from setup_collection import create_coaching_collection

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

def main():
    print(f"Connecting to Qdrant at {config.QDRANT_HOST}:{config.QDRANT_PORT}...")
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT, api_key=config.QDRANT_API_KEY, https=config.QDRANT_HTTPS, timeout=60.0)
    print("Creating coaching_knowledge collection...")
    try:
        create_coaching_collection(client)
        print("Collection created successfully!")
    except Exception as e:
        print(f"Error creating collection: {e}")

if __name__ == "__main__":
    main()
