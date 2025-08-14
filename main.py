#!/usr/bin/env python3
"""
Kalshi Terminal - Main Service Orchestrator
Coordinates all adapters, API, and supporting services
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adapters.kalshi import KalshiAdapter
from core.state.redis_store import create_publisher
from core.recorder.parquet_recorder import create_recorder
from api.main import publish_to_api

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TerminalOrchestrator:
    """Main orchestrator for the Kalshi Terminal"""
    
    def __init__(self):
        self.running = False
        self.adapters = {}
        self.publisher = None
        self.recorder = None
        self.tasks = []
        
        # Configuration from environment
        self.config = {
            "kalshi_api_key": os.getenv("KALSHI_API_KEY"),
            "kalshi_private_key_path": os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem"),
            "kalshi_environment": os.getenv("KALSHI_ENVIRONMENT", "demo"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "data_dir": os.getenv("DATA_DIR", "./data"),
            "log_level": os.getenv("LOG_LEVEL", "INFO")
        }
        
        # Target markets from config or use defaults
        self.target_markets = self._load_target_markets()
        
    def _load_target_markets(self) -> List[str]:
        """Load target markets from environment or use defaults"""
        markets_env = os.getenv("TARGET_MARKETS", "")
        if markets_env:
            return [m.strip() for m in markets_env.split(",")]
        
        # Return empty list to trigger auto-discovery of first 10 active markets
        return []
    
    async def start(self):
        """Start all services"""
        logger.info("Starting Kalshi Terminal Orchestrator")
        self.running = True
        
        try:
            # Initialize publisher and recorder
            await self._initialize_infrastructure()
            
            # Start adapters
            await self._start_adapters()
            
            # Wait for shutdown signal
            await self._wait_for_shutdown()
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _initialize_infrastructure(self):
        """Initialize Redis publisher and Parquet recorder"""
        logger.info("Initializing infrastructure")
        
        # Create publisher
        self.publisher = await create_publisher(self.config["redis_url"])
        
        # Create recorder
        self.recorder = await create_recorder(self.config["data_dir"])
        
        logger.info("Infrastructure initialized")
    
    async def _start_adapters(self):
        """Start all venue adapters"""
        logger.info("Starting venue adapters")
        
        # Start Kalshi adapter if configured
        if self.config["kalshi_api_key"]:
            await self._start_kalshi_adapter()
        else:
            logger.warning("KALSHI_API_KEY not found, Kalshi adapter disabled")
        
        # Polymarket adapter would be started here when ready
        # if self.config["polymarket_api_key"]:
        #     await self._start_polymarket_adapter()
        
        logger.info(f"Started {len(self.adapters)} adapters")
    
    async def _start_kalshi_adapter(self):
        """Start Kalshi adapter"""
        logger.info("Starting Kalshi adapter")
        
        try:
            # Create combined publisher that sends to both Redis and API
            async def combined_publisher(event: Dict):
                # Publish to Redis/state store
                await self.publisher.publish_event(event)
                
                # Record to Parquet
                await self.recorder.record_event(event)
                
                # Publish to API for WebSocket clients
                await publish_to_api(event)
            
            adapter = KalshiAdapter(
                api_key_id=self.config["kalshi_api_key"],
                private_key_path=self.config["kalshi_private_key_path"],
                target_markets=self.target_markets,
                publisher=combined_publisher,
                environment=self.config["kalshi_environment"]
            )
            
            self.adapters["kalshi"] = adapter
            
            # Start adapter in background task
            task = asyncio.create_task(adapter.start())
            self.tasks.append(task)
            
            logger.info("Kalshi adapter started")
            
        except Exception as e:
            logger.error(f"Failed to start Kalshi adapter: {e}")
            raise
    
    async def _wait_for_shutdown(self):
        """Wait for shutdown signal"""
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        
        def signal_handler():
            logger.info("Received shutdown signal")
            self.running = False
        
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, signal_handler)
        
        # Wait for tasks to complete or shutdown signal
        try:
            while self.running and self.tasks:
                # Check if any tasks completed
                done, pending = await asyncio.wait(
                    self.tasks, 
                    timeout=1.0, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Remove completed tasks
                for task in done:
                    self.tasks.remove(task)
                    if task.exception():
                        logger.error(f"Task failed: {task.exception()}")
                
                # If no tasks left, we're done
                if not self.tasks:
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.running = False
    
    async def shutdown(self):
        """Shutdown all services gracefully"""
        logger.info("Shutting down Kalshi Terminal")
        self.running = False
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Stop adapters
        for name, adapter in self.adapters.items():
            try:
                logger.info(f"Stopping {name} adapter")
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping {name} adapter: {e}")
        
        # Close infrastructure
        if self.recorder:
            try:
                await self.recorder.close()
            except Exception as e:
                logger.error(f"Error closing recorder: {e}")
        
        if self.publisher and hasattr(self.publisher, 'redis_store'):
            try:
                await self.publisher.redis_store.disconnect()
            except Exception as e:
                logger.error(f"Error closing publisher: {e}")
        
        logger.info("Shutdown complete")


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"./logs/terminal_{int(asyncio.get_event_loop().time())}.log")
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def main():
    """Main entry point"""
    # Ensure logs directory exists
    os.makedirs("./logs", exist_ok=True)
    
    # Setup logging
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))
    
    logger.info("=" * 50)
    logger.info("Kalshi Terminal Starting")
    logger.info("=" * 50)
    
    # Validate required configuration
    if not os.getenv("KALSHI_API_KEY"):
        logger.error("KALSHI_API_KEY environment variable is required")
        sys.exit(1)
    
    # Create and run orchestrator
    orchestrator = TerminalOrchestrator()
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())