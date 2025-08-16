#!/bin/bash
# Simple Kalshi Terminal Startup Script

echo "🏛️ Starting Kalshi Terminal..."

# Check environment
if [[ ! -f ".env" ]]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with your KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH"
    exit 1
fi

if [[ ! -f "kalshi-key.pem" ]]; then
    echo "❌ Error: kalshi-key.pem not found"
    echo "Please place your Kalshi private key file in the project root"
    exit 1
fi

# Activate Python environment
echo "🐍 Activating Python environment..."
source .venv/bin/activate

# Kill existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python.*simple_api.py" || true
pkill -f "python.*http.server" || true
pkill -f "python.*real_time_bridge.py" || true

# Start backend API
echo "🚀 Starting API server..."
cd backend
python simple_api.py &
API_PID=$!
cd ..

# Start real-time bridge (optional)
echo "🌉 Starting real-time bridge..."
cd backend
python real_time_bridge.py &
BRIDGE_PID=$!
cd ..

# Start frontend
echo "🖥️  Starting UI server..."
cd frontend/ui
python -m http.server 3000 &
UI_PID=$!
cd ../..

echo ""
echo "✅ Kalshi Terminal started successfully!"
echo ""
echo "📡 API Server: http://localhost:8000"
echo "🖥️  Terminal UI: http://localhost:3000"
echo "🌉 WebSocket Bridge: http://localhost:8001"
echo ""
echo "💡 Open http://localhost:3000 in your browser"
echo ""
echo "To stop all services, run: ./stop.sh"
echo "To view logs, run: ./logs.sh"

# Save PIDs for cleanup
echo "$API_PID $BRIDGE_PID $UI_PID" > .pids