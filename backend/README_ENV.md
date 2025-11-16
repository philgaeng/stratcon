# Environment Configuration

## env.local File

The project uses `env.local` file in the project root for storing sensitive configuration like AWS credentials.

### Location
```
/home/philg/projects/stratcon/env.local
```

### Required Variables

```bash
# AWS Configuration for Email Service (SES)
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# SES Sender Email (verified email address)
SES_SENDER_EMAIL=your_verified_email@domain.com
```

### Loading Environment Variables

The environment variables are automatically loaded:
- When running API server (`uvicorn api:app`)
- When running test scripts (`test_email.py`, etc.)
- Via `load_env.py` utility

### Manual Loading

```python
from load_env import load_env_local
load_env_local()
```

### Security

- `env.local` is in `.gitignore` - never commit this file
- Keep credentials secure
- Rotate credentials periodically

