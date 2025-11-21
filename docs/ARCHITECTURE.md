# Architecture Overview

## System Architecture

```
User Browser
    ↓ HTTPS (443)
Nginx (Reverse Proxy)
    ├─→ Frontend (port 3000) - Next.js
    └─→ Backend API (port 8000) - FastAPI
        └─→ SQLite Database
```

## Technology Stack

### Backend
- **FastAPI** (Python) - REST API
- **SQLite** - Database
- **Pandas** - Data manipulation
- **AWS SES** - Email delivery
- **Uvicorn** - ASGI server
- **Conda** - Environment management (`datascience` environment)

### Frontend
- **Next.js 16** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling
- **AWS Cognito** - Authentication
- **Axios** - HTTP client

### Infrastructure
- **EC2** - Ubuntu 22.04 LTS
- **Nginx** - Reverse proxy and SSL termination
- **Let's Encrypt** - SSL certificates
- **Systemd** - Service management

## Server Recommendations

### Instance Types

- **t3.small** (2GB RAM) - ~$15/month
  - Very low traffic
  - Single user or small team
  - Tight on RAM

- **t3.medium** (4GB RAM) - ~$30/month ⭐ **Recommended**
  - Low to moderate traffic
  - Comfortable headroom
  - Good balance of cost and performance

- **t3.large** (8GB RAM) - ~$60/month
  - Production with moderate traffic
  - Multiple concurrent users

### Storage
- **30 GB gp3** EBS volume
- Enough for database, logs, reports

## Service Architecture

### Backend Service (`stratcon-api.service`)
- Runs via systemd
- Auto-starts on boot
- Restarts on failure
- Uses conda environment `datascience`

### Frontend Service (`stratcon-frontend.service`)
- Runs via systemd
- Auto-starts on boot
- Restarts on failure
- Production build (`npm start`)

### Nginx
- Handles SSL/TLS termination
- Proxies requests to frontend/backend
- HTTP to HTTPS redirect
- Security headers

## Data Flow

1. **User Request** → Nginx (HTTPS)
2. **Nginx** → Frontend (port 3000) or Backend API (port 8000)
3. **Backend** → SQLite Database
4. **Backend** → Generates reports
5. **Backend** → Sends email via AWS SES
6. **Response** → Nginx → User

## Security

- **HTTPS**: Let's Encrypt SSL certificates
- **Authentication**: AWS Cognito (JWT tokens)
- **CORS**: Configured for allowed origins
- **Security Groups**: Restrict access to necessary ports
- **Environment Variables**: Sensitive data in `/etc/stratcon/env`

## Monitoring

### Service Status
```bash
sudo systemctl status stratcon-api stratcon-frontend nginx
```

### Logs
```bash
# Backend logs
sudo journalctl -u stratcon-api -f

# Frontend logs
sudo journalctl -u stratcon-frontend -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Scaling Considerations

### Current Setup
- Single EC2 instance
- SQLite database
- Suitable for low to moderate traffic

### Future Scaling Options
- **Database**: Migrate to RDS PostgreSQL
- **Load Balancing**: Add Application Load Balancer
- **Auto Scaling**: EC2 Auto Scaling Groups
- **CDN**: CloudFront for static assets
- **Caching**: Redis for session/data caching

