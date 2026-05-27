#!/bin/bash

# SurvivalStack | Aether Session Manager (Linux)
# Usage: ./session.sh [start|stop|status]

ACTION=${1:-start}
PORT=8000

get_aether_pid() {
    ps -eo pid,state,command | grep "python server.py" | grep -v "defunct" | grep -v "grep" | awk '{print $1}' | head -n 1
}

get_any_aether_pid() {
    ps -eo pid,command | grep "python server.py" | grep -v "grep" | awk '{print $1}' | head -n 1
}

case $ACTION in
    start)
        PID=$(get_aether_pid)
        if [ -n "$PID" ]; then
            echo "Aether is already running (PID: $PID)"
        else
            echo "Starting Aether Context Engine..."
            # Use local .venv python instead of 'uv run'
            nohup ./.venv/bin/python server.py > logs/startup.log 2>&1 &
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
        PID=$(get_any_aether_pid)
        if [ -n "$PID" ]; then
            # Find all child processes (multiprocessing workers) of the parent PID
            CHILDREN=$(pgrep -P $PID)
            ALL_PIDS="$PID $CHILDREN"
            echo "Stopping Aether process tree (PIDs: $ALL_PIDS)..."
            kill $ALL_PIDS 2>/dev/null
            
            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
                STILL_ALIVE=""
                for P in $ALL_PIDS; do
                    if kill -0 $P 2>/dev/null; then
                        STILL_ALIVE="$STILL_ALIVE $P"
                    fi
                done
                if [ -z "$STILL_ALIVE" ]; then
                    break
                fi
                sleep 1
            done

            # Force kill any processes still running
            STILL_ALIVE=""
            for P in $ALL_PIDS; do
                if kill -0 $P 2>/dev/null; then
                    STILL_ALIVE="$STILL_ALIVE $P"
                fi
            done
            if [ -n "$STILL_ALIVE" ]; then
                echo "Processes ($STILL_ALIVE) did not exit. Force killing..."
                kill -9 $STILL_ALIVE 2>/dev/null
            fi
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
