#!/usr/bin/env python3
"""
Quick fix to update provider_name field in games based on existing provider_slug
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

# Provider slug to name mapping
PROVIDER_MAPPING = {
    "pragmatic-play": "Pragmatic Play",
    "pgsoft": "PGSoft", 
    "netent": "NetEnt",
    "microgaming": "Microgaming",
    "evolution": "Evolution",
    "habanero": "Habanero",
    "nolimit-city": "Nolimit City",
    "red-tiger": "Red Tiger",
    "hacksaw-gaming": "Hacksaw Gaming",
    "hacksaw": "Hacksaw Gaming",
    "playngo": "Play'n GO",
    "quickspin": "Quickspin",
    "relax-gaming": "Relax Gaming",
    "spribe": "Spribe",
    "cq9": "CQ9",
    "blueprint": "Blueprint Gaming",
    "elk": "ELK Studios", 
    "thunderkick": "Thunderkick",
    "push-gaming": "Push Gaming",
    "yggdrasil": "Yggdrasil"
}

async def fix_provider_names():
    """Fix provider_name field in games collection"""
    
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL must be set")
        return False
    
    db_name = os.environ.get('DB_NAME', 'gaming_platform')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        print("🔧 Fixing provider_name field in games...")
        
        # Get all games with provider_slug
        games_cursor = db.games.find({"provider_slug": {"$exists": True}})
        
        updates_count = 0
        total_count = 0
        
        async for game in games_cursor:
            total_count += 1
            provider_slug = game.get("provider_slug")
            current_provider_name = game.get("provider_name")
            
            if provider_slug and provider_slug in PROVIDER_MAPPING:
                expected_name = PROVIDER_MAPPING[provider_slug]
                
                if current_provider_name != expected_name:
                    await db.games.update_one(
                        {"_id": game["_id"]},
                        {"$set": {"provider_name": expected_name}}
                    )
                    updates_count += 1
                    print(f"   Updated {game.get('name', 'Unknown')}: '{current_provider_name}' -> '{expected_name}'")
        
        print(f"\n✅ Fixed {updates_count} games out of {total_count} total")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_provider_names())