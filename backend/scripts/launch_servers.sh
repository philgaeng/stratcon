#!/bin/bash
# Launch script for Stratcon servers
# Compiles floor data, then starts backend and frontend servers
#
# Usage:
#   ./launch_servers.sh                    # Interactive mode (prompts for existing servers)
#   ./launch_servers.sh --restart          # Auto-restart mode (kills existing servers)
#   ./launch_servers.sh --skip-compile     # Skip data compilation step
#   ./launch_servers.sh --restart --skip-compile  # Combine flags

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
AUTO_RESTART=false
SKIP_COMPILE=false

for arg in "$@"; do
    case "$arg" in
        --restart|-r)
            AUTO_RESTART=true
            echo -e "${BLUE}   Auto-restart mode: will kill existing servers${NC}"
            ;;
        --skip-compile|--no-compile|-n)
            SKIP_COMPILE=true
            echo -e "${BLUE}   Skip compilation: will not compile floor data${NC}"
            ;;
    esac
done

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Configuration
CLIENT_TOKEN="${CLIENT_TOKEN:-NEO}"  # Default to NEO, can be overridden
COMPILE_SCRIPT="$BACKEND_DIR/services/data_extract_and_compile_to_db.py"
BACKEND_DIR_PATH="$BACKEND_DIR"
FRONTEND_DIR="$PROJECT_ROOT/website"

echo -e "${BLUE}🚀 Stratcon Server Launcher${NC}"
echo "================================"
echo ""

# Step 1: Compile floor data (unless skipped)
if [ "$SKIP_COMPILE" != "true" ]; then
    echo -e "${YELLOW}📦 Step 1: Compiling floor data...${NC}"
    cd "$PROJECT_ROOT"

    if [ ! -f "$COMPILE_SCRIPT" ]; then
        echo -e "${RED}❌ Compile script not found: $COMPILE_SCRIPT${NC}"
        exit 1
    fi

    if command -v conda &> /dev/null; then
        echo "   Compiling data for client: $CLIENT_TOKEN"
        if conda run -n datascience python3 "$COMPILE_SCRIPT" --client "$CLIENT_TOKEN"; then
            echo -e "${GREEN}✅ Floor data compiled successfully${NC}"
        else
            echo -e "${RED}❌ Failed to compile floor data${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  Conda not found, skipping data compilation${NC}"
        echo "   Make sure data is already compiled or run manually:"
        echo "   conda run -n datascience python3 $COMPILE_SCRIPT --client $CLIENT_TOKEN"
    fi

    echo ""
else
    echo -e "${YELLOW}⏭️  Skipping data compilation (--skip-compile flag)${NC}"
    echo ""
fi

# Step 2: Check if servers are already running
echo -e "${YELLOW}🔍 Step 2: Checking for existing servers...${NC}"

SKIP_BACKEND=false
SKIP_FRONTEND=false

# Check backend (port 8000)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Backend server already running on port 8000${NC}"
    # Test if it's actually responding
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Backend is responding${NC}"
        if [ "$AUTO_RESTART" = true ]; then
            echo "   Auto-restart mode: killing existing backend..."
            REPLY="y"
        else
            read -p "   Kill existing backend and restart? (y/N) " -n 1 -r
            echo
        fi
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Stopping existing backend..."
            pkill -f "uvicorn api:app" || true
            sleep 2
            # Verify it's actually stopped
            if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
                echo -e "${RED}   ⚠️  Port still in use, force killing...${NC}"
                pkill -9 -f "uvicorn api:app" || true
                sleep 1
            fi
            echo -e "${GREEN}✅ Stopped existing backend${NC}"
        else
            echo -e "${YELLOW}   Keeping existing backend running${NC}"
            SKIP_BACKEND=true
        fi
    else
        echo -e "${RED}   ⚠️  Backend port in use but not responding (zombie process?)${NC}"
        if [ "$AUTO_RESTART" = true ]; then
            echo "   Auto-restart mode: killing unresponsive backend..."
            REPLY="y"
        else
            read -p "   Kill and restart? (Y/n) " -n 1 -r
            echo
        fi
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            pkill -f "uvicorn api:app" || true
            sleep 2
            echo -e "${GREEN}✅ Killed unresponsive backend${NC}"
        else
            SKIP_BACKEND=true
        fi
    fi
