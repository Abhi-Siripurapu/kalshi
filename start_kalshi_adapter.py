#!/usr/bin/env python3
"""
Standalone script to run just the Kalshi adapter for testing
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.kalshi import KalshiAdapter

load_dotenv()

async def simple_publisher(event):
    """Simple publisher that just logs events"""
    event_type = event.get("type", "unknown")
    venue_id = event.get("venue_id", "unknown")
    
    if event_type == "market_info":
        data = event["data"]
        print(f"📊 Market discovered: {data.market_id} - {data.title}")
    
    elif event_type == "book_snapshot":
        books = event["data"]
        for book in books:
            print(f"📖 Book snapshot: {book.market_id}/{book.outcome_id} - "
                  f"Best bid: {book.best_bid}¢, Best ask: {book.best_ask}¢")
    
    elif event_type == "health":
        health = event["data"]
        status = health.get("status", "unknown")
        latency = health.get("latency_p95_ms", "N/A")
        print(f"💗 Health: {venue_id} is {status} (P95 latency: {latency}ms)")
    
    elif event_type == "subscribed":
        print(f"✅ Subscribed to Kalshi channels")
    
    elif event_type == "error":
        error_data = event["data"]
        print(f"❌ Error: {error_data}")

async def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")
    
    if not api_key:
        print("❌ KALSHI_API_KEY environment variable is required")
        sys.exit(1)
    
    if not os.path.exists(private_key_path):
        print(f"❌ Private key file not found: {private_key_path}")
        print("   Please download your private key from Kalshi and save it as kalshi-key.pem")
        sys.exit(1)
    
    print("🚀 Starting Kalshi adapter...")
    print(f"   API Key: {api_key}")
    print(f"   Environment: {environment}")
    print(f"   Private Key: {private_key_path}")
    
    # Create adapter with specific markets to avoid rate limits
    target_markets = [
        "BIDEN25",     # Example political market
        "TRUMP25",     # Example political market  
        "HOUSE25",     # Example political market
    ]
    
    adapter = KalshiAdapter(
        api_key_id=api_key,
        private_key_path=private_key_path,
        target_markets=target_markets,  # Use specific markets
        publisher=simple_publisher,
        environment=environment
    )
    
    try:
        await adapter.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping adapter...")
        await adapter.stop()
        print("✅ Adapter stopped")

if __name__ == "__main__":
    asyncio.run(main())