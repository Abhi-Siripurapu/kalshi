import base64
import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class KalshiAuth:
    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        self.private_key = self._load_private_key(private_key_path)
    
    def _load_private_key(self, key_path: str):
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(), 
                password=None, 
                backend=default_backend()
            )
    
    def _sign_message(self, message: str) -> str:
        message_bytes = message.encode('utf-8')
        signature = self.private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    def create_headers(self, method: str, path: str) -> dict:
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method}{path.split('?')[0]}"
        signature = self._sign_message(message)
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
    
    def create_ws_headers(self) -> dict:
        # WebSocket uses milliseconds timestamp (per official docs)
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}GET/trade-api/ws/v2"
        signature = self._sign_message(message)
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp
        }