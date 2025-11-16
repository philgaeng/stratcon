#!/bin/bash
# Stop Stratcon servers

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PID_FILE="/tmp/stratcon_backend.pid"
FRONTEND_PID_FILE="/tmp/stratcon_frontend.pid"

backend_stopped=false
frontend_stopped=false

kill_if_running() {
    local pid="$1"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        return 0
    fi
    return 1
}

echo -e "${YELLOW}🛑 Stopping Stratcon servers...${NC}"
echo ""

# Stop backend
backend_pid=""
if [ -f "$BACKEND_PID_FILE" ]; then
    backend_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)
fi

if kill_if_running "$backend_pid"; then
    backend_stopped=true
elif pkill -f "uvicorn backend.api.api:app" 2>/dev/null; then
    backend_stopped=true
elif pkill -f "uvicorn api:app" 2>/dev/null; then
    backend_stopped=true
fi

if [ "$backend_stopped" = true ]; then
    echo -e "${GREEN}✅ Backend server stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Backend server not running${NC}"
fi

# Stop frontend
frontend_pid=""
if [ -f "$FRONTEND_PID_FILE" ]; then
    frontend_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || true)
fi

if kill_if_running "$frontend_pid"; then
    frontend_stopped=true
elif pkill -f "next dev" 2>/dev/null; then
    frontend_stopped=true
fi

if [ "$frontend_stopped" = true ]; then
    echo -e "${GREEN}✅ Frontend server stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend server not running${NC}"
fi

# Clean up PID files
rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"

echo ""
echo -e "${GREEN}✅ Done${NC}"
echo ""


