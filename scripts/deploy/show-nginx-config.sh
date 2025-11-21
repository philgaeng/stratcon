#!/bin/bash
# Display current nginx configuration in a readable format
# Usage: ./scripts/show-nginx-config.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Nginx Configuration Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some operations may require sudo${NC}"
    echo ""
fi

# Find all nginx config files
echo -e "${CYAN}📁 Searching for nginx configuration files...${NC}"
echo ""

CONFIG_FILES=()

# Check common locations
if [ -f "/etc/nginx/nginx.conf" ]; then
    CONFIG_FILES+=("/etc/nginx/nginx.conf")
fi

if [ -f "/etc/nginx/sites-available/stratcon" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-available/stratcon")
fi

if [ -f "/etc/nginx/sites-enabled/stratcon" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-enabled/stratcon")
fi

if [ -f "/etc/nginx/conf.d/stratcon.conf" ]; then
    CONFIG_FILES+=("/etc/nginx/conf.d/stratcon.conf")
fi

if [ -f "/etc/nginx/sites-enabled/default" ]; then
    CONFIG_FILES+=("/etc/nginx/sites-enabled/default")
fi

if [ ${#CONFIG_FILES[@]} -eq 0 ]; then
    echo -e "${RED}✗ No nginx configuration files found${NC}"
    echo ""
    echo "Checking nginx installation..."
    if command -v nginx >/dev/null 2>&1; then
        echo "  Nginx version: $(nginx -v 2>&1)"
        echo "  Config test:"
        sudo nginx -t 2>&1 | head -5
    else
        echo "  Nginx is not installed"
    fi
    exit 1
fi

# Display each config file
for config_file in "${CONFIG_FILES[@]}"; do
    if [ -f "$config_file" ]; then
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}📄 File: ${config_file}${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        
        # Use sudo if needed to read the file
        if [ -r "$config_file" ]; then
            cat "$config_file"
        else
            sudo cat "$config_file" 2>/dev/null || echo -e "${RED}Cannot read file (permission denied)${NC}"
        fi
        
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
    
    if command -v openssl >/dev/null 2>&1 && [ -r "/etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem" ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem 2>/dev/null | cut -d= -f2)
        if [ -n "$EXPIRY" ]; then
            echo "  Expires: $EXPIRY"
        fi
    fi
elif sudo test -d "/etc/letsencrypt/live/stratcon.facets-ai.com" 2>/dev/null; then
    echo -e "${GREEN}✓ Let's Encrypt certificate found (requires sudo to read):${NC}"
    echo "  Certificate: /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem"
    echo "  Key: /etc/letsencrypt/live/stratcon.facets-ai.com/privkey.pem"
fi

# Self-signed
if [ -d "/etc/nginx/ssl" ]; then
    echo ""
    echo -e "${YELLOW}Self-signed certificates:${NC}"
    ls -lh /etc/nginx/ssl/*.crt /etc/nginx/ssl/*.key /etc/nginx/ssl/*.pem 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
fi

echo ""

# Check nginx status
echo -e "${CYAN}🔍 Nginx Status:${NC}"
echo ""

if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx service is running${NC}"
else
    echo -e "${RED}✗ Nginx service is not running${NC}"
fi

echo ""
echo -e "${CYAN}🧪 Testing nginx configuration:${NC}"
echo ""
sudo nginx -t 2>&1

echo ""
echo -e "${CYAN}📊 Recent nginx error log (last 10 lines):${NC}"
echo ""
if [ -f "/var/log/nginx/error.log" ]; then
    sudo tail -10 /var/log/nginx/error.log 2>/dev/null || echo "  (cannot read error log)"
else
    echo "  (error log not found)"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

