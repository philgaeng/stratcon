#!/bin/bash
# Check current nginx configuration
# Usage: ./scripts/check-nginx-config.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Current Nginx Configuration${NC}"
echo "======================================"
echo ""

# Check if nginx is installed
if ! command -v nginx >/dev/null 2>&1; then
    echo -e "${RED}✗ Nginx is not installed${NC}"
    exit 1
fi

# Check nginx status
echo -e "${YELLOW}Nginx Service Status:${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}  ✓ Nginx is running${NC}"
else
    echo -e "${RED}  ✗ Nginx is not running${NC}"
fi
echo ""

# List all nginx config files
echo -e "${YELLOW}Available Nginx Sites:${NC}"
echo ""
echo "Sites available:"
if [ -d "/etc/nginx/sites-available" ]; then
    ls -la /etc/nginx/sites-available/ | grep -v "^total" | grep -v "^d" | awk '{print "  " $9}' | grep -v "^$"
else
    echo "  (sites-available directory not found)"
fi
echo ""

echo "Sites enabled:"
if [ -d "/etc/nginx/sites-enabled" ]; then
    ls -la /etc/nginx/sites-enabled/ | grep -v "^total" | grep -v "^d" | awk '{print "  " $9}' | grep -v "^$"
else
    echo "  (sites-enabled directory not found)"
fi
echo ""

# Check for stratcon-specific config
echo -e "${YELLOW}Stratcon Configuration Files:${NC}"
STRATCON_CONFIGS=()

if [ -f "/etc/nginx/sites-available/stratcon" ]; then
    STRATCON_CONFIGS+=("/etc/nginx/sites-available/stratcon")
    echo -e "${GREEN}  ✓ Found: /etc/nginx/sites-available/stratcon${NC}"
fi

if [ -f "/etc/nginx/sites-enabled/stratcon" ]; then
    STRATCON_CONFIGS+=("/etc/nginx/sites-enabled/stratcon")
    echo -e "${GREEN}  ✓ Found: /etc/nginx/sites-enabled/stratcon${NC}"
fi

if [ -f "/etc/nginx/conf.d/stratcon.conf" ]; then
    STRATCON_CONFIGS+=("/etc/nginx/conf.d/stratcon.conf")
    echo -e "${GREEN}  ✓ Found: /etc/nginx/conf.d/stratcon.conf${NC}"
fi

if [ ${#STRATCON_CONFIGS[@]} -eq 0 ]; then
    echo -e "${YELLOW}  ⚠️  No stratcon-specific config found${NC}"
    echo "  Checking default config..."
    if [ -f "/etc/nginx/sites-enabled/default" ]; then
        STRATCON_CONFIGS+=("/etc/nginx/sites-enabled/default")
    fi
fi
echo ""

# Display configuration content
for config_file in "${STRATCON_CONFIGS[@]}"; do
    if [ -f "$config_file" ]; then
        echo -e "${BLUE}======================================"
        echo "Configuration: $config_file"
        echo "======================================${NC}"
        echo ""
        cat "$config_file"
        echo ""
        echo ""
    fi
done

# Check SSL certificates
echo -e "${YELLOW}SSL Certificates:${NC}"
if [ -d "/etc/letsencrypt/live" ]; then
    echo "  Let's Encrypt certificates found:"
    ls -la /etc/letsencrypt/live/ 2>/dev/null | grep "^d" | awk '{print "    " $9}' | grep -v "^\.$" | grep -v "^\.\.$"
    
    # Check for stratcon domain
    if [ -d "/etc/letsencrypt/live/stratcon.facets-ai.com" ]; then
        echo ""
        echo -e "${GREEN}  ✓ SSL certificate for stratcon.facets-ai.com found${NC}"
        echo "    Certificate: /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem"
        echo "    Key: /etc/letsencrypt/live/stratcon.facets-ai.com/privkey.pem"
        
        # Check certificate expiry
        if command -v openssl >/dev/null 2>&1; then
            EXPIRY=$(sudo openssl x509 -enddate -noout -in /etc/letsencrypt/live/stratcon.facets-ai.com/fullchain.pem 2>/dev/null | cut -d= -f2)
            if [ -n "$EXPIRY" ]; then
                echo "    Expires: $EXPIRY"
            fi
        fi
    fi
elif [ -d "/etc/nginx/ssl" ]; then
    echo "  Self-signed certificates found:"
    ls -la /etc/nginx/ssl/ 2>/dev/null | grep -E "\.(crt|key|pem)$" | awk '{print "    " $9}'
else
    echo -e "${YELLOW}  ⚠️  No SSL certificates directory found${NC}"
fi
echo ""

# Test nginx configuration
echo -e "${YELLOW}Nginx Configuration Test:${NC}"
if sudo nginx -t 2>&1; then
    echo ""
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo ""
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
fi
echo ""

# Show recent nginx errors
echo -e "${YELLOW}Recent Nginx Errors (last 20 lines):${NC}"
if [ -f "/var/log/nginx/error.log" ]; then
    sudo tail -20 /var/log/nginx/error.log | grep -i "502\|bad gateway\|upstream\|connect\|refused" || echo "  (no relevant errors found)"
else
    echo "  (error log not found)"
fi
echo ""

