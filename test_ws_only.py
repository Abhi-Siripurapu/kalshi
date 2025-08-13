#!/usr/bin/env python3
"""
Test WebSocket connection only with exact format from Kalshi docs
"""

import asyncio
import base64
import time
import websockets
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

API_KEY = "6d7e4138-afce-47a3-ace2-495d6d801410"
WS_URL = "wss://demo-api.kalshi.co/trade-api/ws/v2"

def load_private_key():
    with open("kalshi-key.pem", "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def sign_message(private_key, message: str) -> str:
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

async def test_websocket():
    private_key = load_private_key()
    
    # Try different timestamp formats
    formats_to_try = [
        ("milliseconds", str(int(time.time() * 1000))),
        ("seconds", str(int(time.time()))),
    ]
    
    for format_name, timestamp in formats_to_try:
        print(f"\n🧪 Testing with {format_name}: {timestamp}")
        
        # Create signature
        message = f"{timestamp}GET/trade-api/ws/v2"
        signature = sign_message(private_key, message)
        
        headers = {
            "KALSHI-ACCESS-KEY": API_KEY,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }
        
        try:
            print(f"   Connecting with headers: {headers}")
            async with websockets.connect(WS_URL, additional_headers=headers) as ws:
                print(f"✅ Connected with {format_name}!")
                return
                
        except Exception as e:
            print(f"❌ Failed with {format_name}: {e}")
    
    print("\n❌ All WebSocket connection attempts failed")

if __name__ == "__main__":
    asyncio.run(test_websocket())