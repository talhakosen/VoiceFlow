#!/bin/bash
# VoiceFlow Backend Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PYTHON="$BACKEND_DIR/.venv/bin/python"
PID_FILE="$BACKEND_DIR/.voiceflow.pid"
PORT=8765
export HF_TOKEN="${HF_TOKEN:-}"

start() {
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo "Backend already running on port $PORT"
        return 0
    fi

    echo "Starting VoiceFlow backend..."
    cd "$BACKEND_DIR"
    $PYTHON -m voiceflow.main > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    if curl -s http://localhost:$PORT/api/status >/dev/null 2>&1; then
        echo "Backend started successfully on port $PORT"
    else
        echo "Failed to start backend"
        return 1
    fi
}

stop() {
    echo "Stopping VoiceFlow backend..."
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi
    # Also kill any process on the port
    lsof -ti :$PORT | xargs kill -9 2>/dev/null
    echo "Backend stopped"
}

status() {
    if curl -s http://localhost:$PORT/api/status >/dev/null 2>&1; then
        echo "Backend is running"
        curl -s http://localhost:$PORT/api/status | python3 -m json.tool
    else
        echo "Backend is not running"
    fi
}

restart() {
    stop
    sleep 1
    start
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
