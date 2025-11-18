# Update to New Domain: stratcon.facets-ai.com

This guide walks you through updating all configurations to use the new domain `stratcon.facets-ai.com`.

## ✅ Completed Steps

1. **CORS Settings Updated** - Added `https://stratcon.facets-ai.com` to backend CORS allowed origins
2. **Nginx Update Script Created** - `scripts/update-domain-on-aws.sh` ready to run

## 🔄 Steps to Complete

### Step 1: Update Nginx on AWS Server

Run the update script to configure nginx for the new domain:

```bash
./scripts/update-domain-on-aws.sh
```

This script will:
- Update nginx configuration to accept both `stratcon.facets-ai.com` and `52.221.59.184`
- Test nginx configuration
- Reload nginx
- Check and restart frontend if needed

### Step 2: Update Cognito Redirect URIs

Add the new domain to your Cognito App Client:

**Option A: Using AWS CLI (Recommended)**

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id ap-southeast-1_HtVo9Y0BB \
  --client-id 384id7i8oh9vci2ck2afip4vsn \
  --callback-urls \
    "http://localhost:3000/login" \
    "https://52.221.59.184/login" \
    "https://stratcon.facets-ai.com/login" \
  --logout-urls \
    "http://localhost:3000/login" \
    "https://52.221.59.184/login" \
    "https://stratcon.facets-ai.com/login" \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "openid" "email" "profile" \
  --allowed-o-auth-flows-user-pool-client
```

**Option B: Using AWS Console**

1. Go to **AWS Console** → **Cognito** → **User Pools**
2. Select your user pool: `ap-southeast-1_HtVo9Y0BB`
3. Go to **App integration** → **App clients**
4. Click on your app client: `384id7i8oh9vci2ck2afip4vsn`
5. Scroll to **Hosted UI** section
6. Under **Callback URL(s)**, add:
   - `https://stratcon.facettes-ai.com/login`
7. Under **Sign-out URL(s)**, add:
   - `https://stratcon.facettes-ai.com/login`
8. Click **Save changes**

### Step 3: Deploy Backend Changes

The CORS settings have been updated in the code. Deploy to AWS:

```bash
# Make sure you're on main branch
git checkout main

# Commit the CORS changes
git add backend/api/api.py
git commit -m "Add stratcon.facets-ai.com to CORS allowed origins"

# Sync to prod
./scripts/sync-to-prod.sh

# SSH to AWS and restart backend
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "sudo systemctl restart stratcon-api"
```

### Step 4: Test the New Domain

1. **Test HTTPS access:**
   ```bash
   curl -k https://stratcon.facets-ai.com
   ```
   (The `-k` flag ignores self-signed certificate warnings)

2. **Test in browser:**
   - Go to `https://stratcon.facets-ai.com`
   - Accept the self-signed certificate warning (if using self-signed cert)
   - Click "Sign in"
   - After Cognito login, verify redirect goes to `https://stratcon.facets-ai.com/login`

3. **Check browser console:**
   - Open DevTools (F12)
   - Check for any CORS errors
   - Verify API calls are working

## 🔐 SSL Certificate Options

### Current: Self-Signed Certificate
- Works for demo/testing
- Browser will show security warning
- Users must click "Advanced" → "Proceed to site"

### Future: Let's Encrypt Certificate (Recommended for Production)

Once DNS has fully propagated, you can get a free SSL certificate:

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184

# Install certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d stratcon.facets-ai.com

# Auto-renewal is set up automatically
```

## 📋 Verification Checklist

- [ ] Nginx updated and reloaded on AWS
- [ ] Frontend service running on port 3000
- [ ] Cognito redirect URIs updated
- [ ] Backend CORS updated and deployed
- [ ] Backend service restarted
- [ ] HTTPS access working: `https://stratcon.facets-ai.com`
- [ ] Login flow working with new domain
- [ ] No CORS errors in browser console

## 🐛 Troubleshooting

### 502 Bad Gateway
- **Cause**: Frontend not running on port 3000
- **Fix**: Check frontend service status and restart if needed
  ```bash
  ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184
  cd ~/stratcon/website
  npm run start
  ```

### CORS Errors
- **Cause**: Backend CORS not updated or backend not restarted
- **Fix**: Verify CORS settings in `backend/api/api.py` and restart backend

### Redirect to localhost
- **Cause**: Cognito redirect URI not updated
- **Fix**: Update Cognito App Client callback URLs (Step 2 above)

### SSL Certificate Warning
- **Expected**: If using self-signed certificate
- **Fix**: Use Let's Encrypt for production (see SSL Certificate Options above)

