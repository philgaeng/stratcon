# Mock Authentication Guide

## Overview

The application now supports a **mock authentication mode** that bypasses AWS Cognito entirely. This is useful for:
- Local development without AWS setup
- Demos that don't require real authentication
- Testing the application flow without Cognito configuration

## How to Enable Mock Auth

1. Create or edit `website/.env.local`:
```bash
NEXT_PUBLIC_BYPASS_AUTH=true
```

2. Restart your Next.js development server:
```bash
npm run dev
```

## How It Works

When `NEXT_PUBLIC_BYPASS_AUTH=true`:
- The app uses `MockAuthProvider` instead of `OidcProvider`
- Login automatically authenticates with a mock user
- No AWS Cognito calls are made
- User info is stored in `sessionStorage`

## Mock User Details

- **Email**: `philippe@stratcon.ph`
- **Name**: `Demo User`
- **User ID**: `mock-user-123`

## Switching Back to Real Cognito

Simply remove or set `NEXT_PUBLIC_BYPASS_AUTH=false` in your `.env.local`:
```bash
NEXT_PUBLIC_BYPASS_AUTH=false
# or just remove the line
```

Then restart your development server.

## Notes

- Mock auth state persists in `sessionStorage` (cleared when browser closes)
- Other pages that use `useAuth` from `react-oidc-context` directly may need to be updated to use `useAuthCompat` for full compatibility
- The login page and main app flow work with both mock and real auth

