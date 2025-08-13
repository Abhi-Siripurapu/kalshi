import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import pandas as pd
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class ParquetRecorder:
    """Records normalized events to hourly Parquet files for replay and audit"""
    
    def __init__(self, data_dir: str = "./data/records"):
        self.data_dir = Path(data_dir)
        self.current_files = {}  # venue -> current file handle
        self.buffer = {}  # venue -> list of events
        self.buffer_size = 100  # Flush buffer every N events
        self.last_flush = {}  # venue -> timestamp
        self.flush_interval = 60  # Flush every 60 seconds minimum
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, venue_id: str, timestamp: datetime) -> Path:
        """Get file path for given venue and timestamp"""
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m") 
        day = timestamp.strftime("%d")
        hour = timestamp.strftime("%H")
        
        file_dir = self.data_dir / venue_id / year / month / day / hour
        file_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"events_{hour}.parquet"
        return file_dir / filename
    
    async def record_event(self, event: Dict):
        """Record a normalized event"""
        venue_id = event.get("venue_id", "unknown")
        timestamp = datetime.fromtimestamp(
            event.get("ts_received_ns", time.time_ns()) / 1_000_000_000,
            tz=timezone.utc
        )
        
        # Add to buffer
        if venue_id not in self.buffer:
            self.buffer[venue_id] = []
        
        # Create record
        record = {
            "type": event.get("type", ""),
            "market_id": self._extract_market_id(event),
            "outcome_id": self._extract_outcome_id(event),
            "ts_ns": event.get("ts_received_ns", time.time_ns()),
            "recv_ts_ns": event.get("ts_received_ns", time.time_ns()),
            "payload_json": json.dumps(event),
            "hour": timestamp.strftime("%Y-%m-%d %H:00:00")
        }
        
        self.buffer[venue_id].append(record)
        
        # Check if we should flush
        should_flush = (
            len(self.buffer[venue_id]) >= self.buffer_size or
            time.time() - self.last_flush.get(venue_id, 0) >= self.flush_interval
        )
        
        if should_flush:
            await self._flush_buffer(venue_id, timestamp)
    
    def _extract_market_id(self, event: Dict) -> str:
        """Extract market ID from event data"""
        event_type = event.get("type", "")
        data = event.get("data", {})
        
        if event_type == "book_snapshot" and isinstance(data, list):
            return data[0].market_id if data else ""
        elif event_type == "book_delta":
            return data.get("market_id", "")
        elif event_type == "market_info":
            return data.market_id if hasattr(data, 'market_id') else ""
        elif event_type == "trade":
            return data.market_id if hasattr(data, 'market_id') else ""
        
        return ""
    
    def _extract_outcome_id(self, event: Dict) -> str:
        """Extract outcome ID from event data"""
        event_type = event.get("type", "")
        data = event.get("data", {})
        
        if event_type == "book_snapshot" and isinstance(data, list):
            return data[0].outcome_id if data else ""
        elif event_type == "book_delta":
            return data.get("outcome_id", "")
        elif event_type == "trade":
            return data.outcome_id if hasattr(data, 'outcome_id') else ""
        
        return ""
    
    async def _flush_buffer(self, venue_id: str, timestamp: datetime):
        """Flush buffer to Parquet file"""
        if venue_id not in self.buffer or not self.buffer[venue_id]:
            return
        
        try:
            records = self.buffer[venue_id]
            self.buffer[venue_id] = []
            self.last_flush[venue_id] = time.time()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Get file path
            file_path = self._get_file_path(venue_id, timestamp)
            
            # Append to existing file or create new one
            if file_path.exists():
                # Read existing file and append
                existing_df = pd.read_parquet(file_path)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            # Write with compression
            df.to_parquet(
                file_path,
                compression="snappy",
                index=False
            )
            
            # Create/update index file
            await self._update_index_file(venue_id, timestamp, len(records))
            
            logger.debug(f"Flushed {len(records)} events to {file_path}")
            
        except Exception as e:
            logger.error(f"Error flushing buffer for {venue_id}: {e}")
            # Put records back in buffer on error
            if venue_id not in self.buffer:
                self.buffer[venue_id] = []
            self.buffer[venue_id] = records + self.buffer[venue_id]
    
    async def _update_index_file(self, venue_id: str, timestamp: datetime, record_count: int):
        """Update hourly index file with row counts"""
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        hour = timestamp.strftime("%H")
        
        index_dir = self.data_dir / venue_id / year / month / day
        index_file = index_dir / "index.json"
        
        # Load existing index
        index_data = {}
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading index file: {e}")
        
        # Update with new record count
        hour_key = f"events_{hour}.parquet"
        index_data[hour_key] = index_data.get(hour_key, 0) + record_count
        
        # Write back
        try:
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing index file: {e}")
    
    async def flush_all(self):
        """Flush all venue buffers"""
        timestamp = datetime.now(timezone.utc)
        
        for venue_id in list(self.buffer.keys()):
            if self.buffer[venue_id]:
                await self._flush_buffer(venue_id, timestamp)
    
    async def close(self):
        """Close recorder and flush remaining buffers"""
        await self.flush_all()
        logger.info("Parquet recorder closed")


