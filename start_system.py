#!/usr/bin/env python3
"""
Start the complete Kalshi Terminal system
This script starts Redis, API server, and provides instructions for the UI
"""

import asyncio
import subprocess
import time
import os
import sys
import signal
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

async def check_redis():
    """Check if Redis is running"""
    try:
        proc = await asyncio.create_subprocess_exec(
            'redis-cli', 'ping',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().strip() == 'PONG'
    except:
        return False

async def start_redis():
    """Start Redis server if not running"""
    if await check_redis():
        print("✅ Redis is already running")
        return None
    
    print("🚀 Starting Redis server...")
    proc = await asyncio.create_subprocess_exec(
        'redis-server',
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    # Wait a moment for Redis to start
    await asyncio.sleep(2)
    
    if await check_redis():
        print("✅ Redis started successfully")
        return proc
    else:
        print("❌ Failed to start Redis")
        return None

async def start_api_server():
    """Start the API server"""
    print("🚀 Starting API server on port 8000...")
    
    env = os.environ.copy()
    env['KALSHI_API_KEY'] = '6d7e4138-afce-47a3-ace2-495d6d801410'
    env['KALSHI_PRIVATE_KEY_PATH'] = './kalshi-key.pem'
    env['KALSHI_ENVIRONMENT'] = 'prod'
    
    proc = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'uvicorn',
        'api.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload',
        env=env,
        cwd=Path(__file__).parent
    )
    
    # Wait for API to start
    await asyncio.sleep(3)
    print("✅ API server started on http://localhost:8000")
    return proc

async def test_api():
    """Test if API is responding"""
    try:
        proc = await asyncio.create_subprocess_exec(
            'curl', '-s', 'http://localhost:8000/healthz',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            print("✅ API server is responding")
            return True
    except:
        pass
    
    print("⚠️  API server might not be ready yet")
    return False

async def start_kalshi_adapter():
    """Start the Kalshi adapter"""
    print("🚀 Starting Kalshi adapter...")
    
    env = os.environ.copy()
    env['KALSHI_API_KEY'] = '6d7e4138-afce-47a3-ace2-495d6d801410'
    env['KALSHI_PRIVATE_KEY_PATH'] = './kalshi-key.pem'
    env['KALSHI_ENVIRONMENT'] = 'prod'
    
    proc = await asyncio.create_subprocess_exec(
        sys.executable, 'main.py',
        env=env,
        cwd=Path(__file__).parent
    )
    
    print("✅ Kalshi adapter started")
    return proc

def print_instructions():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 KALSHI TERMINAL SYSTEM STARTED")
    print("="*60)
    print()
    print("🌐 Services running:")
    print("   • Redis: localhost:6379") 
    print("   • API Server: http://localhost:8000")
    print("   • Kalshi Adapter: Connecting to markets...")
    print()
    print("🚀 To start the UI dashboard:")
    print(f"   cd {Path(__file__).parent}/ui")
    print("   npm run dev")
    print()
    print("📊 Then open http://localhost:3000 in your browser")
    print()
    print("🔧 API Endpoints available:")
    print("   • GET  /status        - System status")
    print("   • GET  /books         - Order book data") 
    print("   • GET  /markets       - Market information")
    print("   • WS   /ws            - Real-time WebSocket feed")
    print()
    print("💡 Tip: The terminal will auto-discover and subscribe to 50 active markets")
    print()
    print("⌨️  Press Ctrl+C to stop all services")
    print("="*60)

async def main():
    """Main function to start all services"""
    print("🏗️  Starting Kalshi Terminal System...")
    print()
    
    processes = []
    
    try:
        # Start Redis
        redis_proc = await start_redis()
        if redis_proc:
            processes.append(redis_proc)
        
        # Start API server
        api_proc = await start_api_server()
        processes.append(api_proc)
        
        # Test API
        await test_api()
        
        # Start Kalshi adapter
        kalshi_proc = await start_kalshi_adapter()
        processes.append(kalshi_proc)
        
        # Print instructions
        print_instructions()
        
        # Wait for processes or interruption
        while True:
            await asyncio.sleep(1)
            
            # Check if any process died
            for proc in processes[:]:
                if proc.returncode is not None:
                    print(f"⚠️  Process {proc.pid} exited with code {proc.returncode}")
                    processes.remove(proc)
            
            if not processes:
                print("❌ All processes stopped")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all services...")
        
        # Terminate all processes
        for proc in processes:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        
        print("✅ All services stopped")

if __name__ == "__main__":
    asyncio.run(main())