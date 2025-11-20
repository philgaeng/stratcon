#!/bin/bash
# Stop both backend and frontend servers for Stratcon
#
# Usage:
#   ./scripts/stop-servers.sh              # Stop both servers
#   ./scripts/stop-servers.sh --frontend    # Stop only frontend
#   ./scripts/stop-servers.sh --backend     # Stop only backend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
STOP_BACKEND=true
STOP_FRONTEND=true

for arg in "$@"; do
    case "$arg" in
        --frontend|-f)
            STOP_BACKEND=false
            ;;
        --backend|-b)
            STOP_FRONTEND=false
            ;;
    esac
done

echo -e "${BLUE}🛑 Stopping Stratcon Servers${NC}"
echo "======================================"
echo ""

# Stop backend
if [ "$STOP_BACKEND" = true ]; then
    echo -e "${YELLOW}🔧 Stopping backend...${NC}"
    
    # Try systemd first
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "stratcon-api.service" 2>/dev/null; then
        if systemctl is-active --quiet stratcon-api 2>/dev/null; then
            sudo systemctl stop stratcon-api
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Backend service stopped${NC}"
            else
                echo -e "${RED}❌ Failed to stop backend service${NC}"
            fi
        else
            echo -e "${YELLOW}   Backend service is not running${NC}"
        fi
    fi
    
    # Also check for direct processes (local development)
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   Killing backend process on port 8000..."
        if [ -f /tmp/stratcon_backend.pid ]; then
            PID=$(cat /tmp/stratcon_backend.pid)
            if ps -p "$PID" > /dev/null 2>&1; then
                kill "$PID" 2>/dev/null
                sleep 2
                if ps -p "$PID" > /dev/null 2>&1; then
                    kill -9 "$PID" 2>/dev/null
                fi
            fi
            rm -f /tmp/stratcon_backend.pid
        fi
        pkill -f "uvicorn.*api:app" || pkill -f "uvicorn.*backend.api.api" || true
        sleep 2
        if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            pkill -9 -f "uvicorn.*api:app" || pkill -9 -f "uvicorn.*backend.api.api" || true
        fi
        echo -e "${GREEN}✅ Backend stopped${NC}"
    fi
    echo ""
fi

# Stop frontend
if [ "$STOP_FRONTEND" = true ]; then
    echo -e "${YELLOW}🎨 Stopping frontend server...${NC}"
    
    # Check if frontend is running via PID file
    if [ -f /tmp/stratcon_frontend.pid ]; then
        PID=$(cat /tmp/stratcon_frontend.pid)
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "   Killing frontend process (PID: $PID)..."
            kill "$PID" 2>/dev/null
            sleep 2
            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "   Force killing frontend process..."
                kill -9 "$PID" 2>/dev/null
            fi
            rm -f /tmp/stratcon_frontend.pid
            echo -e "${GREEN}✅ Frontend process stopped${NC}"
        else
            echo -e "${YELLOW}   PID file exists but process not running${NC}"
            rm -f /tmp/stratcon_frontend.pid
        fi
    fi
    
    # Also check for any Next.js processes on port 3000
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   Killing processes on port 3000..."
        pkill -f "next" || true
        sleep 2
        # Force kill if still running
        if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo "   Force killing processes on port 3000..."
            pkill -9 -f "next" || true
        fi
        echo -e "${GREEN}✅ Frontend stopped${NC}"
    else
        echo -e "${YELLOW}   Frontend is not running${NC}"
    fi
    echo ""
fi

echo -e "${GREEN}================================"
echo "✅ Stop complete!"
echo "================================"
echo ""
echo "To start servers again:"
echo "  ./scripts/launch-servers.sh"
echo ""

