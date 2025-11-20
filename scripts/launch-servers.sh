#!/bin/bash
# Launch both backend and frontend servers for Stratcon
#
# Usage:
#   ./scripts/launch-servers.sh                    # Development mode (npm run dev)
#   ./scripts/launch-servers.sh --production        # Production mode (npm run build && npm start)
#   ./scripts/launch-servers.sh --restart          # Auto-restart mode (kills existing servers, non-interactive)
#   ./scripts/launch-servers.sh --production --restart  # Production + auto-restart (non-interactive)
#   ./scripts/launch-servers.sh --yes              # Non-interactive mode (auto-answer all prompts)

# Don't exit on error - we want to handle errors gracefully
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
AUTO_RESTART=false
PRODUCTION_MODE=false
NON_INTERACTIVE=false

for arg in "$@"; do
    case "$arg" in
        --restart|-r)
            AUTO_RESTART=true
            NON_INTERACTIVE=true
            echo -e "${BLUE}   Auto-restart mode: will kill existing servers${NC}"
            ;;
        --production|-p)
            PRODUCTION_MODE=true
            echo -e "${BLUE}   Production mode: will build and start${NC}"
            ;;
        --yes|-y|--non-interactive)
            NON_INTERACTIVE=true
            echo -e "${BLUE}   Non-interactive mode: auto-answering prompts${NC}"
            ;;
    esac
done

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/website"
BACKEND_DIR="$PROJECT_ROOT/backend"

# AWS Server Configuration
AWS_SERVER_IP="${AWS_SERVER_IP:-52.221.59.184}"
AWS_DOMAIN="${AWS_DOMAIN:-stratcon.facets-ai.com}"
# Use domain with HTTPS if available, otherwise fall back to IP
if [ -n "$AWS_DOMAIN" ] && [ "$AWS_DOMAIN" != "none" ]; then
    API_URL="https://${AWS_DOMAIN}/api"
else
    API_URL="http://${AWS_SERVER_IP}:8000"
fi

echo -e "${BLUE}🚀 Stratcon Server Launcher${NC}"
echo "======================================"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "   Server IP: $AWS_SERVER_IP"
echo "   Domain: ${AWS_DOMAIN:-none}"
echo "   API URL: $API_URL"
echo "   Mode: $([ "$PRODUCTION_MODE" = true ] && echo "Production" || echo "Development")"
echo ""

# Step 1: Check and start backend
echo -e "${YELLOW}🔍 Step 1: Checking backend status...${NC}"
SKIP_BACKEND=false
USE_SYSTEMD=false

# Check if systemd service exists and systemctl is available
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "stratcon-api.service" 2>/dev/null; then
    USE_SYSTEMD=true
fi

# Check if backend is already running on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Backend is already running on port 8000${NC}"
        if [ "$AUTO_RESTART" = true ]; then
            echo "   Auto-restart mode: stopping existing backend..."
            if [ "$USE_SYSTEMD" = true ] && systemctl is-active --quiet stratcon-api 2>/dev/null; then
                sudo systemctl stop stratcon-api
            else
                pkill -f "uvicorn.*api:app" || pkill -f "uvicorn.*backend.api.api" || true
            fi
            sleep 2
        else
            SKIP_BACKEND=true
        fi
    else
        echo -e "${YELLOW}   ⚠️  Port 8000 in use but not responding${NC}"
        if [ "$AUTO_RESTART" = true ] || [ "$NON_INTERACTIVE" = true ]; then
            echo "   Killing unresponsive backend..."
            pkill -9 -f "uvicorn.*api:app" || pkill -9 -f "uvicorn.*backend.api.api" || true
            if [ "$USE_SYSTEMD" = true ] && systemctl is-active --quiet stratcon-api 2>/dev/null; then
                sudo systemctl stop stratcon-api
            fi
            sleep 2
        fi
    fi
fi

# Start backend if needed
if [ "$SKIP_BACKEND" != "true" ]; then
    if [ "$USE_SYSTEMD" = true ]; then
        # Use systemd service (AWS server)
        echo "   Using systemd service..."
        if systemctl is-active --quiet stratcon-api 2>/dev/null; then
            if [ "$AUTO_RESTART" = true ]; then
                echo "   Restarting backend service..."
                sudo systemctl restart stratcon-api
            fi
        else
            echo "   Starting backend service..."
            sudo systemctl start stratcon-api
        fi
        sleep 3
        if systemctl is-active --quiet stratcon-api 2>/dev/null; then
            echo -e "${GREEN}   ✓ Backend service started${NC}"
        else
            echo -e "${RED}   ❌ Failed to start backend service${NC}"
            echo "   Falling back to direct start..."
            USE_SYSTEMD=false
        fi
    fi
    
    if [ "$USE_SYSTEMD" != "true" ]; then
        # Start backend directly (local development)
        echo "   Starting backend directly (local mode)..."
        export AUTH_BYPASS_SCOPE=${AUTH_BYPASS_SCOPE:-1}
        (
            if command -v conda >/dev/null 2>&1; then
                source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
                conda activate datascience >/dev/null 2>&1 || true
            fi
            cd "$PROJECT_ROOT"
            PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
            uvicorn backend.api.api:app --host 0.0.0.0 --port 8000 --reload \
                > /tmp/stratcon_backend.log 2>&1 &
            echo $! > /tmp/stratcon_backend.pid
        )
        sleep 3
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo -e "${GREEN}   ✓ Backend started on http://localhost:8000${NC}"
            echo "   Logs: /tmp/stratcon_backend.log"
            echo "   PID: $(cat /tmp/stratcon_backend.pid)"
        else
            echo -e "${YELLOW}   ⚠️  Backend may still be starting...${NC}"
            echo "   Check logs: /tmp/stratcon_backend.log"
        fi
    fi