class ReplayEngine:
    """Engine for replaying recorded events"""
    
    def __init__(self, data_dir: str = "./data/records"):
        self.data_dir = Path(data_dir)
    
    async def load_events(
        self, 
        venue_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> list[Dict]:
        """Load events from Parquet files in time range"""
        events = []
        
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current_time <= end_time:
            file_path = self._get_file_path(venue_id, current_time)
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    
                    # Filter by time range
                    start_ns = int(start_time.timestamp() * 1_000_000_000)
                    end_ns = int(end_time.timestamp() * 1_000_000_000)
                    
                    filtered_df = df[
                        (df['ts_ns'] >= start_ns) & 
                        (df['ts_ns'] <= end_ns)
                    ].sort_values('ts_ns')
                    
                    # Convert back to events
                    for _, row in filtered_df.iterrows():
                        try:
                            event = json.loads(row['payload_json'])
                            events.append(event)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in replay: {e}")
                
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
            
            # Move to next hour
            current_time = current_time.replace(hour=current_time.hour + 1)
            if current_time.hour == 0:
                current_time = current_time.replace(day=current_time.day + 1)
        
        logger.info(f"Loaded {len(events)} events for replay")
        return events
    
    def _get_file_path(self, venue_id: str, timestamp: datetime) -> Path:
        """Get file path for given venue and timestamp"""
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d") 
        hour = timestamp.strftime("%H")
        
        file_dir = self.data_dir / venue_id / year / month / day / hour
        filename = f"events_{hour}.parquet"
        return file_dir / filename
    
    async def replay_events(
        self,
        events: list[Dict],
        publisher_func,
        speed_multiplier: float = 1.0
    ):
        """Replay events at original timing or faster"""
        if not events:
            return
        
        logger.info(f"Starting replay of {len(events)} events at {speed_multiplier}x speed")
        
        start_ts = events[0].get("ts_received_ns")
        replay_start = time.time_ns()
        
        for event in events:
            # Calculate when this event should be sent
            event_ts = event.get("ts_received_ns", start_ts)
            original_delay_ns = event_ts - start_ts
            scaled_delay_ns = original_delay_ns / speed_multiplier
            target_time_ns = replay_start + scaled_delay_ns
            
            # Wait until target time
            current_time_ns = time.time_ns()
            if target_time_ns > current_time_ns:
                sleep_time = (target_time_ns - current_time_ns) / 1_000_000_000
                await asyncio.sleep(sleep_time)
            
            # Send event
            try:
                await publisher_func(event)
            except Exception as e:
                logger.error(f"Error replaying event: {e}")
        
        logger.info("Replay completed")


async def create_recorder(data_dir: str = "./data/records") -> ParquetRecorder:
    """Create and initialize a Parquet recorder"""
    return ParquetRecorder(data_dir)