#!/usr/bin/env python3
"""
Test REST API authentication first
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.kalshi.auth import KalshiAuth

load_dotenv()

async def test_rest_api():
    """Test REST API to verify authentication works"""
    api_key_id = os.getenv("KALSHI_API_KEY")
    private_key_path = "./kalshi-key.pem"
    
    if not api_key_id:
        print("ERROR: KALSHI_API_KEY not found")
        return
    
    try:
        auth = KalshiAuth(api_key_id, private_key_path)
        print("✓ Auth object created successfully")
    except Exception as e:
        print(f"ERROR: Could not create auth: {e}")
        return
    
    # Test REST API call
    url = "https://demo-api.kalshi.co/trade-api/v2/exchange/status"
    headers = auth.create_headers("GET", "/trade-api/v2/exchange/status")
    
    print(f"Making request to: {url}")
    print(f"Headers: {headers}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("✅ REST API authentication successful!")
                    print(f"Response: {data}")
                else:
                    text = await response.text()
                    print(f"❌ REST API failed: {text}")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_rest_api())