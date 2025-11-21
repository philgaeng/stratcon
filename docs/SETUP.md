# Initial Server Setup

## Prerequisites

- AWS EC2 instance (Ubuntu 22.04 LTS recommended)
- SSH access configured
- Domain name (optional, for SSL)

## Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3 python3-venv python3-pip build-essential git curl

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
export PATH="$HOME/miniconda3/bin:$PATH"

# Create conda environment
conda create -n datascience python=3.13 -y
conda activate datascience
```

## Step 2: Clone Repository

```bash
cd ~
git clone https://github.com/philgaeng/stratcon.git
cd stratcon
git checkout prod
```

## Step 3: Install Dependencies

```bash
# Python dependencies
conda activate datascience
pip install -r backend/requirements.txt

# Node.js dependencies
cd website
npm install
cd ..
```

## Step 4: Setup Database

```bash
# Create directories
sudo mkdir -p /var/lib/stratcon/data
sudo mkdir -p /var/lib/stratcon/logs
sudo chown -R $USER:$USER /var/lib/stratcon

# Initialize database
conda activate datascience
python backend/scripts/populate_database.py
```

## Step 5: Configure Environment Variables

### Backend Environment

```bash
sudo nano /etc/stratcon/env
```

Add:
```bash
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
SES_SENDER_EMAIL=philippe@stratcon.ph
DATABASE_PATH=/var/lib/stratcon/data/settings.db
API_URL=https://stratcon.facets-ai.com/api
DEBUG=false
```

### Frontend Environment

```bash
cd ~/stratcon/website
nano .env.local
```

Add:
```bash
NEXT_PUBLIC_API_URL=https://stratcon.facets-ai.com/api
NEXT_PUBLIC_COGNITO_USER_POOL_ID=ap-southeast-1_HtVo9Y0BB
NEXT_PUBLIC_COGNITO_CLIENT_ID=384id7i8oh9vci2ck2afip4vsn
```

## Step 6: Setup Backend Service

The backend service should already be configured. Verify:

```bash
sudo systemctl status stratcon-api
```

If not configured, see `backend/README.md` for service setup.

## Step 7: Setup Frontend Service

```bash
cd ~/stratcon
sudo ./scripts/setup-frontend-service.sh
```

This will:
- Build the frontend
- Create systemd service
- Start and enable the service

## Step 8: Configure Nginx

Nginx should already be configured. Verify:

```bash
sudo nginx -t
sudo systemctl status nginx
```

If not configured, see `docs/NGINX.md` for setup.

## Step 9: Setup SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d stratcon.facets-ai.com
```

## Step 10: Verify Everything Works

```bash
# Check services
sudo systemctl status stratcon-api stratcon-frontend nginx

# Test locally
curl http://localhost:3000
curl http://localhost:8000

# Test externally
curl https://stratcon.facets-ai.com
```

## Instance Recommendations

- **Minimum**: t3.small (2GB RAM) - ~$15/month
- **Recommended**: t3.medium (4GB RAM) - ~$30/month
- **Production**: t3.large (8GB RAM) - ~$60/month

See `docs/ARCHITECTURE.md` for more details.

