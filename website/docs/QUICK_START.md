# Quick Start Checklist

## Immediate Next Steps

### Step 1: Backend Extensions (Priority)
- [ ] Add `GET /clients` endpoint to list all clients
- [ ] Update `POST /reports/tenant` to accept:
  - `month`: string (YYYY-MM format)
  - `cutoff_date`: string (YYYY-MM-DD)
  - `cutoff_time`: string (HH:mm)
- [ ] Create `backend/services/email_service.py` with AWS SES integration
- [ ] Update report generation to use cutoff datetime and email results

### Step 2: Initialize Next.js
```bash
cd /home/philg/projects/stratcon/website
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
```

### Step 3: Install Dependencies
```bash
npm install @aws-amplify/auth @aws-amplify/core @aws-amplify/ui-react
npm install axios date-fns
```

### Step 4: Setup AWS Cognito
- [ ] Create Cognito User Pool
- [ ] Create User Pool Client
- [ ] Configure hosted UI
- [ ] Get credentials for `.env.local`

### Step 5: Create Theme System
- [ ] Create `lib/theme.ts` with Stratcon colors/fonts
- [ ] Configure `tailwind.config.ts`
- [ ] Setup Google Fonts in `app/layout.tsx`

### Step 6: Build Pages
- [ ] Login page (`app/login/page.tsx`)
- [ ] Reports page (`app/reports/page.tsx`)
- [ ] Selector components

### Step 7: Connect Everything
- [ ] API client with JWT auth
- [ ] Form submission
- [ ] Error handling
- [ ] Success states

---

## File Structure Overview

```
website/
├── app/
│   ├── layout.tsx          # Root + Amplify setup
│   ├── login/page.tsx      # Login page
│   └── reports/page.tsx    # Main report form
├── components/              # Reusable components
├── lib/
│   ├── amplify-config.ts   # Cognito config
│   ├── api-client.ts       # FastAPI wrapper
│   └── theme.ts            # Brand colors/fonts
└── public/logos/           # Stratcon logos
```

---

## Environment Variables Needed

Create `website/.env.local`:
```
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_xxxxx
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxx
NEXT_PUBLIC_COGNITO_DOMAIN=xxxxx.auth.region.amazoncognito.com
NEXT_PUBLIC_REDIRECT_SIGN_IN=http://localhost:3000/reports
NEXT_PUBLIC_REDIRECT_SIGN_OUT=http://localhost:3000/login
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Key Colors (from config.py)

- Primary Green: `#4CAF50`
- Dark Green: `#2E7D32`
- Consumption: `#f5b041` (orange)
- Dark Grey: `#2c3e50`

## Fonts

- Headings: Montserrat (700, 600, 400)
- Body: Inter (400, 600, 700)

