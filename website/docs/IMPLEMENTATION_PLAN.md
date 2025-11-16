# Next.js Website Implementation Plan

## Overview
Build a simple Next.js website with AWS Cognito authentication for generating electricity consumption reports. The website will allow authenticated users to select a client, tenant, month, and cutoff date/time to generate reports that are emailed directly.

## Architecture

### Tech Stack
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS
- **Authentication**: AWS Amplify Auth (Cognito)
- **Backend**: FastAPI (existing)
- **Email**: AWS SES (Simple Email Service)
- **Styling**: Tailwind CSS with custom theme matching Stratcon brand

---

## Phase 1: Backend API Extensions

### 1.1 Add Client Listing Endpoint
**File**: `backend/api.py`
- Add `GET /clients` endpoint
- Return list of client folders from `downloads/` directory
- Response: `{ "clients": ["NEO", "CLIENT2", ...], "count": 2 }`

### 1.2 Extend Report Generation Endpoint
**File**: `backend/api.py`
- Modify `POST /reports/tenant` to accept:
  - `month`: string (format: "YYYY-MM" or "YYYY-MM-DD")
  - `cutoff_date`: string (format: "YYYY-MM-DD")
  - `cutoff_time`: string (format: "HH:mm" or "HH:MM:SS")
- Combine cutoff_date + cutoff_time into cutoff_datetime for report generation
- Update `TenantReportRequest` model

### 1.3 Add Email Service
**File**: `backend/services/email_service.py` (new)
- Create email sending service using AWS SES (boto3)
- Function: `send_report_email(email: str, report_path: str, client_name: str, tenant_name: str)`
- Email should include:
  - Subject: "Electricity Report - {Client} - {Tenant} - {Month}"
  - Body: HTML email with report attached or linked
- Integrate with existing report generation flow

### 1.4 Update Report Generation Flow
**File**: `backend/services/report_generation.py`
- Modify `generate_reports_for_tenant()` to:
  - Accept month filter
  - Accept cutoff datetime (date + time)
  - Generate report for specific month
  - After generation, call email service
  - Return report path for email attachment

---

## Phase 2: Frontend Setup

### 2.1 Initialize Next.js Project
**Location**: `website/`
**Commands**:
```bash
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
npm install @aws-amplify/auth @aws-amplify/core @aws-amplify/ui-react
npm install axios date-fns
```

### 2.2 Project Structure
```
website/
├── app/
│   ├── layout.tsx          # Root layout with Amplify provider
│   ├── page.tsx             # Redirect to login or dashboard
│   ├── login/
│   │   └── page.tsx         # Login page (Cognito hosted UI)
│   └── reports/
│       └── page.tsx         # Report generation form
├── components/
│   ├── ClientSelector.tsx
│   ├── TenantSelector.tsx
│   ├── MonthSelector.tsx
│   ├── CutoffDateTimeSelector.tsx
│   └── Logo.tsx
├── lib/
│   ├── amplify-config.ts    # Amplify configuration
│   ├── api-client.ts        # FastAPI client wrapper
│   └── theme.ts             # Theme matching config.py
├── styles/
│   └── globals.css          # Global styles + Tailwind
└── public/
    └── logos/               # Copy Stratcon logos here
```

---

## Phase 3: Brand Theme Setup

### 3.1 Create Theme Configuration
**File**: `website/lib/theme.ts`
Extract from `backend/services/config.py`:
- Colors: CONSUMPTION_COLOR, PRODUCTION_COLOR, STRATCON_DARK_GREEN, etc.
- Fonts: Montserrat (headings), Inter (body)
- Font sizes: H1, H2, H3, body

### 3.2 Configure Tailwind CSS
**File**: `website/tailwind.config.ts`
- Extend theme with Stratcon colors
- Add custom fonts (Montserrat, Inter from Google Fonts)
- Configure typography plugin

### 3.3 Global Styles
**File**: `website/styles/globals.css`
- Import Google Fonts (Montserrat, Inter)
- Define CSS variables for colors
- Base styles matching report styling

### 3.4 Copy Logo Assets
- Copy PNG logos from `resources/logos/` to `website/public/logos/`
- Create `Logo` component to display logos

---

## Phase 4: AWS Cognito Setup

### 4.1 AWS Cognito Configuration
**Prerequisites**: AWS account, AWS CLI configured
**Steps**:
1. Create Cognito User Pool (or use existing)
2. Create User Pool Client
3. Configure hosted UI settings
4. Set redirect URLs (localhost for dev, production URL for prod)

### 4.2 Amplify Configuration
**File**: `website/lib/amplify-config.ts`
```typescript
export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
      loginWith: {
        oauth: {
          domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
          scopes: ['email', 'openid', 'profile'],
          redirectSignIn: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_IN],
          redirectSignOut: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_OUT],
          responseType: 'code'
        },
        username: 'false',
        email: 'true'
      }
    }
  }
}
```

