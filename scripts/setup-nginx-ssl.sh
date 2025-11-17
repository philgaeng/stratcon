#!/bin/bash
# Setup Nginx with SSL for Stratcon
# Usage: ./scripts/setup-nginx-ssl.sh [--self-signed] [--domain yourdomain.com]

set -e

SELF_SIGNED=false
DOMAIN=""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --self-signed|-s)
            SELF_SIGNED=true
            echo "Using self-signed certificate (for demo/testing)"
            ;;
        --domain=*)
            DOMAIN="${arg#*=}"
            ;;
        -d)
            shift
            DOMAIN="$1"
            ;;
    esac
done

AWS_SERVER_IP="${AWS_SERVER_IP:-52.221.59.184}"

echo "🚀 Setting up Nginx with SSL for Stratcon"
echo "=========================================="
echo ""

# Step 1: Create Nginx configuration
echo "📝 Step 1: Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/stratcon > /dev/null << EOF
# Upstream definitions
upstream backend_api {
    server 127.0.0.1:8000;
}

upstream frontend_app {
    server 127.0.0.1:3000;
}

# HTTP server (redirects to HTTPS)
server {
    listen 80;
    server_name ${DOMAIN:-$AWS_SERVER_IP};

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name ${DOMAIN:-$AWS_SERVER_IP};

    # SSL configuration (will be updated by certbot or self-signed)
    ssl_certificate /etc/nginx/ssl/stratcon.crt;
    ssl_certificate_key /etc/nginx/ssl/stratcon.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend (Next.js)
    location / {
        proxy_pass http://frontend_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend_api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Direct API access (for backward compatibility)
    location ~ ^/(clients|buildings|tenants|reports|settings|meters)/ {
        proxy_pass http://backend_api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "✅ Nginx configuration created"
echo ""

# Step 2: Create SSL directory
echo "📁 Step 2: Creating SSL directory..."
sudo mkdir -p /etc/nginx/ssl
echo "✅ SSL directory created"
echo ""

# Step 3: Generate SSL certificate
if [ "$SELF_SIGNED" = true ]; then
    echo "🔐 Step 3: Generating self-signed certificate..."
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/stratcon.key \
        -out /etc/nginx/ssl/stratcon.crt \
        -subj "/C=PH/ST=Metro Manila/L=Manila/O=Stratcon/CN=${DOMAIN:-$AWS_SERVER_IP}"
    echo "✅ Self-signed certificate created"
    echo "⚠️  Note: Browsers will show a security warning for self-signed certificates"
else
    echo "🔐 Step 3: SSL certificate setup..."
    if [ -z "$DOMAIN" ]; then
        echo "❌ Error: Domain name required for Let's Encrypt"
        echo "   Usage: $0 --domain yourdomain.com"
        echo "   Or use: $0 --self-signed (for testing)"
        exit 1
    fi
    
    echo "   Installing Certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    
    echo "   Getting Let's Encrypt certificate..."
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@stratcon.ph
    
    echo "✅ Let's Encrypt certificate installed"
fi

echo ""

# Step 4: Enable site
echo "🔗 Step 4: Enabling Nginx site..."
sudo ln -sf /etc/nginx/sites-available/stratcon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ Site enabled"
echo ""

# Step 5: Test configuration
echo "🧪 Step 5: Testing Nginx configuration..."
sudo nginx -t
echo "✅ Configuration test passed"
echo ""

# Step 6: Reload Nginx
echo "🔄 Step 6: Reloading Nginx..."
sudo systemctl reload nginx
echo "✅ Nginx reloaded"
echo ""

echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Frontend: https://${DOMAIN:-$AWS_SERVER_IP}"
echo "Backend API: https://${DOMAIN:-$AWS_SERVER_IP}/api/"
echo ""
if [ "$SELF_SIGNED" = true ]; then
    echo "⚠️  Self-signed certificate in use"
    echo "   Browsers will show a security warning"
    echo "   Click 'Advanced' → 'Proceed to site' to continue"
else
    echo "✅ Let's Encrypt certificate installed"
    echo "   Auto-renewal is configured"
fi
echo ""

