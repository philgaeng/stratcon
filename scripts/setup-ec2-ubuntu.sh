#!/bin/bash
# EC2 Setup Script for Ubuntu 22.04 LTS
# Run this on a fresh Ubuntu 22.04 EC2 instance
# Usage: curl -sSL https://raw.githubusercontent.com/philgaeng/stratcon/prod/scripts/setup-ec2-ubuntu.sh | bash

set -e

echo "🚀 Setting up Stratcon on Ubuntu 22.04 EC2"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Update system
echo -e "${YELLOW}📦 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install essential tools
echo -e "${YELLOW}🔧 Installing essential tools...${NC}"
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    sqlite3 \
    nginx

# Install Node.js 20
echo -e "${YELLOW}📦 Installing Node.js 20...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
echo -e "${YELLOW}✅ Verifying installations...${NC}"
python3 --version
node --version
npm --version

# Install AWS CLI v2
echo -e "${YELLOW}☁️  Installing AWS CLI...${NC}"
if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
else
    echo "AWS CLI already installed"
fi

# Install Miniconda
echo -e "${YELLOW}🐍 Installing Miniconda...${NC}"
if [ ! -d "$HOME/miniconda3" ]; then
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
    rm Miniconda3-latest-Linux-x86_64.sh
    echo 'export PATH="$HOME/miniconda3/bin:$PATH"' >> ~/.bashrc
    export PATH="$HOME/miniconda3/bin:$PATH"
else
    echo "Miniconda already installed"
fi

# Create conda environment
echo -e "${YELLOW}🔨 Creating conda environment...${NC}"
source ~/miniconda3/etc/profile.d/conda.sh
if ! conda env list | grep -q "datascience"; then
    conda create -n datascience python=3.13 -y
fi

# Clone repository (if not already present)
if [ ! -d "stratcon" ]; then
    echo -e "${YELLOW}📥 Cloning repository...${NC}"
    git clone https://github.com/philgaeng/stratcon.git
    cd stratcon
    git checkout prod
else
    echo "Repository already exists"
    cd stratcon
    git checkout prod
    git pull origin prod
fi

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
conda activate datascience
pip install -r backend/requirements.txt

# Install Node.js dependencies
echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
cd website
npm install
cd ..

# Create directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
sudo mkdir -p /var/lib/stratcon/data
sudo mkdir -p /var/lib/stratcon/logs
sudo mkdir -p /var/lib/stratcon/reports
sudo chown -R $USER:$USER /var/lib/stratcon

# Create systemd service file
echo -e "${YELLOW}⚙️  Creating systemd service...${NC}"
sudo tee /etc/systemd/system/stratcon-api.service > /dev/null <<EOF
[Unit]
Description=Stratcon FastAPI Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$HOME/miniconda3/envs/datascience/bin:$PATH"
Environment="PYTHONPATH=$(pwd)"
ExecStart=$HOME/miniconda3/envs/datascience/bin/uvicorn backend.api.api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service (but don't start yet - need env vars first)
sudo systemctl daemon-reload
sudo systemctl enable stratcon-api

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Set up environment variables:"
echo "   sudo nano /etc/stratcon/env"
echo "   (See env.production.example for template)"
echo ""
echo "2. Update systemd service to load env file:"
echo "   sudo systemctl edit stratcon-api"
echo "   Add: EnvironmentFile=/etc/stratcon/env"
echo ""
echo "3. Initialize database:"
echo "   conda activate datascience"
echo "   cd $(pwd)"
echo "   python backend/scripts/populate_database.py"
echo ""
echo "4. Start the service:"
echo "   sudo systemctl start stratcon-api"
echo "   sudo systemctl status stratcon-api"
echo ""
echo "5. Configure nginx as reverse proxy (optional)"
echo ""
echo "📖 See DEPLOYMENT_GUIDE.md for detailed instructions"

