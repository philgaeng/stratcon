#!/bin/bash
# Check status of Stratcon servers and nginx configuration
# Usage: ./scripts/check-server-status.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Stratcon Server Status Check${NC}"
echo "======================================"
echo ""

# Check backend
echo -e "${YELLOW}Backend Status:${NC}"
if systemctl is-active --quiet stratcon-api 2>/dev/null; then
    echo -e "${GREEN}  ✓ Backend service (systemd) is running${NC}"
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Backend API responding on port 8000${NC}"
    else
        echo -e "${RED}  ✗ Backend service running but not responding on port 8000${NC}"
    fi
elif lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Backend process running on port 8000${NC}"
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Backend API responding${NC}"
    else
        echo -e "${RED}  ✗ Backend port in use but not responding${NC}"
    fi
else
    echo -e "${RED}  ✗ Backend is not running${NC}"
fi
echo ""

# Check frontend
echo -e "${YELLOW}Frontend Status:${NC}"
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Frontend process running on port 3000${NC}"
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Frontend responding on port 3000${NC}"
    else
        echo -e "${RED}  ✗ Frontend port in use but not responding${NC}"
    fi
else
    echo -e "${RED}  ✗ Frontend is not running${NC}"
fi
echo ""

# Check nginx
echo -e "${YELLOW}Nginx Status:${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}  ✓ Nginx service is running${NC}"
    
    # Check nginx configuration
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        echo -e "${GREEN}  ✓ Nginx configuration is valid${NC}"
    else
        echo -e "${RED}  ✗ Nginx configuration has errors:${NC}"
        sudo nginx -t 2>&1 | grep -i error
    fi
    
    # Check what nginx is proxying to
    echo ""
    echo -e "${YELLOW}Nginx Configuration:${NC}"
    if [ -f /etc/nginx/sites-available/stratcon ]; then
        echo "  Found: /etc/nginx/sites-available/stratcon"
        echo ""
        echo "  Proxy configuration:"
        grep -A 5 "proxy_pass" /etc/nginx/sites-available/stratcon | head -10 || echo "    (no proxy_pass found)"
    elif [ -f /etc/nginx/sites-enabled/stratcon ]; then
        echo "  Found: /etc/nginx/sites-enabled/stratcon"
        echo ""
        echo "  Proxy configuration:"
        grep -A 5 "proxy_pass" /etc/nginx/sites-enabled/stratcon | head -10 || echo "    (no proxy_pass found)"
    else
        echo -e "${YELLOW}  ⚠️  No stratcon nginx config found${NC}"
        echo "  Checking default config..."
        if [ -f /etc/nginx/sites-enabled/default ]; then
            grep -A 5 "proxy_pass" /etc/nginx/sites-enabled/default | head -10 || echo "    (no proxy_pass in default)"
        fi
    fi
else
    echo -e "${RED}  ✗ Nginx service is not running${NC}"
fi
echo ""

# Check recent nginx errors
echo -e "${YELLOW}Recent Nginx Errors (last 10 lines):${NC}"
sudo tail -10 /var/log/nginx/error.log 2>/dev/null | grep -i "502\|bad gateway\|upstream\|connect" || echo "  (no recent errors found)"
echo ""

# Summary
echo -e "${BLUE}======================================"
echo "Summary:${NC}"
echo ""

BACKEND_OK=false
FRONTEND_OK=false
NGINX_OK=false

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    BACKEND_OK=true
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    FRONTEND_OK=true
fi

if systemctl is-active --quiet nginx 2>/dev/null && sudo nginx -t 2>&1 | grep -q "successful"; then
    NGINX_OK=true
fi

if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ] && [ "$NGINX_OK" = true ]; then
    echo -e "${GREEN}✅ All services are running correctly${NC}"
    echo ""
    echo "If you're still getting 502 errors:"
    echo "  1. Check nginx proxy_pass configuration points to correct ports"
    echo "  2. Verify nginx can access localhost:3000 and localhost:8000"
    echo "  3. Check firewall rules"
else
    echo -e "${YELLOW}⚠️  Some services need attention:${NC}"
    [ "$BACKEND_OK" = false ] && echo "  - Backend is not responding"
    [ "$FRONTEND_OK" = false ] && echo "  - Frontend is not responding"
    [ "$NGINX_OK" = false ] && echo "  - Nginx has issues"
    echo ""
    echo "To start servers:"
    echo "  ./scripts/launch-servers.sh --production --restart"
fi
echo ""

