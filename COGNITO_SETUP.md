# Cognito Authentication Setup

## Current Configuration

- **User Pool ID:** `ap-southeast-1_HtVo9Y0BB`
- **Region:** `ap-southeast-1`
- **Client ID:** `384id7i8oh9vci2ck2afip4vsn`
- **Domain:** `ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com`

## Required Setup

### 1. Enable Hosted UI

**Location:** AWS Cognito Console → User Pool → **App integration** → **App clients and analytics** → Click app client → **Hosted UI** → **Edit**

**Status:** Should show as "Available" (not "Unavailable")

If unavailable:
- Ensure callback URLs are configured (see below)
- Ensure OAuth scopes are configured (see below)
- Save changes and wait a few seconds

### 2. Configure Callback URLs

**Callback URLs** (add all environments):
```
http://localhost:3000/login
https://52.221.59.184/login
https://stratcon.facets-ai.com/login
```

**Sign-out URLs** (add all environments):
```
http://localhost:3000/login
https://52.221.59.184/login
https://stratcon.facets-ai.com/login
```

### 3. Configure OAuth Settings

**OAuth grant types:**
- ✅ Authorization code grant

**OpenID Connect scopes:**
- ✅ `email`
- ✅ `openid`
- ✅ `profile`

**Custom scopes:** (none required)

### 4. User Groups (Optional but Recommended)

Create these groups in Cognito Console → **Users and groups** → **Groups**:

- `super_admin` - Full system access
- `client_admin` - Manage assigned clients
- `client_manager` - View/manage assigned clients
- `viewer` - Read-only access
- `tenant_user` - Tenant-specific access

## How It Works

1. User visits `/login` page
2. Page automatically redirects to Cognito Hosted UI (`/login` endpoint)
3. User signs in on Cognito's managed login page
4. Cognito redirects back to `/login` with authorization code
5. App exchanges code for tokens and redirects to `/reports`

## Testing

**Local Development:**
```bash
cd website && npm run dev
# Visit http://localhost:3000
# Should redirect to Cognito Hosted UI
```

**Production:**
- Visit `https://stratcon.facets-ai.com`
- Should redirect to Cognito Hosted UI
- After login, redirects back to production URL

## Troubleshooting

**"Status: Unavailable" in Hosted UI:**
- Verify callback URLs are configured
- Verify OAuth scopes include `openid` and `email`
- Save changes and wait 10-30 seconds for propagation

**"Invalid redirect URI" error:**
- Check callback URLs match exactly (including `/login` at the end)
- Verify URLs are added in App Client settings
- Clear browser cache and try again

**Still redirecting to wrong URL:**
- Check browser console for errors
- Verify environment variables are set correctly
- Ensure Cognito domain is active