fi

echo ""

# Step 2: Check if frontend is already running
echo -e "${YELLOW}🔍 Step 2: Checking for existing frontend...${NC}"

SKIP_FRONTEND=false

# Check frontend (port 3000)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Frontend server already running on port 3000${NC}"
    # Test if it's actually responding
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Frontend is responding${NC}"
        if [ "$AUTO_RESTART" = true ] || [ "$NON_INTERACTIVE" = true ]; then
            echo "   Auto-restart mode: killing existing frontend..."
            REPLY="y"
        else
            read -p "   Kill existing frontend and restart? (y/N) " -n 1 -r
            echo
        fi
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Stopping existing frontend..."
            pkill -f "next" || true
            sleep 2
            # Verify it's actually stopped
            if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
                echo -e "${RED}   ⚠️  Port still in use, force killing...${NC}"
                pkill -9 -f "next" || true
                sleep 1
            fi
            echo -e "${GREEN}✅ Stopped existing frontend${NC}"
        else
            echo -e "${YELLOW}   Keeping existing frontend running${NC}"
            SKIP_FRONTEND=true
        fi
    else
        echo -e "${RED}   ⚠️  Frontend port in use but not responding (zombie process?)${NC}"
        if [ "$AUTO_RESTART" = true ] || [ "$NON_INTERACTIVE" = true ]; then
            echo "   Auto-restart mode: killing unresponsive frontend..."
            REPLY="y"
        else
            read -p "   Kill and restart? (Y/n) " -n 1 -r
            echo
        fi
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            pkill -f "next" || true
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

# Step 3: Setup frontend environment variables
echo -e "${YELLOW}📝 Step 3: Setting up frontend environment variables...${NC}"
cd "$FRONTEND_DIR"

# Create or update .env.local
ENV_FILE="$FRONTEND_DIR/.env.local"
if [ -f "$ENV_FILE" ]; then
    echo "   Found existing .env.local"
    # Check if API URL needs updating
    if grep -q "NEXT_PUBLIC_API_URL" "$ENV_FILE"; then
        echo "   Updating NEXT_PUBLIC_API_URL to $API_URL"
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=$API_URL|" "$ENV_FILE"
    else
        echo "   Adding NEXT_PUBLIC_API_URL=$API_URL"
        echo "NEXT_PUBLIC_API_URL=$API_URL" >> "$ENV_FILE"
    fi
else
    echo "   Creating .env.local with AWS configuration"
    cat > "$ENV_FILE" << EOF
# AWS Production Configuration
NEXT_PUBLIC_API_URL=$API_URL

# AWS Cognito Configuration (update with your values)
# NEXT_PUBLIC_COGNITO_USER_POOL_ID=ap-southeast-1_xxxxxxxxx
# NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
# NEXT_PUBLIC_COGNITO_REGION=ap-southeast-1
EOF
fi

echo -e "${GREEN}✅ Environment variables configured${NC}"
echo ""

# Step 4: Install frontend dependencies if needed
echo -e "${YELLOW}📦 Step 4: Checking frontend dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   Installing npm dependencies...${NC}"
    npm install
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}   ✓ Dependencies already installed${NC}"
fi

echo ""

# Step 5: Start frontend server
if [ "$SKIP_FRONTEND" != "true" ]; then
    echo -e "${YELLOW}🎨 Step 5: Starting frontend server...${NC}"
    
    if [ "$PRODUCTION_MODE" = true ]; then
        echo "   Building for production..."
        npm run build
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Build complete${NC}"
            echo "   Starting production server..."
            npm start > /tmp/stratcon_frontend.log 2>&1 &
            echo $! > /tmp/stratcon_frontend.pid
        else
            echo -e "${RED}❌ Build failed${NC}"
            echo "   Check the output above for errors"
            exit 1
        fi
    else
        echo "   Starting development server..."
        npm run dev > /tmp/stratcon_frontend.log 2>&1 &
        echo $! > /tmp/stratcon_frontend.pid
    fi
    
    # Wait a moment and check if frontend started
    sleep 5
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend server started on http://localhost:3000${NC}"
        echo "   Logs: /tmp/stratcon_frontend.log"
        echo "   PID: $(cat /tmp/stratcon_frontend.pid)"
    else
        echo -e "${YELLOW}⚠️  Frontend may still be starting...${NC}"
        echo "   Check logs: /tmp/stratcon_frontend.log"
        tail -20 /tmp/stratcon_frontend.log
    fi
else
    echo -e "${YELLOW}⏭️  Skipping frontend start (already running)${NC}"
fi

echo ""
echo -e "${GREEN}================================"
echo "✅ Launch complete!"
echo "================================"
echo ""
echo "Backend:  http://$AWS_SERVER_IP:8000 (systemd service)"
echo "Frontend: http://$AWS_SERVER_IP:3000"
echo ""
echo "To stop servers:"
echo "  ./scripts/stop-servers.sh"
echo ""
echo "To view logs:"
if [ "$USE_SYSTEMD" = true ]; then
    echo "  Backend:  sudo journalctl -u stratcon-api -f"
else
    echo "  Backend:  tail -f /tmp/stratcon_backend.log"
fi
echo "  Frontend: tail -f /tmp/stratcon_frontend.log"
echo ""

