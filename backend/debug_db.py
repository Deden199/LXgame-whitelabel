#!/usr/bin/env python3
"""
Debug provider data in database
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def debug_db_providers():
    """Debug provider data in database"""
    
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL must be set")
        return False
    
    db_name = os.environ.get('DB_NAME', 'gaming_platform')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        print("🔍 Debugging provider data in database...")
        
        # Check what fields exist in games
        sample_game = await db.games.find_one()
        if sample_game:
            print(f"\nSample game fields:")
            for key, value in sample_game.items():
                if 'provider' in key.lower():
                    print(f"   {key}: {value}")
        
        # Check unique provider_name values
        provider_names = await db.games.distinct("provider_name")
        print(f"\nUnique provider_name values ({len(provider_names)}):")
        for name in sorted(provider_names):
            count = await db.games.count_documents({"provider_name": name})
            print(f"   '{name}': {count} games")
        
        # Check unique provider_slug values
        provider_slugs = await db.games.distinct("provider_slug")
        print(f"\nUnique provider_slug values ({len(provider_slugs)}):")
        for slug in sorted(provider_slugs):
            count = await db.games.count_documents({"provider_slug": slug})
            print(f"   '{slug}': {count} games")
        
        # Check unique provider_id values
        provider_ids = await db.games.distinct("provider_id")
        print(f"\nUnique provider_id values ({len(provider_ids)}):")
        for pid in sorted(provider_ids):
            count = await db.games.count_documents({"provider_id": pid})
            print(f"   '{pid}': {count} games")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_db_providers())