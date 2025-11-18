# AWS Deployment Status & Next Steps

**Server IP:** `52.221.59.184`  
**SSH Key:** `~/.ssh/aws-key.pem`  
**Date Checked:** November 16, 2025

---

## Architecture Overview

**Important:** This application uses a **client-side frontend architecture**:

```
User's Browser (Next.js Frontend)
    ↓ (direct HTTP requests)
AWS EC2 Server (FastAPI Backend on port 8000)
```

- **Frontend**: Next.js application that runs in the user's browser
- **API Access**: Browser makes direct HTTP requests to the API server
- **Implication**: The API must be **publicly accessible** from any user's browser
- **Security**: Use HTTPS, authentication, and Nginx reverse proxy for protection

This is different from server-side rendering where the frontend server would make requests on behalf of users.

---

## ✅ What's Already Done

### Infrastructure

- ✅ **EC2 Instance**: Running Ubuntu 24.04 LTS
- ✅ **Python**: 3.12.3 installed (system) + 3.13 via Miniconda (datascience environment)
- ✅ **Node.js**: v20.19.5 installed
- ✅ **Nginx**: Installed and running on port 80
- ✅ **Project**: Cloned to `/opt/stratcon` (or `~/stratcon`)
- ✅ **Database**: Exists at `/var/lib/stratcon/data/settings.db` (479MB)

### Application

- ✅ **Systemd Service**: `stratcon-api.service` is running and enabled
- ✅ **API**: Listening on `0.0.0.0:8000` internally
- ✅ **Environment Variables**: Configured at `/etc/stratcon/env`
- ✅ **Service Status**: Active and running (PID 15670)
- ✅ **Local Access**: API responds to `curl http://localhost:8000/`

### Service Details

```
Service: stratcon-api.service
Status: active (running)
Command: /home/ubuntu/miniconda3/envs/datascience/bin/uvicorn backend.api.api:app --host 0.0.0.0 --port 8000
Port: 8000 (listening internally)
```

---

## ❌ What's Missing (Next Steps)

### 1. AWS Security Group Configuration (CRITICAL)

**Problem:** The API is not accessible from outside because the Security Group is blocking port 8000.

**Important Architecture Note:**

- The frontend is a **Next.js client-side application** that runs in the user's browser
- The browser makes **direct HTTP requests** to the API server
- This means the API must be **publicly accessible** from any user's browser
- The Security Group must allow inbound traffic from anywhere users will access it

**Solution:** Configure AWS Security Group to allow inbound traffic:

1. **Go to AWS Console** → **EC2** → **Instances**
2. **Select your instance** (IP: 52.221.59.184)
3. **Click on Security Group** (in the details panel)
4. **Edit Inbound Rules** → **Add Rule**:
   - **Type**: Custom TCP
   - **Port**: `8000` (or `80` if using Nginx)
   - **Source**:
     - **For production**: `0.0.0.0/0` (anywhere) - **Required** because users' browsers need access
     - **For testing**: You can restrict to your IP temporarily, but you'll need to open it up for real users
   - **Description**: "Stratcon API - Public access from user browsers"
5. **Save rules**

**Security Note:** Since the API is accessed directly by browsers, you should:

- Use HTTPS (port 443) instead of HTTP when possible
- Implement proper authentication (Cognito JWT tokens)
- Use Nginx as a reverse proxy for additional security layers

**Alternative:** If using Nginx (recommended), allow port 80/443 instead:

- **Port 80**: HTTP (for testing)
- **Port 443**: HTTPS (for production with SSL)

---

### 2. Configure Nginx as Reverse Proxy (RECOMMENDED)

**Current Status:** Nginx is running but using default configuration (not proxying to API).

**Why:**

- Better security (hide internal port 8000)
- Can add SSL/HTTPS easily
- Standard web server setup
- Can serve frontend later

**Steps:**

1. **SSH into the server:**

   ```bash
   ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184
   ```

2. **Create Nginx configuration:**

   ```bash
   sudo nano /etc/nginx/sites-available/stratcon
   ```

3. **Paste this configuration:**

   ```nginx
   server {
       listen 80;
       server_name 52.221.59.184;  # Or your domain name if you have one

       # API proxy
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       # Health check endpoint (optional)
       location /health {
           proxy_pass http://127.0.0.1:8000/;
           access_log off;
       }
   }
   ```

4. **Enable the site:**

   ```bash
   sudo ln -s /etc/nginx/sites-available/stratcon /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default  # Remove default config
   ```

5. **Test Nginx configuration:**

   ```bash
   sudo nginx -t
   ```

6. **Reload Nginx:**

   ```bash
   sudo systemctl reload nginx
   ```

7. **Update Security Group:**

   - Remove port 8000 rule (if you added it)
   - Add port 80 rule (HTTP)
   - Add port 443 rule (HTTPS, for later SSL setup)

8. **Test from your local machine:**
   ```bash
   curl http://52.221.59.184/
   ```

