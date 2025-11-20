#!/bin/bash
# AWS-specific launch script for Stratcon frontend
# Launches only the frontend server (backend is managed by systemd)
#
# Usage:
#   ./scripts/launch-aws-frontend.sh                    # Development mode (npm run dev)
#   ./scripts/launch-aws-frontend.sh --production        # Production mode (npm run build && npm start)
#   ./scripts/launch-aws-frontend.sh --restart          # Auto-restart mode (kills existing frontend, non-interactive)
#   ./scripts/launch-aws-frontend.sh --production --restart  # Production + auto-restart (non-interactive)
#   ./scripts/launch-aws-frontend.sh --systemd          # Create systemd service instead of running directly
#   ./scripts/launch-aws-frontend.sh --yes              # Non-interactive mode (auto-answer all prompts)

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
CREATE_SYSTEMD=false
NON_INTERACTIVE=false

for arg in "$@"; do
    case "$arg" in
        --restart|-r)
            AUTO_RESTART=true
            NON_INTERACTIVE=true
            echo -e "${BLUE}   Auto-restart mode: will kill existing frontend${NC}"
            ;;
        --production|-p)
            PRODUCTION_MODE=true
            echo -e "${BLUE}   Production mode: will build and start${NC}"
            ;;
        --systemd|-s)
            CREATE_SYSTEMD=true
            echo -e "${BLUE}   Systemd mode: will create systemd service${NC}"
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

# AWS Server Configuration
AWS_SERVER_IP="${AWS_SERVER_IP:-52.221.59.184}"
AWS_DOMAIN="${AWS_DOMAIN:-stratcon.facets-ai.com}"
# Use domain with HTTPS if available, otherwise fall back to IP
if [ -n "$AWS_DOMAIN" ] && [ "$AWS_DOMAIN" != "none" ]; then
    API_URL="https://${AWS_DOMAIN}/api"
else
    API_URL="http://${AWS_SERVER_IP}:8000"
fi

echo -e "${BLUE}🚀 Stratcon AWS Frontend Launcher${NC}"
echo "======================================"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "   Server IP: $AWS_SERVER_IP"
echo "   Domain: ${AWS_DOMAIN:-none}"
echo "   API URL: $API_URL"
echo "   Mode: $([ "$PRODUCTION_MODE" = true ] && echo "Production" || echo "Development")"
echo ""

# Step 1: Check backend status (should be running via systemd)
echo -e "${YELLOW}🔍 Step 1: Checking backend status...${NC}"
if systemctl is-active --quiet stratcon-api; then
    echo -e "${GREEN}   ✓ Backend service is running (systemd)${NC}"
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ Backend API is responding${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Backend service running but not responding yet${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️  Backend service is not running${NC}"
    if [ "$NON_INTERACTIVE" = true ]; then
        echo "   Non-interactive mode: continuing anyway (frontend can start independently)"
    else
        echo "   Start it with: sudo systemctl start stratcon-api"
        read -p "   Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
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

# Step 3: Setup environment variables
echo -e "${YELLOW}📝 Step 3: Setting up environment variables...${NC}"
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

# Step 4: Install dependencies if needed
echo -e "${YELLOW}📦 Step 4: Checking dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   Installing npm dependencies...${NC}"
    npm install
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}   ✓ Dependencies already installed${NC}"
fi

echo ""

# Step 5: Create systemd service or start directly
if [ "$CREATE_SYSTEMD" = true ]; then
    echo -e "${YELLOW}⚙️  Step 5: Creating systemd service...${NC}"
    
    SERVICE_FILE="/etc/systemd/system/stratcon-frontend.service"
    
    if [ "$PRODUCTION_MODE" = true ]; then
        # Production service (build first, then start)
        sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Stratcon Next.js Frontend
After=network.target stratcon-api.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$FRONTEND_DIR
Environment="NEXT_PUBLIC_API_URL=$API_URL"
ExecStartPre=/usr/bin/npm run build
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    else
        # Development service
        sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Stratcon Next.js Frontend (Development)
After=network.target stratcon-api.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$FRONTEND_DIR
Environment="NEXT_PUBLIC_API_URL=$API_URL"
ExecStart=/usr/bin/npm run dev
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    sudo systemctl daemon-reload
    sudo systemctl enable stratcon-frontend
    echo -e "${GREEN}✅ Systemd service created${NC}"
    echo ""
    echo "   Start service: sudo systemctl start stratcon-frontend"
    echo "   Check status: sudo systemctl status stratcon-frontend"
    echo "   View logs: sudo journalctl -u stratcon-frontend -f"
    
elif [ "$SKIP_FRONTEND" != "true" ]; then
    echo -e "${YELLOW}🎨 Step 5: Starting frontend server...${NC}"
    
    if [ "$PRODUCTION_MODE" = true ]; then
        echo "   Building for production..."
        npm run build
        echo -e "${GREEN}✅ Build complete${NC}"
        echo "   Starting production server..."
        npm start > /tmp/stratcon_frontend.log 2>&1 &
        echo $! > /tmp/stratcon_frontend.pid
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
if [ "$CREATE_SYSTEMD" = false ]; then
    echo "To stop frontend:"
    echo "  pkill -f 'next'"
    echo "  Or: kill \$(cat /tmp/stratcon_frontend.pid)"
    echo ""
fi
echo "To view logs:"
if [ "$CREATE_SYSTEMD" = true ]; then
    echo "  sudo journalctl -u stratcon-frontend -f"
else
    echo "  tail -f /tmp/stratcon_frontend.log"
fi
echo ""

