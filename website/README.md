# Stratcon Website - Electricity Report Generator

Next.js frontend for the Stratcon electricity report generation system.

## Features

- **Authentication**: AWS Cognito login (to be configured)
- **Report Generation**: Simple form to select client, tenant, month, and cutoff date/time
- **Email Delivery**: Reports are automatically sent to user's email
- **Brand Styling**: Matches Stratcon brand colors and fonts

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd website
npm install
```

### Environment Setup

Create `.env.local` file in the `website/` directory:

```bash
cd website
cat > .env.local << EOF
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# AWS Cognito Configuration
NEXT_PUBLIC_COGNITO_USER_POOL_ID=ap-southeast-1_xxxxxxxxx
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_COGNITO_REGION=ap-southeast-1
EOF
```

**Development (WSL):**
- `NEXT_PUBLIC_API_URL`: `http://localhost:8000`
- Use development Cognito credentials

**Production (AWS):**
- `NEXT_PUBLIC_API_URL`: `https://api.stratcon.ph`
- Use production Cognito credentials
- Set in AWS Amplify Console → Environment variables

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
website/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home (redirects to login)
│   ├── login/
│   │   └── page.tsx        # Login page
│   └── reports/
│       └── page.tsx        # Report generation form
├── components/
│   └── Logo.tsx            # Stratcon logo component
├── lib/
│   ├── api-client.ts       # FastAPI client
│   ├── amplify-config.ts   # AWS Cognito config
│   └── theme.ts            # Brand theme
└── public/
    └── logos/              # Stratcon logos
```

## Next Steps

1. **Configure AWS Cognito**
   - Create Cognito User Pool
   - Set up OAuth redirect URLs
   - Add credentials to `.env.local`

2. **Deploy**
   - Deploy to AWS Amplify, Vercel, or preferred platform
   - Update API URL for production

## Tech Stack

- **Next.js 16**: React framework with App Router
- **TypeScript**: Type safety
- **Tailwind CSS v4**: Styling
- **AWS Amplify Auth**: Authentication (Cognito)
- **Axios**: HTTP client
- **date-fns**: Date formatting