### 4.3 Environment Variables
**File**: `website/.env.local` (not committed)
```
NEXT_PUBLIC_COGNITO_USER_POOL_ID=...
NEXT_PUBLIC_COGNITO_CLIENT_ID=...
NEXT_PUBLIC_COGNITO_DOMAIN=...
NEXT_PUBLIC_REDIRECT_SIGN_IN=http://localhost:3000/reports
NEXT_PUBLIC_REDIRECT_SIGN_OUT=http://localhost:3000/login
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Phase 5: Authentication Pages

### 5.1 Root Layout
**File**: `website/app/layout.tsx`
- Wrap app with Amplify `Authenticator` provider
- Include global styles
- Setup font imports (Montserrat, Inter)

### 5.2 Login Page
**File**: `website/app/login/page.tsx`
- Use Cognito hosted UI for sign-in
- Redirect to `/reports` on successful login
- Show Stratcon logo and branding
- Use Stratcon green colors for buttons

### 5.3 Protected Route Middleware
**File**: `website/middleware.ts`
- Protect `/reports` route
- Redirect to `/login` if not authenticated
- Verify Cognito JWT token

---

## Phase 6: Report Generation Page

### 6.1 API Client
**File**: `website/lib/api-client.ts`
- Create axios instance with base URL
- Add request interceptors for Cognito JWT tokens
- Functions:
  - `getClients()`: GET /clients
  - `getTenants(clientToken)`: GET /tenants?client_token=...
  - `generateReport(params)`: POST /reports/tenant

### 6.2 Selector Components
**Components**:
- `ClientSelector.tsx`: Dropdown/select for client selection
- `TenantSelector.tsx`: Dropdown that loads when client selected
- `MonthSelector.tsx`: Month/year picker
- `CutoffDateTimeSelector.tsx`: Date picker + time picker

### 6.3 Report Generation Page
**File**: `website/app/reports/page.tsx`
- Form layout with all selectors
- Form validation
- Submit button with loading state
- Success message: "Report generation started. You will receive an email when ready."
- Error handling with user-friendly messages
- Use Stratcon styling (green buttons, Montserrat/Inter fonts)

---

## Phase 7: Integration & Testing

### 7.1 Connect Frontend to Backend
- Test API endpoints with Postman/curl
- Verify CORS settings in FastAPI
- Test authentication flow end-to-end
- Test form submission with real data

### 7.2 Error Handling
- Network errors
- Authentication errors
- API validation errors
- Display user-friendly error messages

### 7.3 Loading States
- Show loading spinner during API calls
- Disable form during submission
- Optimistic UI updates

---

## Phase 8: Email Integration

### 8.1 AWS SES Setup
**Prerequisites**:
- Verify email addresses/domain in SES
- Request production access if needed
- Configure IAM roles for SES access

### 8.2 Email Service Implementation
- Send HTML email with report attached
- Include branding (Stratcon logo in email)
- Handle email sending errors gracefully

---

## Phase 9: Deployment Preparation

### 9.1 Environment Configuration
- Separate configs for dev/staging/prod
- Environment variables for all AWS resources
- API URLs for different environments

### 9.2 Build & Deployment
- Next.js build process
- Static export or server-side rendering?
- AWS Amplify Hosting or Vercel deployment
- FastAPI deployment (ECS, Lambda, EC2, or Elastic Beanstalk)

---

## Phase 10: Polish & Documentation

### 10.1 UX Improvements
- Loading skeletons
- Success animations
- Error toast notifications
- Responsive design (mobile-friendly)

### 10.2 Documentation
- README for website folder
- Setup instructions
- AWS Cognito configuration guide
- Environment variables documentation

---

## Implementation Order

1. ✅ **Backend API Extensions** (Phase 1)
2. ✅ **Frontend Setup** (Phase 2)
3. ✅ **Theme Setup** (Phase 3)
4. ✅ **Cognito Setup** (Phase 4) - Can be done in parallel with frontend
5. ✅ **Auth Pages** (Phase 5)
6. ✅ **Report Page** (Phase 6)
7. ✅ **Integration** (Phase 7)
8. ✅ **Email Service** (Phase 8)
9. ✅ **Deployment** (Phase 9)
10. ✅ **Polish** (Phase 10)

---

## Key Design Decisions

1. **Month Selection**: Allow users to select month from available data months (could add API endpoint to get available months per tenant)
2. **Cutoff Date/Time**: Separate date and time inputs for better UX
3. **Email Delivery**: Send report as attachment (PDF conversion?) or link to S3-hosted HTML report
4. **User Groups**: Use Cognito groups to map users to clients (future enhancement)
5. **Error Recovery**: Allow users to retry failed report generation

---

## Estimated Timeline

- **Phase 1-2**: 4-6 hours (Backend API + Frontend setup)
- **Phase 3-4**: 2-3 hours (Theme + Cognito)
- **Phase 5-6**: 6-8 hours (Auth + Report page)
- **Phase 7-8**: 4-6 hours (Integration + Email)
- **Phase 9-10**: 3-4 hours (Deployment + Polish)

**Total**: ~20-27 hours of focused development

---

## Notes

- Reuse existing `ReportStyle` colors and fonts for consistency
- Keep website simple - no need for complex state management (use React Query if needed)
- Follow existing backend patterns for logging (use `db_manager.log`)
- Test with real data before deployment
- Consider adding API endpoint to list available months for a tenant (for validation)

