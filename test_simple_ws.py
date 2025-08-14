#!/usr/bin/env python3
"""
Simple WebSocket test based exactly on Kalshi documentation
"""

import asyncio
import base64
import json
import time
import websockets
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
KEY_ID = os.getenv("KALSHI_API_KEY")
PRIVATE_KEY_PATH = "./kalshi-key.pem"
WS_URL = "wss://demo-api.kalshi.co/trade-api/ws/v2"

def sign_pss_text(private_key, text: str) -> str:
    """Sign message using RSA-PSS"""
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def create_headers(private_key, method: str, path: str) -> dict:
    """Create authentication headers"""
    # Use current timestamp - WebSocket auth might need very recent timestamp
    # Even though system clock is wrong, let's use what we have
    timestamp = str(int(time.time()))
    msg_string = timestamp + method + path.split('?')[0]
    signature = sign_pss_text(private_key, msg_string)
    
    print(f"Debug: Using timestamp: {timestamp} ({time.ctime(int(timestamp))})")
    print(f"Debug: Message to sign: '{msg_string}'")
    print(f"Debug: Signature: {signature[:50]}...")
    
    return {
        "KALSHI-ACCESS-KEY": KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }

async def test_websocket():
    """Test WebSocket connection"""
    if not KEY_ID:
        print("ERROR: KALSHI_API_KEY not found")
        return
    
    # Load private key
    try:
        with open(PRIVATE_KEY_PATH, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        print("✓ Private key loaded successfully")
    except Exception as e:
        print(f"ERROR: Could not load private key: {e}")
        return
    
    # Create WebSocket headers
    ws_headers = create_headers(private_key, "GET", "/trade-api/ws/v2")
    
    print(f"Connecting to: {WS_URL}")
    print(f"Headers: {ws_headers}")
    
    try:
        async with websockets.connect(WS_URL, additional_headers=ws_headers) as websocket:
            print("🎉 Connected successfully!")
            
            # Test basic ping
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())