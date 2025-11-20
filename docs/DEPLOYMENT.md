# Deployment Guide

## Quick Start

### AWS Server Setup

**Server:** `52.221.59.184` (stratcon.facets-ai.com)  
**SSH:** `ssh -i ~/.ssh/aws-key.pem ubuntu@stratcon.facets-ai.com`

### Current Status

- ✅ **Backend**: Running via systemd (`stratcon-api.service`)
- ✅ **Frontend**: Running via systemd (`stratcon-frontend.service`)
- ✅ **Nginx**: Configured with SSL (Let's Encrypt)
- ✅ **SSL**: Active for `stratcon.facets-ai.com`
- ✅ **Domain**: DNS configured and working

### Deploying Updates

```bash
# 1. Sync changes to prod branch
./scripts/sync-to-prod.sh

# 2. SSH to server and pull latest
ssh -i ~/.ssh/aws-key.pem ubuntu@stratcon.facets-ai.com
cd ~/stratcon
git pull origin prod

# 3. Restart services if needed
sudo systemctl restart stratcon-api
sudo systemctl restart stratcon-frontend
```

### Managing Services

```bash
# Check status
sudo systemctl status stratcon-api
sudo systemctl status stratcon-frontend

# Restart services
sudo systemctl restart stratcon-api
sudo systemctl restart stratcon-frontend

# View logs
sudo journalctl -u stratcon-api -f
sudo journalctl -u stratcon-frontend -f

# Or use the scripts
./scripts/launch-servers.sh --production --restart
./scripts/stop-servers.sh
```

## Architecture

```
User Browser
    ↓ HTTPS (443)
Nginx (Reverse Proxy)
    ├─→ Frontend (port 3000) - Next.js
    └─→ Backend API (port 8000) - FastAPI
```

- **Frontend**: Next.js app served on port 3000
- **Backend**: FastAPI on port 8000
- **Nginx**: Proxies HTTPS → Frontend, `/api` → Backend
- **SSL**: Let's Encrypt certificate for `stratcon.facets-ai.com`

## Environment Configuration

### Backend Environment (`/etc/stratcon/env`)

```bash
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SES_SENDER_EMAIL=philippe@stratcon.ph
DATABASE_PATH=/var/lib/stratcon/data/settings.db
API_URL=https://stratcon.facets-ai.com/api
DEBUG=false
```

### Frontend Environment (`~/stratcon/website/.env.local`)

```bash
NEXT_PUBLIC_API_URL=https://stratcon.facets-ai.com/api
NEXT_PUBLIC_COGNITO_USER_POOL_ID=ap-southeast-1_HtVo9Y0BB
NEXT_PUBLIC_COGNITO_CLIENT_ID=384id7i8oh9vci2ck2afip4vsn
```

## Troubleshooting

### 502 Bad Gateway

**Cause**: Frontend or backend not running

**Fix**:
```bash
# Check services
sudo systemctl status stratcon-frontend stratcon-api

# Restart if needed
sudo systemctl restart stratcon-frontend
sudo systemctl restart stratcon-api

# Or use launch script
./scripts/launch-servers.sh --production --restart
```

### Services Not Starting

**Check logs**:
```bash
sudo journalctl -u stratcon-api -n 50
sudo journalctl -u stratcon-frontend -n 50
```

**Common issues**:
- Missing environment variables
- Database permissions
- Port conflicts

### Nginx Issues

**Check nginx config**:
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

**Reload nginx**:
```bash
sudo systemctl reload nginx
```

## Initial Server Setup

See `docs/SETUP.md` for complete initial setup instructions.

