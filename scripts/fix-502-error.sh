#!/bin/bash
# Fix 502 Bad Gateway error by ensuring servers are running and nginx is configured correctly
# Usage: ./scripts/fix-502-error.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Fixing 502 Bad Gateway Error${NC}"
echo "======================================"
echo ""

# Step 1: Check if servers are running
echo -e "${YELLOW}Step 1: Checking server status...${NC}"

BACKEND_RUNNING=false
FRONTEND_RUNNING=false

# Check backend
if systemctl is-active --quiet stratcon-api 2>/dev/null; then
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        BACKEND_RUNNING=true
        echo -e "${GREEN}  ✓ Backend is running and responding${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Backend service running but not responding${NC}"
    fi
elif lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        BACKEND_RUNNING=true
        echo -e "${GREEN}  ✓ Backend is running and responding${NC}"
    fi
else
    echo -e "${RED}  ✗ Backend is not running${NC}"
fi

# Check frontend
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        FRONTEND_RUNNING=true
        echo -e "${GREEN}  ✓ Frontend is running and responding${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Frontend port in use but not responding${NC}"
    fi
else
    echo -e "${RED}  ✗ Frontend is not running${NC}"
fi

echo ""

# Step 2: Start servers if needed
if [ "$BACKEND_RUNNING" = false ] || [ "$FRONTEND_RUNNING" = false ]; then
    echo -e "${YELLOW}Step 2: Starting servers...${NC}"
    echo ""
    
    # Use launch script to start servers
    if [ -f "./scripts/launch-servers.sh" ]; then
        ./scripts/launch-servers.sh --production --restart
    else
        echo -e "${RED}  ✗ launch-servers.sh not found${NC}"
        echo "  Please run: ./scripts/launch-servers.sh --production --restart"
    fi
    echo ""
fi

# Step 3: Check nginx configuration
echo -e "${YELLOW}Step 3: Checking nginx configuration...${NC}"

NGINX_CONFIG="/etc/nginx/sites-available/stratcon"
NGINX_ENABLED="/etc/nginx/sites-enabled/stratcon"

if [ ! -f "$NGINX_CONFIG" ] && [ ! -f "$NGINX_ENABLED" ]; then
    echo -e "${YELLOW}  ⚠️  Nginx config not found, creating it...${NC}"
    
    # Create nginx configuration
    sudo tee "$NGINX_CONFIG" > /dev/null << 'EOF'
server {
    listen 80;
    listen 443 ssl;
    server_name stratcon.facets-ai.com 52.221.59.184;

    # SSL configuration (self-signed for now)
    ssl_certificate /etc/nginx/ssl/stratcon.crt;
    ssl_certificate_key /etc/nginx/ssl/stratcon.key;

    # Frontend proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

    # Enable the site
    sudo ln -sf "$NGINX_CONFIG" "$NGINX_ENABLED"
    echo -e "${GREEN}  ✓ Nginx configuration created${NC}"
else
    echo -e "${GREEN}  ✓ Nginx configuration exists${NC}"
fi

# Check if SSL certificates exist
if [ ! -d "/etc/nginx/ssl" ]; then
    echo -e "${YELLOW}  ⚠️  SSL directory not found, creating self-signed certificate...${NC}"
    sudo mkdir -p /etc/nginx/ssl
    
    # Generate self-signed certificate
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/stratcon.key \
        -out /etc/nginx/ssl/stratcon.crt \
        -subj "/C=PH/ST=MetroManila/L=Taguig/O=Stratcon/CN=stratcon.facets-ai.com" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Self-signed certificate created${NC}"
    else
        echo -e "${RED}  ✗ Failed to create certificate${NC}"
    fi
fi

# Test nginx configuration
echo ""
echo -e "${YELLOW}Step 4: Testing nginx configuration...${NC}"
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}  ✓ Nginx configuration is valid${NC}"
    
    # Reload nginx
    echo "  Reloading nginx..."
    sudo systemctl reload nginx
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Nginx reloaded successfully${NC}"
    else
        echo -e "${RED}  ✗ Failed to reload nginx${NC}"
    fi
else
    echo -e "${RED}  ✗ Nginx configuration has errors:${NC}"
    sudo nginx -t
fi

echo ""
echo -e "${BLUE}======================================"
echo "✅ Fix complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Wait a few seconds for servers to start"
echo "  2. Test: curl -k https://stratcon.facets-ai.com"
echo "  3. Check logs if still having issues:"
echo "     - Backend: sudo journalctl -u stratcon-api -f"
echo "     - Frontend: tail -f /tmp/stratcon_frontend.log"
echo "     - Nginx: sudo tail -f /var/log/nginx/error.log"
echo ""

