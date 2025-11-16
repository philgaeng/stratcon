# Required Packages for Phase 1 API

## Core API Dependencies
- ✅ `fastapi>=0.100.0` - Web framework
- ✅ `uvicorn[standard]>=0.20.0` - ASGI server
- ✅ `pydantic>=2.0.0` - Data validation

## AWS Email Service (Optional)
- ❌ `boto3>=1.26.0` - AWS SDK for SES email sending

## Existing Data Science Stack (Already Installed)
- ✅ `pandas` - Data processing
- ✅ `plotly` - Chart generation
- ✅ `pytz` - Timezone handling

## Installation Command

```bash
conda activate datascience
pip install boto3
```

Or install all from requirements.txt:
```bash
conda activate datascience
pip install -r backend/requirements.txt
```

## Notes
- `boto3` is optional - API works without it, but email functionality requires it
- Email service will gracefully handle missing boto3 and log an error

