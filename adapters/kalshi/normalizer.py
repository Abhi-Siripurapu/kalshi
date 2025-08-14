import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class NormalizedMarket:
    venue_id: str
    market_id: str
    title: str
    description: str
    resolution_source: str
    resolution_ts: int
    timezone: str
    currency: str
    outcomes: List[Dict]
    status: str
    created_ts: int
    mapping_tags: Dict


@dataclass
class NormalizedBook:
    venue_id: str
    market_id: str
    outcome_id: str
    ts_ns: int
    bids: List[Dict]  # [{"px_cents": int, "qty": int}]
    asks: List[Dict]  # [{"px_cents": int, "qty": int}]
    best_bid: Optional[int]
    best_ask: Optional[int]
    mid_px: Optional[float]
    sequence: int


@dataclass 
class NormalizedTrade:
    venue_id: str
    market_id: str
    outcome_id: str
    trade_id: str
    side: str
    px_cents: int
    qty: int
    fee_cents: int
    liquidity_flag: str
    ts_ns: int


@dataclass
class NormalizedHealth:
    venue_id: str
    status: str  # "healthy" | "degraded" | "down"
    reason: Optional[str]
    ts_ns: int
    latency_p50_ms: Optional[float]
    latency_p95_ms: Optional[float]


class KalshiNormalizer:
    def __init__(self):
        self.venue_id = "kalshi"
        
    def normalize_market(self, kalshi_market: Dict) -> Dict:
        """Convert Kalshi market format to canonical format"""
        
        # Extract resolution timestamp (Kalshi uses close_ts for when market stops trading)
        resolution_ts = kalshi_market.get("close_ts", int(time.time()))
        
        # Create outcomes - Kalshi binary markets have YES/NO
        outcomes = [
            {
                "id": "yes",
                "label": "YES", 
                "type": "binary",
                "mapping_tags": self._extract_mapping_tags(kalshi_market)
            },
            {
                "id": "no",
                "label": "NO",
                "type": "binary", 
                "mapping_tags": self._extract_mapping_tags(kalshi_market)
            }
        ]
        
        return {
            "venue_id": self.venue_id,
            "market_id": kalshi_market["ticker"],
            "title": kalshi_market.get("title", ""),
            "description": kalshi_market.get("subtitle", ""),
            "resolution_source": kalshi_market.get("rules", ""),
            "resolution_ts": resolution_ts,
            "timezone": "US/Eastern",  # Kalshi default
            "currency": "USD",
            "outcomes": outcomes,
            "status": self._normalize_status(kalshi_market.get("status", "open")),
            "created_ts": kalshi_market.get("open_ts", int(time.time())),
            "mapping_tags": self._extract_mapping_tags(kalshi_market)
        }
    
    def normalize_orderbook_snapshot(self, market_ticker: str, orderbook_data: Dict, recv_ts_ns: int) -> List[Dict]:
        """Convert Kalshi orderbook to canonical format
        
        Kalshi returns separate yes/no bids, we need to create books for both outcomes
        """
        books = []
        sequence = int(time.time_ns())
        
        # YES outcome book
        yes_bids = self._convert_kalshi_bids(orderbook_data.get("orderbook", {}).get("yes", []))
        yes_asks = self._derive_asks_from_no_bids(orderbook_data.get("orderbook", {}).get("no", []))
        
        yes_book = {
            "venue_id": self.venue_id,
            "market_id": market_ticker,
            "outcome_id": "yes",
            "ts_ns": recv_ts_ns,
            "bids": yes_bids,
            "asks": yes_asks,
            "best_bid": yes_bids[0]["px_cents"] if yes_bids else None,
            "best_ask": yes_asks[0]["px_cents"] if yes_asks else None,
            "mid_px": self._calculate_mid(yes_bids, yes_asks),
            "sequence": sequence
        }
        books.append(yes_book)
        
        # NO outcome book  
        no_bids = self._convert_kalshi_bids(orderbook_data.get("orderbook", {}).get("no", []))
        no_asks = self._derive_asks_from_yes_bids(orderbook_data.get("orderbook", {}).get("yes", []))
        
        no_book = {
            "venue_id": self.venue_id,
            "market_id": market_ticker,
            "outcome_id": "no", 
            "ts_ns": recv_ts_ns,
            "bids": no_bids,
            "asks": no_asks,
            "best_bid": no_bids[0]["px_cents"] if no_bids else None,
            "best_ask": no_asks[0]["px_cents"] if no_asks else None,
            "mid_px": self._calculate_mid(no_bids, no_asks),
            "sequence": sequence + 1
        }
        books.append(no_book)
        
        return books
    
    def normalize_websocket_message(self, message: Dict, recv_ts_ns: int) -> Optional[Dict]:
        """Normalize incoming WebSocket messages to canonical events"""
        msg_type = message.get("type")
        
        # Kalshi WebSocket messages have data in 'msg' field, not 'data'
        msg_data = message.get("msg", message.get("data", {}))
        
        if msg_type == "orderbook_snapshot":
            return {
                "type": "book_snapshot",
                "venue_id": self.venue_id,
                "data": self.normalize_orderbook_snapshot(
                    msg_data["market_ticker"],
                    {"orderbook": msg_data},
                    recv_ts_ns
                ),
                "ts_received_ns": recv_ts_ns
            }
            
        elif msg_type == "orderbook_delta":
            return {
                "type": "book_delta", 
                "venue_id": self.venue_id,
                "data": self._normalize_orderbook_delta(msg_data, recv_ts_ns),
                "ts_received_ns": recv_ts_ns
            }
            
        elif msg_type == "ticker":
            return {
                "type": "ticker",
                "venue_id": self.venue_id,
                "data": self._normalize_ticker(msg_data, recv_ts_ns),
                "ts_received_ns": recv_ts_ns
            }
            
        elif msg_type == "error":
            return {
                "type": "error",
                "venue_id": self.venue_id,
                "data": msg_data,
                "ts_received_ns": recv_ts_ns
            }
            
        elif msg_type == "subscribed":
            return {
                "type": "subscribed",
                "venue_id": self.venue_id, 
                "data": msg_data,
                "ts_received_ns": recv_ts_ns
            }
            
        return None
    
    def _convert_kalshi_bids(self, kalshi_bids: List) -> List[Dict]:
        """Convert Kalshi bid format [[price, qty], ...] to canonical format"""
        bids = []
        for price_qty in kalshi_bids:
            if len(price_qty) >= 2:
                bids.append({
                    "px_cents": int(price_qty[0]),
                    "qty": int(price_qty[1])
                })
        
        # Sort by price descending (best bid first)
        bids.sort(key=lambda x: x["px_cents"], reverse=True)
        return bids
    
    def _derive_asks_from_no_bids(self, no_bids: List) -> List[Dict]:
        """Convert NO bids to YES asks using 100-price relationship"""
        asks = []
        for price_qty in no_bids:
            if len(price_qty) >= 2:
                # NO bid at X cents = YES ask at (100-X) cents
                yes_ask_price = 100 - int(price_qty[0])
                if yes_ask_price > 0:
                    asks.append({
                        "px_cents": yes_ask_price,
                        "qty": int(price_qty[1])
                    })
        
        # Sort by price ascending (best ask first)
        asks.sort(key=lambda x: x["px_cents"])
        return asks
    
    def _derive_asks_from_yes_bids(self, yes_bids: List) -> List[Dict]:
        """Convert YES bids to NO asks using 100-price relationship"""
        asks = []
        for price_qty in yes_bids:
            if len(price_qty) >= 2:
                # YES bid at X cents = NO ask at (100-X) cents
                no_ask_price = 100 - int(price_qty[0])
                if no_ask_price > 0:
                    asks.append({
                        "px_cents": no_ask_price,
                        "qty": int(price_qty[1])
                    })
        
        # Sort by price ascending (best ask first)
        asks.sort(key=lambda x: x["px_cents"])
        return asks
    
    def _calculate_mid(self, bids: List[Dict], asks: List[Dict]) -> Optional[float]:
        """Calculate mid price from best bid and ask"""
        if not bids or not asks:
            return None
        
        best_bid = bids[0]["px_cents"]
        best_ask = asks[0]["px_cents"]
        return (best_bid + best_ask) / 2.0
    
    def _normalize_orderbook_delta(self, delta_data: Dict, recv_ts_ns: int) -> Dict:
        """Normalize orderbook delta message
        
        Kalshi delta format:
        {
            "market_ticker": "KXNOBELPEACE-25-EMM",
            "market_id": "805160dc-0eda-49c0-b390-c20592e3d57e", 
            "price": 1,
            "delta": -2000,
            "side": "no",
            "ts": "2025-08-14T17:49:01.501762229Z"
        }
        """
        # Determine outcome ID from side
        side = delta_data.get("side", "yes")
        outcome_id = "yes" if side == "yes" else "no"
        
        # Parse timestamp from Kalshi format to nanoseconds
        ts_str = delta_data.get("ts", "")
        ts_ns = recv_ts_ns  # Default to received time
        if ts_str:
            try:
                from datetime import datetime
                import dateutil.parser
                dt = dateutil.parser.isoparse(ts_str.replace('Z', '+00:00'))
                ts_ns = int(dt.timestamp() * 1_000_000_000)
            except:
                pass  # Use recv_ts_ns as fallback
        
        return {
            "market_id": delta_data.get("market_ticker", ""),
            "market_uuid": delta_data.get("market_id", ""),
            "outcome_id": outcome_id,
            "ts_ns": ts_ns,
            "price": delta_data.get("price"),
            "delta": delta_data.get("delta"),
            "side": side
        }
    
    def _normalize_ticker(self, ticker_data: Dict, recv_ts_ns: int) -> Dict:
        """Normalize ticker message"""
        return {
            "market_id": ticker_data.get("market_ticker", ""),
            "best_bid": ticker_data.get("bid"),
            "best_ask": ticker_data.get("ask"),
            "ts_ns": recv_ts_ns
        }
    
    def _extract_mapping_tags(self, kalshi_market: Dict) -> Dict:
        """Extract structured tags for market matching"""
        title = kalshi_market.get("title", "").lower()
        category = kalshi_market.get("category", "").lower()
        
        tags = {
            "category": category,
            "venue": "kalshi"
        }
        
        # Extract common patterns
        if "fed" in title or "federal reserve" in title:
            tags["entity"] = "federal_reserve"
            tags["subcategory"] = "monetary_policy"
        elif "cpi" in title or "inflation" in title:
            tags["entity"] = "bls" 
            tags["subcategory"] = "inflation"
        elif "election" in category or "politics" in category:
            tags["subcategory"] = "politics"
        elif "economics" in category:
            tags["subcategory"] = "macro"
        elif "climate" in category or "weather" in category:
            tags["subcategory"] = "weather"
        
        # Extract dates from title
        date_match = re.search(r'(\d{4})', title)
        if date_match:
            tags["year"] = date_match.group(1)
            
        return tags
    
    def _normalize_status(self, kalshi_status: str) -> str:
        """Normalize Kalshi market status to canonical format"""
        status_map = {
            "open": "active",
            "closed": "resolved", 
            "settled": "resolved",
            "unopened": "pending"
        }
        return status_map.get(kalshi_status.lower(), "active")