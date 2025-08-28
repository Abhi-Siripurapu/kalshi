#!/bin/bash
# View Kalshi Terminal Logs

echo "📋 Kalshi Terminal Logs"
echo "======================="

if [[ ! -d "logs" ]]; then
    echo "❌ No logs directory found. Services may not have been started yet."
    exit 1
fi

# Function to show log file with header
show_log() {
    local file=$1
    local name=$2
    
    if [[ -f "$file" ]]; then
        echo ""
        echo "🔍 $name Logs (last 20 lines):"
        echo "----------------------------------------"
        tail -n 20 "$file"
    else
        echo "❌ $name log file not found: $file"
    fi
}

# Check command line argument
case "${1:-all}" in
    "api")
        show_log "logs/api.log" "API Server"
        ;;
    "bridge")
        show_log "logs/bridge.log" "WebSocket Bridge"
        ;;
    "ui")
        show_log "logs/ui.log" "UI Server"
        ;;
    "all")
        show_log "logs/api.log" "API Server"
        show_log "logs/bridge.log" "WebSocket Bridge"
        show_log "logs/ui.log" "UI Server"
        ;;
    "follow")
        echo "Following all logs (Ctrl+C to stop)..."
        tail -f logs/*.log 2>/dev/null
        ;;
    *)
        echo "Usage: $0 [api|bridge|ui|all|follow]"
        echo "  api    - Show API server logs only"
        echo "  bridge - Show WebSocket bridge logs only"
        echo "  ui     - Show UI server logs only"
        echo "  all    - Show all logs (default)"
        echo "  follow - Follow all logs in real-time"
        exit 1
        ;;
esac

echo ""
echo "💡 Use './logs.sh follow' to watch logs in real-time"