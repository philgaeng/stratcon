# AWS Quick Start Guide

## Step-by-Step: Launch and Deploy to AWS

### Step 1: Launch EC2 Instance

1. **Go to AWS Console** → **EC2** → **Launch Instance**

2. **Configure Instance:**
   - **Name**: `stratcon-demo` (or any name you like)
   - **AMI**: Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance type**: `t3.small` (or `t3.medium` for more headroom)
   - **Key pair**: Create new or select existing (you'll need this to SSH)
   - **Network settings**: 
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 8000) from anywhere (or your IP for testing)
   - **Storage**: 20-30 GB gp3 (default is fine)

3. **Click "Launch Instance"**

4. **Wait for instance to be "Running"** (green status)

---

### Step 2: SSH into Your Instance

**On Windows (WSL or PowerShell):**

```bash
# Replace with your key file path and instance IP
ssh -i /path/to/your-key.pem ubuntu@YOUR_INSTANCE_IP
```

**Or if you're in WSL and the key is in Windows:**

```bash
ssh -i /mnt/c/Users/YourName/path/to/key.pem ubuntu@YOUR_INSTANCE_IP
```

**Find your instance IP:**
- AWS Console → EC2 → Your instance → "Public IPv4 address"

---

### Step 3: Run the Setup Script (Easiest Way) ✅

The script does **everything automatically**:
- ✅ Installs Python, Node.js, AWS CLI, Miniconda
- ✅ Creates conda environment called `datascience`
- ✅ Clones your repository from `prod` branch
- ✅ Installs all packages from `requirements.txt`
- ✅ Creates systemd service (ready to start)

**Just run this one command:**

```bash
# On your EC2 instance (after SSH)
curl -sSL https://raw.githubusercontent.com/philgaeng/stratcon/prod/scripts/setup-ec2-ubuntu.sh | bash
```

**That's it!** The script handles everything.

---

### Step 4: Set Up Environment Variables

After the script finishes, you need to set production environment variables:

```bash
# Create environment file
sudo nano /etc/stratcon/env
```

**Paste this (update with your values):**

```bash
# AWS Configuration
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your_prod_access_key
AWS_SECRET_ACCESS_KEY=your_prod_secret_key

# SES Email
SES_SENDER_EMAIL=noreply@stratcon.ph

# Database
DATABASE_PATH=/var/lib/stratcon/data/settings.db

# API
API_URL=https://api.stratcon.ph
DEBUG=false
```

**Save and exit** (Ctrl+X, then Y, then Enter)

---

### Step 5: Update Systemd Service to Load Environment

```bash
# Edit the service to load environment file
sudo systemctl edit stratcon-api
```

**Add these lines:**

```ini
[Service]
EnvironmentFile=/etc/stratcon/env
```

**Save and exit**, then reload:

```bash
sudo systemctl daemon-reload
```

---

### Step 6: Initialize Database

```bash
# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate datascience

# Go to project directory
cd ~/stratcon

# Initialize database
python backend/scripts/populate_database.py
```

---

### Step 7: Start the Service

```bash
# Start the API service
sudo systemctl start stratcon-api

# Check status
sudo systemctl status stratcon-api

# Enable auto-start on boot
sudo systemctl enable stratcon-api
```

---

### Step 8: Test It

```bash
# Check if API is running
curl http://localhost:8000/

# Or from your local machine (replace with your EC2 IP)
curl http://YOUR_INSTANCE_IP:8000/
```

---

## Alternative: Manual Setup (If You Prefer)

If you want to do it manually instead of using the script:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and tools
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential git curl

# 3. Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 4. Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
export PATH="$HOME/miniconda3/bin:$PATH"

# 5. Create conda environment
conda create -n datascience python=3.10 -y
conda activate datascience

# 6. Clone repository
git clone https://github.com/philgaeng/stratcon.git
cd stratcon
git checkout prod

# 7. Install Python packages
pip install -r backend/requirements.txt

# 8. Install Node.js packages (if deploying frontend on same server)
cd website
npm install
cd ..

# 9. Create directories
sudo mkdir -p /var/lib/stratcon/data
sudo mkdir -p /var/lib/stratcon/logs
sudo chown -R $USER:$USER /var/lib/stratcon
```

**But the script does all of this automatically!** ⚡

---

## What the Script Does vs Manual

| Task | Script | Manual |
|------|--------|--------|
| Install Python/Node.js | ✅ | ❌ You do it |
| Install Miniconda | ✅ | ❌ You do it |
| Create conda env `datascience` | ✅ | ❌ You do it |
| Clone repo from `prod` | ✅ | ❌ You do it |
| Install requirements.txt | ✅ | ❌ You do it |
| Create systemd service | ✅ | ❌ You do it |
| Set environment variables | ❌ | ❌ You do it |
| Initialize database | ❌ | ❌ You do it |
| Start service | ❌ | ❌ You do it |

**Recommendation:** Use the script! It saves you 10+ steps.

---

## Troubleshooting

### Can't SSH into instance?
- Check security group allows SSH (port 22) from your IP
- Verify key file permissions: `chmod 400 your-key.pem`
- Make sure you're using `ubuntu` user (not `ec2-user`)

### Script fails?
- Check internet connection on EC2
- Make sure instance has enough disk space (20GB+)
- Check logs: The script will show errors

### Service won't start?
- Check logs: `sudo journalctl -u stratcon-api -n 50`
- Verify environment variables are set: `cat /etc/stratcon/env`
- Check database exists: `ls -la /var/lib/stratcon/data/`

### API not accessible?
- Check security group allows port 8000
- Verify service is running: `sudo systemctl status stratcon-api`
- Check firewall: `sudo ufw status`

---

## Next Steps After Setup

1. **Set up domain** (optional): Point domain to EC2 IP
2. **Set up SSL** (optional): Use Let's Encrypt with nginx
3. **Deploy frontend** (optional): Deploy to AWS Amplify or run on same server
4. **Set up monitoring**: CloudWatch alarms
5. **Set up backups**: Automated EBS snapshots

---

## Quick Reference

```bash
# SSH into instance
ssh -i key.pem ubuntu@INSTANCE_IP

# Run setup script
curl -sSL https://raw.githubusercontent.com/philgaeng/stratcon/prod/scripts/setup-ec2-ubuntu.sh | bash

# Set environment variables
sudo nano /etc/stratcon/env

# Update systemd service
sudo systemctl edit stratcon-api
# Add: EnvironmentFile=/etc/stratcon/env

# Initialize database
conda activate datascience
python backend/scripts/populate_database.py

# Start service
sudo systemctl start stratcon-api
sudo systemctl status stratcon-api
```

---

## Cost Estimate

- **t3.small**: ~$15/month
- **t3.medium**: ~$30/month
- **EBS storage (30GB)**: ~$3/month
- **Data transfer**: Minimal for low traffic
- **Total**: ~$18-33/month

