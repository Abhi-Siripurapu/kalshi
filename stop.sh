#!/bin/bash
# Stop Kalshi Terminal Services

echo "🛑 Stopping Kalshi Terminal..."

# Kill by process names
pkill -f "python.*simple_api.py" || true
pkill -f "python.*real_time_bridge.py" || true  
pkill -f "python.*http.server" || true

# Clean up PID file
rm -f .pids

echo "✅ All services stopped"