else
    echo -e "${GREEN}   ✓ Backend port 8000 is free${NC}"
fi

# Check frontend (port 3000)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Frontend server already running on port 3000${NC}"
    # Test if it's actually responding
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Frontend is responding${NC}"
        if [ "$AUTO_RESTART" = true ]; then
            echo "   Auto-restart mode: killing existing frontend..."
            REPLY="y"
        else
            read -p "   Kill existing frontend and restart? (y/N) " -n 1 -r
            echo
        fi
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Stopping existing frontend..."
            pkill -f "next dev" || true
            sleep 2
            # Verify it's actually stopped
            if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
                echo -e "${RED}   ⚠️  Port still in use, force killing...${NC}"
                pkill -9 -f "next dev" || true
                sleep 1
            fi
            echo -e "${GREEN}✅ Stopped existing frontend${NC}"
        else
            echo -e "${YELLOW}   Keeping existing frontend running${NC}"
            SKIP_FRONTEND=true
        fi
    else
        echo -e "${RED}   ⚠️  Frontend port in use but not responding (zombie process?)${NC}"
        if [ "$AUTO_RESTART" = true ]; then
            echo "   Auto-restart mode: killing unresponsive frontend..."
            REPLY="y"
        else
            read -p "   Kill and restart? (Y/n) " -n 1 -r
            echo
        fi
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            pkill -f "next dev" || true
            sleep 2
            echo -e "${GREEN}✅ Killed unresponsive frontend${NC}"
        else
            SKIP_FRONTEND=true
        fi
    fi
else
    echo -e "${GREEN}   ✓ Frontend port 3000 is free${NC}"
fi

echo ""

# Step 3: Start backend server
if [ "$SKIP_BACKEND" != "true" ]; then
    echo -e "${YELLOW}🔧 Step 3: Starting backend server...${NC}"
    (
        if command -v conda >/dev/null 2>&1; then
            source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
            conda activate datascience >/dev/null 2>&1 || true
        fi
        cd "$PROJECT_ROOT"
        PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
        uvicorn backend.api.api:app --host 0.0.0.0 --port 8000 --reload --log-level debug \
            > /tmp/stratcon_backend.log 2>&1 &
        echo $! > /tmp/stratcon_backend.pid
    ) &
    
    # Wait a moment and check if backend started
    sleep 3
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend server started on http://localhost:8000${NC}"
        echo "   Logs: /tmp/stratcon_backend.log"
    else
        echo -e "${RED}❌ Backend server failed to start${NC}"
        echo "   Check logs: /tmp/stratcon_backend.log"
        tail -20 /tmp/stratcon_backend.log
    fi
else
    echo -e "${YELLOW}⏭️  Skipping backend start (already running)${NC}"
fi

echo ""

# Step 4: Start frontend server
if [ "$SKIP_FRONTEND" != "true" ]; then
    echo -e "${YELLOW}🎨 Step 4: Starting frontend server...${NC}"
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}   Installing npm dependencies...${NC}"
        npm install
    fi
    
    # Start frontend in background
    npm run dev > /tmp/stratcon_frontend.log 2>&1 &
    echo $! > /tmp/stratcon_frontend.pid
    
    # Wait a moment and check if frontend started
    sleep 5
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend server started on http://localhost:3000${NC}"
        echo "   Logs: /tmp/stratcon_frontend.log"
    else
        echo -e "${YELLOW}⚠️  Frontend may still be starting...${NC}"
        echo "   Check logs: /tmp/stratcon_frontend.log"
    fi
else
    echo -e "${YELLOW}⏭️  Skipping frontend start (already running)${NC}"
fi

echo ""
echo -e "${GREEN}================================"
echo "✅ Launch complete!"
echo "================================"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "To stop servers:"
echo "  pkill -f 'uvicorn api:app'  # Backend"
echo "  pkill -f 'next dev'          # Frontend"
echo ""
echo "Or use: ./backend/scripts/stop_servers.sh"
echo ""

