#!/bin/bash

# SurvivalStack | Aether Session Manager (Linux)
# Usage: ./session.sh [start|stop|status]

ACTION=${1:-start}
PORT=8000

get_aether_pid() {
    pgrep -f "python server.py" | head -n 1
}

case $ACTION in
    start)
        PID=$(get_aether_pid)
        if [ -n "$PID" ]; then
            echo "Aether is already running (PID: $PID)"
        else
            echo "Starting Aether Context Engine..."
            # Use local .venv python instead of 'uv run'
            nohup ./.venv/bin/python server.py > aether.log 2>&1 &
            sleep 2
            PID=$(get_aether_pid)
            if [ -n "$PID" ]; then
                echo "Aether is live at http://localhost:$PORT (PID: $PID)"
            else
                echo "Aether started but PID not found. Check aether.log"
            fi
        fi
        ;;
    stop)
        PID=$(get_aether_pid)
        if [ -n "$PID" ]; then
            echo "Stopping Aether process (PID: $PID)..."
            kill $PID
            echo "Aether session ended."
        else
            echo "Aether is not running."
        fi
        ;;
    status)
        PID=$(get_aether_pid)
        if [ -n "$PID" ]; then
            MEM=$(ps -o rss= -p $PID | awk '{print $1/1024}')
            echo "Aether Status: ACTIVE"
            echo "PID: $PID"
            echo "RAM: ${MEM} MB"
        else
            echo "Aether Status: INACTIVE"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
