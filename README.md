# Stratcon - Electricity Report Generator

Automated electricity consumption reporting system with interactive charts and analytics for building energy management.

## Quick Start

### Local Development

```bash
# Start backend and frontend
./scripts/launch-servers.sh

# Or manually:
conda activate datascience
cd backend && uvicorn api:app --host 0.0.0.0 --port 8000 --reload
cd website && npm run dev
```

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000

### Production Deployment

```bash
# Sync changes to prod
./scripts/sync-to-prod.sh

# Deploy to AWS (SSH to server)
ssh -i ~/.ssh/aws-key.pem ubuntu@stratcon.facets-ai.com
cd ~/stratcon && git pull origin prod
sudo systemctl restart stratcon-api stratcon-frontend
```

**Production URL**: https://stratcon.facets-ai.com

## Features

- ✅ **Report Generation**: Automated HTML reports with interactive charts
- ✅ **Authentication**: AWS Cognito integration
- ✅ **Email Delivery**: Automatic report distribution via AWS SES
- ✅ **Cutoff Logic**: Complex billing period calculations
- ✅ **Multi-tenant**: Support for multiple clients and buildings

## Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deploying to AWS
- **[Setup Guide](docs/SETUP.md)** - Initial server setup
- **[Authentication](docs/AUTHENTICATION.md)** - Cognito configuration
- **[Nginx Configuration](docs/NGINX.md)** - Reverse proxy setup
- **[Branch Workflow](docs/BRANCH_WORKFLOW.md)** - Git workflow
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture

## Project Structure

```
stratcon/
├── backend/          # FastAPI backend
├── website/          # Next.js frontend
├── scripts/          # Deployment scripts
└── docs/             # Documentation
```

## Tech Stack

**Backend:**
- FastAPI (Python)
- SQLite
- Pandas, Plotly
- AWS SES

**Frontend:**
- Next.js 16
- TypeScript
- Tailwind CSS
- AWS Cognito

**Infrastructure:**
- AWS EC2 (Ubuntu)
- Nginx
- Let's Encrypt SSL
- Systemd services

## Useful Commands

```bash
# Launch servers (local)
./scripts/launch-servers.sh

# Stop servers
./scripts/stop-servers.sh

# Sync to production
./scripts/sync-to-prod.sh

# Check server status (on AWS)
./scripts/check-server-status.sh
```

## Support

For issues or questions, check:
- Service logs: `sudo journalctl -u stratcon-api -f`
- Nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Documentation in `docs/` folder

---

**Production**: https://stratcon.facets-ai.com

