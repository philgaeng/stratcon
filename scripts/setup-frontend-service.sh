#!/bin/bash
# Setup systemd service for Stratcon frontend
# Usage: ./scripts/setup-frontend-service.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚙️  Setting up Frontend Systemd Service${NC}"
echo "======================================"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/website"

# Get user
USER_NAME="${USER:-ubuntu}"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  This script needs sudo privileges${NC}"
    echo "Please run with: sudo ./scripts/setup-frontend-service.sh"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Frontend directory: $FRONTEND_DIR"
echo "  User: $USER_NAME"
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}✗ Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
    cd "$FRONTEND_DIR"
    sudo -u "$USER_NAME" npm install
fi

# Build the frontend first
echo -e "${YELLOW}📦 Building frontend for production...${NC}"
cd "$FRONTEND_DIR"
sudo -u "$USER_NAME" npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/stratcon-frontend.service"

echo -e "${YELLOW}📝 Creating systemd service...${NC}"

# Find node and npm paths
NODE_PATH=$(which node)
NPM_PATH=$(which npm)

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Stratcon Next.js Frontend
After=network.target stratcon-api.service

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$FRONTEND_DIR
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=$NPM_PATH start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created: $SERVICE_FILE${NC}"
echo ""

# Reload systemd
echo -e "${YELLOW}🔄 Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Daemon reloaded${NC}"
echo ""

# Enable service
echo -e "${YELLOW}🔧 Enabling service...${NC}"
systemctl enable stratcon-frontend
echo -e "${GREEN}✓ Service enabled${NC}"
echo ""

# Stop any existing frontend processes
echo -e "${YELLOW}🛑 Stopping any existing frontend processes...${NC}"
pkill -f "next" || true
sleep 2
echo -e "${GREEN}✓ Stopped existing processes${NC}"
echo ""

# Start the service
echo -e "${YELLOW}🚀 Starting frontend service...${NC}"
systemctl start stratcon-frontend
sleep 3

# Check status
if systemctl is-active --quiet stratcon-frontend; then
    echo -e "${GREEN}✓ Frontend service started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start service${NC}"
    echo "Check logs with: sudo journalctl -u stratcon-frontend -n 50"
    exit 1
fi

echo ""
echo -e "${BLUE}======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Service: stratcon-frontend"
echo "Status: $(systemctl is-active stratcon-frontend)"
echo ""
echo "Useful commands:"
echo "  Start:   sudo systemctl start stratcon-frontend"
echo "  Stop:    sudo systemctl stop stratcon-frontend"
echo "  Restart: sudo systemctl restart stratcon-frontend"
echo "  Status:  sudo systemctl status stratcon-frontend"
echo "  Logs:    sudo journalctl -u stratcon-frontend -f"
echo ""

