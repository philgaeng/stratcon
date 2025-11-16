# AWS Server Recommendations for Stratcon

## Amazon Linux vs Ubuntu: Which to Choose?

### Quick Answer for Your Project

**Recommendation: Ubuntu 22.04 LTS** ✅

Since you're already developing on WSL (which typically uses Ubuntu), sticking with Ubuntu on AWS will:
- Match your development environment exactly
- Reduce deployment complexity
- Leverage your existing knowledge
- Provide better Python/Node.js package availability

However, **Amazon Linux 2023** is also a solid choice if you want deeper AWS integration.

---

## Detailed Comparison

### Amazon Linux 2023

**Pros:**
- ✅ **AWS-optimized**: Pre-configured for AWS services, better integration
- ✅ **Lightweight**: Smaller footprint, faster boot times
- ✅ **AWS support**: Direct AWS support channels
- ✅ **Free**: No licensing costs
- ✅ **Security**: Regular AWS-managed security updates
- ✅ **AWS CLI pre-installed**: Comes with AWS tools out of the box
- ✅ **Better performance**: Optimized for EC2 hardware

**Cons:**
- ❌ **Less familiar**: Different package manager (YUM/DNF vs APT)
- ❌ **Smaller community**: Less Stack Overflow answers, tutorials
- ❌ **Package availability**: Fewer packages in default repos
- ❌ **Python/Node setup**: Requires more manual configuration
- ❌ **Learning curve**: Different commands and structure

**Package Manager:**
```bash
# YUM/DNF (Amazon Linux)
sudo yum install python3 python3-pip
sudo dnf install nodejs npm  # AL2023 uses DNF
```

### Ubuntu 22.04 LTS

**Pros:**
- ✅ **Familiar**: Same as your WSL environment
- ✅ **Large community**: Extensive documentation and support
- ✅ **Package availability**: Huge repository of packages
- ✅ **Python/Node**: Easy installation via apt
- ✅ **Conda support**: Better conda integration
- ✅ **Long-term support**: LTS versions supported until 2027
- ✅ **Tutorials**: More deployment guides available

**Cons:**
- ❌ **Slightly larger**: More disk space required
- ❌ **AWS integration**: Requires manual AWS CLI/tools setup
- ❌ **Not AWS-optimized**: May have slightly higher overhead

**Package Manager:**
```bash
# APT (Ubuntu)
sudo apt update
sudo apt install python3 python3-pip python3-venv
sudo apt install nodejs npm
```

---

## Your Project Requirements

Based on your codebase:

