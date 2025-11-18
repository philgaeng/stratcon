# Troubleshooting Domain Timeout: stratcon.facets-ai.com

## Issue
Browser shows "ERR_CONNECTION_TIMED_OUT" when accessing `https://stratcon.facets-ai.com`

## Server Status ✅
- **DNS**: Resolves correctly to `52.221.59.184`
- **Frontend**: Running on port 3000
- **Nginx**: Configured and running
- **HTTPS**: Working (tested server-side)
- **Backend**: Running and responding

## Troubleshooting Steps

### 1. Clear Browser Cache & DNS Cache

**Windows (WSL):**
```bash
# Clear DNS cache
sudo systemd-resolve --flush-caches
# Or if using older system:
sudo service systemd-resolved restart
```

**Browser:**
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private window
- Hard refresh (Ctrl+F5)

### 2. Test Direct IP Access First

Before using the domain, test if the IP works:
```
https://52.221.59.184
```

If IP works but domain doesn't, it's a DNS propagation issue.

### 3. Check DNS Propagation

The domain was just created. DNS can take time to propagate globally:

```bash
# Check from different locations
nslookup stratcon.facets-ai.com
# Or use online tools:
# - https://dnschecker.org
# - https://www.whatsmydns.net
```

**Expected:** Should resolve to `52.221.59.184`

### 4. Self-Signed Certificate Warning

The server uses a self-signed certificate. Browsers will show a security warning:

1. Click "Advanced" or "Show Details"
2. Click "Proceed to site" or "Accept the risk"
3. The browser may cache this decision

**Note:** Some browsers/security software may block self-signed certs entirely.

### 5. Check Firewall/Security Software

- Windows Firewall
- Antivirus software
- Corporate firewall/proxy
- VPN connections

Try disabling temporarily to test.

### 6. Test from Different Network

- Try from mobile data (different network)
- Try from different location
- Use online tools like: https://downforeveryoneorjustme.com

### 7. Route 53 Health Check

Route 53 health checks are working (seen in nginx logs). If health checks fail, Route 53 may stop routing traffic.

**Check Route 53 Health Check Status:**
1. Go to AWS Console → Route 53
2. Check Health Checks
3. Verify status is "Healthy"

### 8. Browser-Specific Issues

**Chrome/Edge:**
- May block self-signed certs more aggressively
- Try: `chrome://flags/#allow-insecure-localhost` (for localhost)
- For production domain, you'll need a valid SSL cert

**Firefox:**
- Usually more lenient with self-signed certs
- Try Firefox if Chrome doesn't work

### 9. Alternative: Use IP Address Temporarily

For immediate testing, you can:
1. Access via IP: `https://52.221.59.184`
2. Update Cognito redirect URI to use IP temporarily
3. Once DNS fully propagates, switch back to domain

## Quick Test Commands

```bash
# Test DNS resolution
nslookup stratcon.facets-ai.com

# Test HTTPS connection
curl -k -v https://stratcon.facets-ai.com

# Test from server
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "curl -k https://localhost"
```

## Expected Behavior

Once working, you should see:
1. Browser connects to `https://stratcon.facets-ai.com`
2. Security warning (self-signed cert) - click "Advanced" → "Proceed"
3. Page loads and redirects to `/login`
4. Cognito login works
5. Redirects back to `https://stratcon.facets-ai.com/login`

## Next Steps

1. **For Production:** Get a valid SSL certificate (Let's Encrypt)
   ```bash
   ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184
   sudo certbot --nginx -d stratcon.facets-ai.com
   ```

2. **For Demo:** Use IP address if domain still has issues
   - Update Cognito: `https://52.221.59.184/login`
   - Access via: `https://52.221.59.184`

## Current Configuration

- **Domain:** stratcon.facets-ai.com
- **IP:** 52.221.59.184
- **Frontend:** Running on port 3000
- **Backend:** Running on port 8000
- **Nginx:** Proxying HTTPS (443) → Frontend (3000)
- **Cognito:** Configured for both domain and IP

