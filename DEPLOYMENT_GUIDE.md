# Deployment Guide - AWS

## Strategy Overview

This project uses a **two-branch strategy**:
- **`main`**: Development branch (WSL) - where you fix things and iterate
- **`prod`**: Production/demo branch (AWS) - stable demo environment

Both branches use the same codebase with environment-based configuration for differences.

> 📖 See `BRANCH_WORKFLOW.md` for detailed branch management workflow.

---

## Branch Strategy ✅

### Architecture

```
main branch (WSL Development)
  │
  │ [Sync when ready]
  │
  └─→ prod branch (AWS Demo/Production)
      ├── Same codebase (synced from main)
      ├── Different environment variables
      │   ├── WSL (main): env.local (dev config)
      │   └── AWS (prod): Environment variables (prod config)
      └── Stable demo environment
```

### Setup

#### 1. Environment Variables Structure

**Backend (`env.local` for dev, AWS Systems Manager Parameter Store for prod):**

```bash
# Development (WSL) - env.local
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=dev_key
AWS_SECRET_ACCESS_KEY=dev_secret
SES_SENDER_EMAIL=dev@stratcon.ph
DATABASE_PATH=./backend/data/settings.db
API_URL=http://localhost:8000
DEBUG=true

# Production (AWS) - Set in EC2/ECS/Lambda environment
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=prod_key  # Or use IAM roles
AWS_SECRET_ACCESS_KEY=prod_secret  # Or use IAM roles
SES_SENDER_EMAIL=noreply@stratcon.ph
DATABASE_PATH=/var/lib/stratcon/settings.db
API_URL=https://api.stratcon.ph
DEBUG=false
```

**Frontend (`.env.local` for dev, AWS Amplify/Vercel env vars for prod):**

```bash
# Development - website/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_COGNITO_USER_POOL_ID=dev_pool_id
NEXT_PUBLIC_COGNITO_CLIENT_ID=dev_client_id
NEXT_PUBLIC_COGNITO_REGION=ap-southeast-1

# Production - Set in AWS Amplify Console
NEXT_PUBLIC_API_URL=https://api.stratcon.ph
NEXT_PUBLIC_COGNITO_USER_POOL_ID=prod_pool_id
NEXT_PUBLIC_COGNITO_CLIENT_ID=prod_client_id
NEXT_PUBLIC_COGNITO_REGION=ap-southeast-1
```

#### 2. AWS Deployment Options

**Option A: EC2 Instance**
- Deploy backend to EC2
- Use environment variables from Systems Manager Parameter Store
- Deploy frontend to S3 + CloudFront or AWS Amplify

**Option B: ECS/Fargate**
- Containerize backend (Docker)
- Use ECS task definitions for environment variables
- Deploy frontend to Amplify

**Option C: Lambda + API Gateway**
- Convert backend to Lambda functions
- Use Lambda environment variables
- Deploy frontend to Amplify

#### 3. Deployment Workflow

```bash
# 1. Develop on WSL (main branch)
git checkout main
# ... make changes ...
git add .
git commit -m "Feature: ..."
git push origin main

# 2. Sync to prod when ready for demo/production
./scripts/sync-to-prod.sh

# 3. AWS deployment pulls from prod branch
# - AWS CodePipeline/CodeDeploy pulls from prod (not main)
# - Uses production environment variables
# - Deploys to production infrastructure
```

> 💡 **Tip**: Use `./scripts/check-branch-status.sh` to see what's different between branches before syncing.

---

### Architecture

```
main branch (WSL dev)
└── prod branch (AWS production)
    ├── Merged from main regularly
    └── Production-specific configs
```

### Branch Management

The `prod` branch is already set up. Use these scripts to manage it:

**Sync main → prod:**
```bash
./scripts/sync-to-prod.sh
```

**Check branch status:**
```bash
./scripts/check-branch-status.sh
```

See `BRANCH_WORKFLOW.md` for detailed workflow and best practices.

---

## AWS Infrastructure Recommendations

