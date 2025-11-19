# Cognito Setup Checklist

## Your Current Configuration

- **User Pool Name:** `stratcon-users`
- **User Pool ID:** `ap-southeast-1_HtVo9Y0BB`
- **Region:** `ap-southeast-1`
- **Client ID:** `384id7i8oh9vci2ck2afip4vsn`
- **Domain:** `ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com`

---

## ✅ Required Setup Steps

### 1. Verify User Groups (REQUIRED)

**Location:** Cognito Console → `stratcon-users` → **Users and groups** → **Groups**

You need these 5 groups (create any that are missing):

- ✅ `super_admin` - Full system access
- ✅ `client_admin` - Manage assigned clients
- ✅ `client_manager` - View/manage assigned clients (no user creation)
- ✅ `viewer` - Read-only access
- ✅ `tenant_user` - Tenant-specific access

**Action:** Check which groups exist, create any missing ones.

---

### 2. Configure App Client Redirect URIs (REQUIRED)

**Location:** Cognito Console → `stratcon-users` → **App integration** → **App clients and analytics** → Click on your app client → **Hosted UI** → **Edit**

**Callback URLs** (add both):
```
http://localhost:3000/login
https://stratcon.facets-ai.com/login
```

**Sign-out URLs** (add both):
```
http://localhost:3000/login
https://stratcon.facets-ai.com/login
```

**OAuth 2.0 grant types** (should include):
- ✅ Authorization code grant
- ✅ Implicit grant (if needed)

**OAuth 2.0 scopes** (should include):
- ✅ `openid`
- ✅ `email`
- ✅ `profile` (optional but recommended)

**Action:** Update redirect URIs to include production domain.

---

### 3. Verify Cognito Domain (REQUIRED)

**Location:** Cognito Console → `stratcon-users` → **App integration** → **Domain**

**Current Domain:** `ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com`

**Status:** Should show as "Active"

**Action:** Verify domain is active. If not, create/activate it.

---

### 4. App Client Settings (VERIFY)

**Location:** Cognito Console → `stratcon-users` → **App integration** → **App clients and analytics** → Click on your app client

**Settings to verify:**

- **Allowed OAuth flows:**
  - ✅ Authorization code grant
  - ✅ Implicit grant (optional)

- **Allowed OAuth scopes:**
  - ✅ `openid`
  - ✅ `email`
  - ✅ `profile` (optional)

- **Prevent user existence errors:** Should be enabled (recommended)

**Action:** Verify these settings match above.

---

### 5. Lambda Triggers (OPTIONAL but Recommended)

**Location:** Cognito Console → `stratcon-users` → **User pool properties** → **Lambda triggers**

#### PreSignUp Trigger (Domain Allowlist)
- **Purpose:** Only allow sign-ups from specific email domains
- **Lambda Function:** `stratcon-cognito-pre-signup` (create if doesn't exist)
- **Environment Variables:**
  - `ALLOWLIST_DOMAINS`: `stratcon.ph,neooffice.ph` (add your domains)

#### PostConfirmation Trigger (Auto-assign Group)
- **Purpose:** Automatically add new users to `viewer` group
- **Lambda Function:** `stratcon-cognito-post-confirmation` (create if doesn't exist)
- **Environment Variables:**
  - `USER_POOL_ID`: `ap-southeast-1_HtVo9Y0BB`
  - `DEFAULT_GROUP`: `viewer`

**Action:** Set up Lambda triggers if you want domain allowlisting and auto-group assignment.

**Note:** Lambda setup instructions are in `backend/lambdas/README.md`

---

## 🔍 Quick Verification

### Test Authentication Flow

1. **Local Development:**
   ```bash
   # Start frontend
   cd website && npm run dev
   # Visit http://localhost:3000
   # Click "Sign in" → Should redirect to Cognito
   # After login → Should redirect back to http://localhost:3000/login
   ```

2. **Production:**
   - Visit `https://stratcon.facets-ai.com`
   - Click "Sign in" → Should redirect to Cognito
   - After login → Should redirect back to `https://stratcon.facets-ai.com/login`

### Common Issues

**"Invalid redirect URI" error:**
- Check that both callback URLs are added in App Client settings
- Verify URLs match exactly (including `/login` at the end)
- Wait a few seconds after saving (Cognito changes can take time to propagate)

**User not in correct group:**
- Manually add user to group in Cognito Console
- Or set up PostConfirmation Lambda trigger to auto-assign

**Domain not allowed:**
- Check PreSignUp Lambda `ALLOWLIST_DOMAINS` environment variable
- Or disable PreSignUp trigger if you want to allow all domains

---

## 📝 Summary

**Minimum Required:**
1. ✅ All 5 user groups exist
2. ✅ App Client redirect URIs include production domain
3. ✅ Cognito domain is active

**Recommended:**
4. ✅ Lambda triggers for domain allowlist and auto-group assignment
5. ✅ OAuth scopes include `openid`, `email`, `profile`

---

## Next Steps After Setup

1. Test authentication locally
2. Deploy to production and test
3. Verify users can sign in and are assigned to correct groups
4. Test that backend receives correct user information from JWT tokens

