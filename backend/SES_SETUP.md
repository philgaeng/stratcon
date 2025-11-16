# AWS SES Email Setup Guide

## Prerequisites

To send emails via AWS SES, you need:

1. **AWS Account** with SES access
2. **AWS Credentials** configured
3. **Verified sender email** in SES
4. **Verified recipient** (if in SES sandbox mode)

## Setup Steps

### 1. Configure AWS Credentials

You can set credentials in several ways:

**Option A: Environment Variables (Recommended for testing)**
```bash
export AWS_REGION=us-east-1  # or your preferred region
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

**Option B: AWS Credentials File**
```bash
# Create/edit ~/.aws/credentials
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key

# Create/edit ~/.aws/config
[default]
region = us-east-1
```

**Option C: Using AWS CLI**
```bash
aws configure
```

### 2. Verify Sender Email in SES

1. Go to AWS SES Console
2. Navigate to "Verified identities" 
3. Click "Create identity"
4. Choose "Email address"
5. Enter your sender email (e.g., `noreply@stratcon.ph`)
6. Confirm verification email

### 3. Verify Recipient (If in Sandbox Mode)

SES sandbox mode only allows sending to verified emails:
1. Add recipient email to verified identities
2. Or request production access from AWS

### 4. Set Sender Email

Set the sender email that will be used:
```bash
export SES_SENDER_EMAIL=noreply@stratcon.ph
```

## Testing

After setting up credentials:

```bash
conda activate datascience
cd backend
python test_email.py
```

Or test via API:
```bash
curl -X POST http://localhost:8000/reports/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_token": "NEO3_0708",
    "client_token": "NEO",
    "user_email": "philgaeng@gmail.com"
  }'
```

## Quick Test with Temporary Credentials

If you have AWS CLI configured:

```bash
# Check if AWS CLI is configured
aws sts get-caller-identity

# Set region
export AWS_REGION=$(aws configure get region)

# Test email
conda activate datascience
cd backend
python test_email.py
```

## Troubleshooting

- **"Sender email not verified"**: Verify sender email in SES console
- **"Recipient email not verified"**: Verify recipient or request production access
- **"Invalid credentials"**: Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- **"Region not set"**: Set AWS_REGION environment variable

