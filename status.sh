#!/bin/bash
# Check Kalshi Terminal Service Status

echo "🔍 Kalshi Terminal Service Status"
echo "================================="

# Check if services are running
check_service() {
    local name=$1
    local port=$2
    local process=$3
    
    # Check if process is running
    if pgrep -f "$process" > /dev/null; then
        # Check if port is accessible
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            echo "✅ $name (Port $port) - Running and accessible"
        else
            echo "⚠️  $name (Port $port) - Process running but not accessible"
        fi
    else
        echo "❌ $name (Port $port) - Not running"
    fi
}

# Check each service
check_service "API Server" "8000" "simple_api.py"
check_service "WebSocket Bridge" "8001" "real_time_bridge.py"
check_service "UI Server" "3000" "http.server"

echo ""
echo "🌐 Network Status:"
echo "------------------"

# Check port usage
echo "Port usage:"
ss -tulpn | grep -E ":(3000|8000|8001)" | while read line; do
    echo "  $line"
done

echo ""
echo "🐍 Python Processes:"
echo "-------------------"
ps aux | grep python | grep -E "(simple_api|real_time_bridge|http.server)" | grep -v grep

echo ""
echo "📊 Resource Usage:"
echo "-----------------"
if command -v top > /dev/null; then
    echo "Memory and CPU usage for Kalshi services:"
    ps aux | grep python | grep -E "(simple_api|real_time_bridge|http.server)" | grep -v grep | awk '{print "  " $11 " - CPU: " $3 "%, Memory: " $4 "%"}'
fi

echo ""
if [[ -f ".pids" ]]; then
    echo "📝 Stored PIDs: $(cat .pids)"
else
    echo "📝 No PID file found"
fi

echo ""
echo "💡 Commands:"
echo "  ./start.sh  - Start all services"
echo "  ./stop.sh   - Stop all services"  
echo "  ./logs.sh   - View service logs"