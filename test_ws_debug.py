#!/usr/bin/env python3
"""
Debug WebSocket connection with detailed logging
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.kalshi.adapter import KalshiAdapter

load_dotenv()

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_debug():
    """Test WebSocket connection with debug output"""
    api_key_id = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")
    
    if not api_key_id:
        print("ERROR: KALSHI_API_KEY not found in environment")
        return
        
    if not os.path.exists(private_key_path):
        print(f"ERROR: Private key not found at {private_key_path}")
        return
    
    print(f"✓ API Key ID: {api_key_id[:10]}...")
    print(f"✓ Private key path: {private_key_path}")
    
    # Event counter for debugging
    event_count = {"total": 0, "by_type": {}}
    
    async def debug_publisher(event):
        event_count["total"] += 1
        event_type = event.get("type", "unknown")
        event_count["by_type"][event_type] = event_count["by_type"].get(event_type, 0) + 1
        
        print(f"Event #{event_count['total']}: {event_type}")
        
        if event_type == "market_info":
            market = event["data"]
            print(f"  Market: {market.get('market_id')} - {market.get('title', '')[:50]}...")
        elif event_type == "book_snapshot":
            books = event["data"]
            if books:
                book = books[0]
                print(f"  Book snapshot: {book.market_id} - Bid: {book.best_bid}, Ask: {book.best_ask}")
        elif event_type == "book_delta":
            delta = event["data"]
            print(f"  Book delta: {delta}")
        elif event_type == "health":
            health = event["data"]
            print(f"  Health: {health.get('status')} - Latency P95: {health.get('latency_p95_ms')}ms")
        elif event_type == "subscribed":
            print(f"  Subscription confirmed: {event['data']}")
        elif event_type == "error":
            print(f"  ERROR: {event['data']}")
        
        # Print summary every 10 events
        if event_count["total"] % 10 == 0:
            print(f"Summary after {event_count['total']} events: {event_count['by_type']}")
    
    # Create adapter with empty target markets (auto-discover 5)
    environment = os.getenv("KALSHI_ENVIRONMENT", "demo")
    adapter = KalshiAdapter(
        api_key_id=api_key_id,
        private_key_path=private_key_path,
        target_markets=[],  # Auto-discover
        publisher=debug_publisher,
        environment=environment
    )
    
    try:
        print("Starting Kalshi adapter...")
        await adapter.start()
    except KeyboardInterrupt:
        print("\\n⏹️  Stopping adapter...")
        await adapter.stop()
        print(f"Final event count: {event_count['total']}")
        print(f"Events by type: {event_count['by_type']}")

if __name__ == "__main__":
    asyncio.run(test_debug())