### Backend Deployment

1. **EC2 Instance**
   - **Recommended**: Ubuntu 22.04 LTS (matches WSL environment)
   - **Alternative**: Amazon Linux 2023 (better AWS integration)
   - Python 3.13 (via conda, matches dev environment)
   - Use `systemd` service for API
   - Store env vars in `/etc/stratcon/env` or Parameter Store
   - **Instance type**: Start with t3.medium, scale to t3.large or m5.large as needed
   
   > 📖 See `AWS_SERVER_RECOMMENDATIONS.md` for detailed OS comparison and instance type recommendations

2. **Database**
   - SQLite for small scale (current)
   - Consider RDS PostgreSQL for production scale
   - Backup strategy: S3 snapshots

3. **API Gateway**
   - Use API Gateway + Lambda for serverless
   - Or ALB + EC2 for traditional setup

### Frontend Deployment

1. **AWS Amplify** (Recommended)
   - Automatic deployments from Git
   - Environment variables in console
   - SSL certificates included
   - CDN built-in

2. **S3 + CloudFront**
   - Manual deployment
   - More control
   - Requires manual SSL setup

### Security

1. **Secrets Management**
   - Use AWS Secrets Manager for sensitive data
   - Or Systems Manager Parameter Store
   - Never commit secrets to Git

2. **IAM Roles**
   - Use IAM roles instead of access keys when possible
   - Least privilege principle

3. **Environment Variables**
   - All sensitive data via environment variables
   - Never hardcode credentials

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Environment variables documented
- [ ] Database migrations ready
- [ ] Backup strategy in place
- [ ] Monitoring/logging configured

### Backend Deployment

- [ ] EC2/ECS/Lambda configured
- [ ] Environment variables set
- [ ] Database initialized
- [ ] API accessible
- [ ] Health check endpoint working

### Frontend Deployment

- [ ] Build succeeds (`npm run build`)
- [ ] Environment variables set
- [ ] API URL points to production backend
- [ ] Cognito configured
- [ ] SSL certificate valid

### Post-Deployment

- [ ] Smoke tests passing
- [ ] Logs accessible
- [ ] Monitoring alerts configured
- [ ] Documentation updated

---

## Quick Start: Deploy to AWS

1. **Set up AWS resources:**
   - EC2 instance (for backend)
   - AWS Amplify app (for frontend)
   - RDS (optional, if not using SQLite)

2. **Configure environment variables in AWS:**
   - **Backend (EC2)**: Use Parameter Store, Secrets Manager, or `/etc/stratcon/env`
   - **Frontend (Amplify)**: Console → App settings → Environment variables
   - See `env.production.example` and `website/.env.production.example` for templates

3. **Deploy:**
   ```bash
   # 1. Develop on main (WSL)
   git checkout main
   # ... make changes ...
   git add .
   git commit -m "Feature: ..."
   git push origin main
   
   # 2. Sync to prod when ready
   ./scripts/sync-to-prod.sh
   
   # 3. AWS pulls from prod branch
   # - EC2: git pull origin prod (or auto-deploy via CodePipeline)
   # - Amplify: Auto-deploys on prod branch push
   ```

4. **Manual deployment (if not using CI/CD):**
   ```bash
   # On EC2 instance
   ssh ec2-instance
   cd /opt/stratcon
   git checkout prod
   git pull origin prod
   systemctl restart stratcon-api
   ```

---

## Troubleshooting

### Environment Variables Not Loading

- Check file paths in `load_env.py`
- Verify AWS Parameter Store access
- Check IAM permissions

### Database Issues

- Ensure database file permissions
- Check disk space
- Verify SQLite version compatibility

### API Not Accessible

- Check security groups (ports 8000/443)
- Verify ALB/API Gateway configuration
- Check application logs

---

## Next Steps

1. Choose deployment approach (single branch recommended)
2. Set up AWS infrastructure
3. Configure environment variables
4. Test deployment process
5. Set up CI/CD pipeline (optional but recommended)

