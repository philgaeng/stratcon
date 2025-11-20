#!/bin/bash
# Check nginx configuration via SSH
# Usage: ./scripts/ssh-check-nginx.sh [optional: ssh user@host]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default SSH connection
AWS_SERVER_IP="${AWS_SERVER_IP:-52.221.59.184}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/aws-key.pem}"
SSH_USER="${SSH_USER:-ubuntu}"
SSH_HOST="${1:-${SSH_USER}@${AWS_SERVER_IP}}"

echo -e "${BLUE}🔍 Checking Nginx Configuration via SSH${NC}"
echo "======================================"
echo ""
echo "Connecting to: $SSH_HOST"
echo ""

# Check if SSH key exists
if [ -n "$SSH_KEY" ] && [ -f "$SSH_KEY" ]; then
    SSH_OPTS="-i $SSH_KEY"
    echo -e "${GREEN}✓ Using SSH key: $SSH_KEY${NC}"
else
    SSH_OPTS=""
    echo -e "${YELLOW}⚠️  No SSH key specified, using default authentication${NC}"
fi

echo ""

# Run commands on remote server
ssh $SSH_OPTS "$SSH_HOST" << 'REMOTE_SCRIPT'
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Nginx Configuration Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check nginx installation
if ! command -v nginx >/dev/null 2>&1; then
    echo -e "${RED}✗ Nginx is not installed${NC}"
    exit 1
fi

echo -e "${CYAN}📦 Nginx Version:${NC}"
nginx -v 2>&1
echo ""

# Check nginx service status
echo -e "${CYAN}🔍 Nginx Service Status:${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
    systemctl status nginx --no-pager -l | head -5
else
    echo -e "${RED}✗ Nginx is not running${NC}"
fi
echo ""

# Find nginx config files
echo -e "${CYAN}📁 Nginx Configuration Files:${NC}"
echo ""

CONFIG_FILES=()

if [ -f "/etc/nginx/sites-available/stratcon" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-available/stratcon")
    echo -e "${GREEN}✓ Found: /etc/nginx/sites-available/stratcon${NC}"
fi

if [ -f "/etc/nginx/sites-enabled/stratcon" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-enabled/stratcon")
    echo -e "${GREEN}✓ Found: /etc/nginx/sites-enabled/stratcon${NC}"
fi

if [ -f "/etc/nginx/conf.d/stratcon.conf" ]; then
    CONFIG_FILES+=("/etc/nginx/conf.d/stratcon.conf")
    echo -e "${GREEN}✓ Found: /etc/nginx/conf.d/stratcon.conf${NC}"
fi

if [ -f "/etc/nginx/sites-enabled/default" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-enabled/default")
    echo -e "${YELLOW}⚠ Found: /etc/nginx/sites-enabled/default${NC}"
fi

if [ ${#CONFIG_FILES[@]} -eq 0 ]; then
    echo -e "${RED}✗ No nginx configuration files found${NC}"
fi

echo ""

# Display configuration content
for config_file in "${CONFIG_FILES[@]}"; do
    if [ -f "$config_file" ]; then
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}📄 File: ${config_file}${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        cat "$config_file"
        echo ""
        echo ""
    fi
done

# Check SSL certificates
echo -e "${CYAN}🔐 SSL Certificate Information:${NC}"
echo ""

# Let's Encrypt
if [ -d "/etc/letsencrypt/live/stratcon.facets-ai.com" ]; then
    echo -e "${GREEN}✓ Let's Encrypt certificate found:${NC}"
    echo "  Certificate: /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem"
    echo "  Key: /etc/letsencrypt/live/stratcon.facets-ai.com/privkey.pem"
    
    if command -v openssl >/dev/null 2>&1; then
        if [ -r "/etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem" ]; then
            EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem 2>/dev/null | cut -d= -f2)
            if [ -n "$EXPIRY" ]; then
                echo "  Expires: $EXPIRY"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠ No Let's Encrypt certificate found for stratcon.facets-ai.com${NC}"
fi

# Self-signed
if [ -d "/etc/nginx/ssl" ]; then
    echo ""
    echo -e "${YELLOW}Self-signed certificates:${NC}"
    ls -lh /etc/nginx/ssl/*.crt /etc/nginx/ssl/*.key /etc/nginx/ssl/*.pem 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (none found)"
fi

echo ""

# Test nginx configuration
echo -e "${CYAN}🧪 Testing nginx configuration:${NC}"
echo ""
sudo nginx -t 2>&1
echo ""

# Check what's listening on ports
echo -e "${CYAN}🔌 Port Status:${NC}"
echo ""
echo "Port 80 (HTTP):"
sudo lsof -i :80 -sTCP:LISTEN 2>/dev/null | head -3 || echo "  (not listening)"
echo ""
echo "Port 443 (HTTPS):"
sudo lsof -i :443 -sTCP:LISTEN 2>/dev/null | head -3 || echo "  (not listening)"
echo ""
echo "Port 3000 (Frontend):"
sudo lsof -i :3000 -sTCP:LISTEN 2>/dev/null | head -3 || echo -e "  ${RED}(not listening - this is likely the problem!)${NC}"
echo ""
echo "Port 8000 (Backend):"
sudo lsof -i :8000 -sTCP:LISTEN 2>/dev/null | head -3 || echo -e "  ${YELLOW}(not listening)${NC}"
echo ""

# Check recent nginx errors
echo -e "${CYAN}📊 Recent Nginx Error Log (last 20 lines):${NC}"
echo ""
if [ -f "/var/log/nginx/error.log" ]; then
    sudo tail -20 /var/log/nginx/error.log 2>/dev/null | grep -E "502|Bad Gateway|upstream|connect|refused|failed" || echo "  (no relevant errors found)"
else
    echo "  (error log not found)"
fi
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}📋 Summary:${NC}"
echo ""

# Check if frontend is running
if sudo lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running on port 3000${NC}"
else
    echo -e "${RED}✗ Frontend is NOT running on port 3000${NC}"
    echo "  This is likely causing the 502 error!"
    echo "  Start it with: ./scripts/launch-servers.sh --production --restart"
fi

# Check if backend is running
if sudo lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running on port 8000${NC}"
else
    echo -e "${YELLOW}⚠ Backend is NOT running on port 8000${NC}"
fi

# Check nginx config
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
fi

echo ""
REMOTE_SCRIPT

echo ""
echo -e "${GREEN}✅ Check complete!${NC}"
echo ""