### Backend Needs:
- Python 3.10+ (you're using conda `datascience` environment)
- FastAPI + Uvicorn
- Pandas, Plotly (data science libraries)
- SQLite (built-in, no extra setup)
- AWS SDK (boto3) for SES

### Frontend Needs:
- Node.js 20+ (Next.js 16)
- npm/yarn

### System Needs:
- ~2-4 GB RAM minimum (for data processing)
- ~20 GB storage (for database, logs, reports)
- Low to moderate CPU (web API, not compute-intensive)

---

## Recommended EC2 Instance Types

### Option 1: **t3.medium** (Recommended for Start) 💰

**Specs:**
- 2 vCPU
- 4 GB RAM
- Up to 5 Gbps network
- Burstable performance

**Cost:** ~$30-35/month (on-demand)

**Best for:**
- Development/demo environment
- Low to moderate traffic
- Your current project size

**Why:** Good balance of cost and performance. Burstable CPU handles your FastAPI + data processing needs.

### Option 2: **t3.large** (If you need more headroom)

**Specs:**
- 2 vCPU
- 8 GB RAM
- Up to 5 Gbps network

**Cost:** ~$60-70/month (on-demand)

**Best for:**
- Production with moderate traffic
- More concurrent users
- Larger data processing

### Option 3: **m5.large** (For consistent performance)

**Specs:**
- 2 vCPU
- 8 GB RAM
- Up to 10 Gbps network
- Consistent CPU (not burstable)

**Cost:** ~$75-85/month (on-demand)

**Best for:**
- Production with steady traffic
- When you need consistent CPU performance
- Better for data processing workloads

### Option 4: **t4g.medium** (ARM-based, cheaper)

**Specs:**
- 2 vCPU (ARM Graviton2)
- 4 GB RAM
- Up to 5 Gbps network

**Cost:** ~$25-30/month (on-demand) - **20-30% cheaper**

**Best for:**
- Cost optimization
- If your Python packages support ARM (most do)

**Note:** Verify your Python packages (especially pandas, plotly) work on ARM. Most do, but some scientific packages may need compilation.

---

## Setup Recommendations

### For Ubuntu 22.04 LTS:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and tools
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y build-essential git curl

# 3. Install Node.js 20 (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 4. Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 5. Install Miniconda (for your datascience environment)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Follow prompts, then:
conda create -n datascience python=3.10
conda activate datascience
pip install -r backend/requirements.txt
```

### For Amazon Linux 2023:

```bash
# 1. Update system
sudo dnf update -y

# 2. Install Python and tools
sudo dnf install -y python3.11 python3-pip git gcc
sudo dnf groupinstall -y "Development Tools"

# 3. Install Node.js 20 (via NodeSource)
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# 4. AWS CLI (usually pre-installed, but update if needed)
# Already included in AL2023

# 5. Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create -n datascience python=3.11
conda activate datascience
pip install -r backend/requirements.txt
```

---

## Cost Optimization Tips

1. **Use Reserved Instances**: Save 30-60% with 1-3 year commitments
2. **Use Spot Instances**: For non-critical workloads (save up to 90%)
3. **Start with t3.medium**: Scale up if needed
4. **Use ARM (t4g)**: 20-30% cheaper if compatible
5. **Auto-scaling**: Scale down during off-hours
6. **EBS optimization**: Use gp3 volumes (cheaper than gp2)

---

## Final Recommendation

### For Your Project:

**OS:** Ubuntu 22.04 LTS
- Matches your WSL environment
- Easier Python/Node.js setup
- Better conda support
- More familiar commands

**Instance:** t3.medium (start) → t3.large (scale up)
- Good balance of cost and performance
- Sufficient for FastAPI + data processing
- Easy to scale up later

**Storage:** 30 GB gp3 EBS volume
- Enough for database, logs, reports
- gp3 is cheaper and faster than gp2

**Network:** Default VPC is fine for start
- Add security groups for ports 8000 (API) and 443 (HTTPS via ALB)

---

## Migration Path

1. **Start**: t3.medium Ubuntu 22.04 (demo)
2. **Scale up**: t3.large if traffic increases
3. **Production**: m5.large if you need consistent CPU
4. **Optimize**: Consider t4g (ARM) for cost savings

---

## Security Considerations

Both OS options are secure, but:

- **Amazon Linux**: AWS-managed security updates
- **Ubuntu**: Community + Canonical security updates
- Both receive regular patches
- Use security groups to restrict access
- Enable automatic security updates on both

---

## Quick Decision Matrix

| Factor | Amazon Linux 2023 | Ubuntu 22.04 LTS |
|--------|------------------|------------------|
| **Familiarity** (WSL match) | ❌ Different | ✅ Same |
| **Python/Node setup** | ⚠️ Manual | ✅ Easy |
| **AWS integration** | ✅ Excellent | ⚠️ Manual |
| **Community support** | ⚠️ Smaller | ✅ Large |
| **Package availability** | ⚠️ Limited | ✅ Extensive |
| **Cost** | ✅ Free | ✅ Free |
| **Performance** | ✅ Optimized | ✅ Good |

**Winner for your use case: Ubuntu 22.04 LTS** 🏆

---

## Next Steps

1. Launch EC2 instance: Ubuntu 22.04 LTS, t3.medium
2. Configure security groups (ports 22, 8000, 443)
3. Set up environment variables (see `env.production.example`)
4. Deploy from `prod` branch
5. Set up systemd service for auto-start
6. Configure CloudWatch for monitoring

See `DEPLOYMENT_GUIDE.md` for detailed deployment steps.

