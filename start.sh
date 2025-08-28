#!/bin/bash
# Kalshi Terminal Startup Script
set -e  # Exit on any error

echo "🏛️ Starting Kalshi Terminal..."

# Check Python version
if ! python3 --version >/dev/null 2>&1; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check environment
if [[ ! -f ".env" ]]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with your KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PATH"
    echo "Example:"
    echo "  KALSHI_API_KEY=your_api_key_here"
    echo "  KALSHI_PRIVATE_KEY_PATH=./kalshi-key.pem"
    echo "  KALSHI_ENVIRONMENT=prod"
    exit 1
fi

if [[ ! -f "kalshi-key.pem" ]]; then
    echo "❌ Error: kalshi-key.pem not found"
    echo "Please place your Kalshi private key file in the project root"
    echo "Download it from https://kalshi.com/profile"
    exit 1
fi

# Check virtual environment
if [[ ! -d ".venv" ]]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate Python environment
echo "🐍 Activating Python environment..."
source .venv/bin/activate

# Create logs directory
mkdir -p logs

# Kill existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python.*simple_api.py" || true
pkill -f "python.*http.server" || true
pkill -f "python.*real_time_bridge.py" || true

# Wait for processes to stop
sleep 2

# Start backend API
echo "🚀 Starting API server..."
cd backend
python simple_api.py > ../logs/api.log 2>&1 &
API_PID=$!
cd ..

# Start real-time bridge (optional)
echo "🌉 Starting real-time bridge..."
cd backend
python real_time_bridge.py > ../logs/bridge.log 2>&1 &
BRIDGE_PID=$!
cd ..

# Start frontend
echo "🖥️  Starting UI server..."
cd frontend/ui
python -m http.server 3000 > ../../logs/ui.log 2>&1 &
UI_PID=$!
cd ../..

echo ""
echo "✅ Kalshi Terminal started successfully!"
echo ""
echo "📡 API Server: http://localhost:8000"
echo "🖥️  Terminal UI: http://localhost:3000/markets.html"
echo "🌉 WebSocket Bridge: http://localhost:8001"
echo ""
echo "💡 Open http://localhost:3000/markets.html in your browser to start trading!"
echo ""
echo "🔧 Commands:"
echo "  ./stop.sh    - Stop all services"
echo "  ./logs.sh    - View service logs"
echo "  ./status.sh  - Check service status"
echo ""
echo "📋 Logs are saved in the logs/ directory"

# Save PIDs for cleanup
echo "$API_PID $BRIDGE_PID $UI_PID" > .pids

# Wait a moment for services to start
echo "⏳ Waiting for services to start..."
sleep 3

# Test if services are running
echo "🧪 Testing services..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API Server is running"
else
    echo "⚠️  API Server may not be responding yet"
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ UI Server is running"
else
    echo "⚠️  UI Server may not be responding yet"
fi

echo ""
echo "🎉 Setup complete! Happy trading!"