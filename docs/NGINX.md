# Nginx Configuration

## Current Setup

Nginx is configured as a reverse proxy:
- **HTTPS (443)** → Frontend (port 3000)
- **`/api`** → Backend (port 8000)
- **SSL**: Let's Encrypt certificate

## Configuration File

Located at: `/etc/nginx/sites-available/stratcon`

Key features:
- HTTP to HTTPS redirect
- Frontend proxy with WebSocket support
- Backend API proxy
- Security headers
- SSL/TLS configuration

## Viewing Configuration

```bash
sudo cat /etc/nginx/sites-available/stratcon
```

## Testing Configuration

```bash
# Test syntax
sudo nginx -t

# Reload after changes
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

## Viewing Logs

```bash
# Error log
sudo tail -f /var/log/nginx/error.log

# Access log
sudo tail -f /var/log/nginx/access.log
```

## Common Issues

### 502 Bad Gateway

**Cause**: Frontend or backend not running

**Fix**:
```bash
# Check if services are running
sudo systemctl status stratcon-frontend stratcon-api

# Restart services
sudo systemctl restart stratcon-frontend
sudo systemctl restart stratcon-api
```

### SSL Certificate Issues

**Check certificate**:
```bash
sudo certbot certificates
```

**Renew certificate**:
```bash
sudo certbot renew
```

**Test renewal**:
```bash
sudo certbot renew --dry-run
```

## Updating Configuration

1. Edit config file:
   ```bash
   sudo nano /etc/nginx/sites-available/stratcon
   ```

2. Test configuration:
   ```bash
   sudo nginx -t
   ```

3. Reload nginx:
   ```bash
   sudo systemctl reload nginx
   ```