---

### 3. Set Up SSL/HTTPS (OPTIONAL but Recommended)

**Using Let's Encrypt (Free SSL):**

1. **Install Certbot:**

   ```bash
   sudo apt update
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. **Get SSL Certificate:**

   ```bash
   # If you have a domain name:
   sudo certbot --nginx -d yourdomain.com

   # If you only have IP address, you'll need to use a different method
   # or set up a domain name first
   ```

3. **Auto-renewal is set up automatically**

**Note:** Let's Encrypt requires a domain name. If you only have an IP address, you can:

- Use AWS Route 53 to create a domain
- Or use a free domain service
- Or skip SSL for now (not recommended for production)

---

### 4. Update CORS Settings (If Frontend is Separate)

**Current CORS:** Only allows `localhost:3000`, `localhost:3001`

**If your frontend will be on a different domain, update:**

1. **SSH into server:**

   ```bash
   ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184
   ```

2. **Edit CORS settings:**

   ```bash
   cd /opt/stratcon  # or wherever the project is
   nano backend/api/api.py
   ```

3. **Update the CORS middleware (around line 39-49):**

   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "http://localhost:3000",
           "http://127.0.0.1:3000",
           "http://localhost:3001",
           "http://52.221.59.184",  # Add your server IP
           "https://yourdomain.com",  # Add your domain if you have one
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **Restart the service:**
   ```bash
   sudo systemctl restart stratcon-api
   ```

---

## Quick Access Commands

### SSH into Server

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184
```

### Check Service Status

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "sudo systemctl status stratcon-api"
```

### View Service Logs

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "sudo journalctl -u stratcon-api -n 50 --no-pager"
```

### Restart Service

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "sudo systemctl restart stratcon-api"
```

### Test API Locally (on server)

```bash
ssh -i ~/.ssh/aws-key.pem ubuntu@52.221.59.184 "curl http://localhost:8000/"
```

### Test API from Your Machine (after Security Group is configured)

```bash
curl http://52.221.59.184:8000/
# Or if using Nginx:
curl http://52.221.59.184/
```

---

## Priority Order

1. **🔴 HIGH PRIORITY**: Configure AWS Security Group (Step 1)

   - Without this, the API is completely inaccessible from outside
   - Takes 2 minutes in AWS Console

2. **🟡 MEDIUM PRIORITY**: Configure Nginx (Step 2)

   - Better security and standard setup
   - Takes 5-10 minutes
   - Makes future SSL setup easier

3. **🟢 LOW PRIORITY**: Set up SSL/HTTPS (Step 3)

   - Requires domain name
   - Can be done later
   - Important for production

4. **🟢 LOW PRIORITY**: Update CORS (Step 4)
   - Only needed if frontend is on different domain
   - Can be done when deploying frontend

---

## Testing Checklist

After completing each step, test:

- [ ] Security Group configured → `curl http://52.221.59.184:8000/` works
- [ ] Nginx configured → `curl http://52.221.59.184/` works
- [ ] SSL configured → `curl https://yourdomain.com/` works
- [ ] API endpoints respond correctly
- [ ] Frontend can connect (if deployed)

---

## Current Environment Variables

Located at: `/etc/stratcon/env`

```bash
AWS_REGION=ap-southeast-1
SES_SENDER_EMAIL=noreply@stratcon.ph
DATABASE_PATH=/var/lib/stratcon/data/settings.db
API_URL=http://52.221.59.184:8000
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

**Note:** After setting up Nginx/SSL, you may want to update `API_URL` to use HTTPS.

---

## Troubleshooting

### API Not Accessible from Outside

- ✅ Check Security Group allows port 8000 (or 80 if using Nginx)
- ✅ Check service is running: `sudo systemctl status stratcon-api`
- ✅ Check firewall: `sudo ufw status` (should be inactive or allow the port)

### Nginx Not Working

- ✅ Check config: `sudo nginx -t`
- ✅ Check Nginx status: `sudo systemctl status nginx`
- ✅ Check logs: `sudo tail -f /var/log/nginx/error.log`

### Service Won't Start

- ✅ Check logs: `sudo journalctl -u stratcon-api -n 50`
- ✅ Check environment file: `sudo cat /etc/stratcon/env`
- ✅ Check database permissions: `ls -la /var/lib/stratcon/data/`

---

## Next Steps Summary

1. **Configure AWS Security Group** (2 min) - Allow port 8000 or 80
2. **Configure Nginx** (10 min) - Set up reverse proxy
3. **Test API access** (1 min) - Verify it works from your machine
4. **Set up SSL** (15 min) - If you have a domain name
5. **Update CORS** (5 min) - If frontend is on different domain

**Estimated Total Time:** 30-45 minutes

---

## Support

If you encounter issues:

1. Check service logs: `sudo journalctl -u stratcon-api -n 100`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify Security Group in AWS Console
4. Test locally on server first: `curl http://localhost:8000/`
