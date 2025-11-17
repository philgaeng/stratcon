# How to Update Cognito Redirect URIs

## Problem
Cognito is redirecting to `localhost:3000` instead of your AWS server URL. You need to add the production redirect URI to your Cognito App Client.

## Step-by-Step Instructions

### Step 1: Open AWS Cognito Console

1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Make sure you're in the correct region: **ap-southeast-1** (Singapore)
3. Search for "Cognito" in the search bar
4. Click on **"Amazon Cognito"**

### Step 2: Find Your User Pool

1. In the left sidebar, click **"User pools"**
2. You should see a user pool (likely named something like "stratcon" or similar)
3. **Click on the User Pool name** to open it

### Step 3: Navigate to App Client Settings

1. In the left sidebar, click **"App integration"**
2. Scroll down to the **"App clients and analytics"** section
3. You should see an app client listed (Client ID: `384id7i8oh9vci2ck2afip4vsn`)
4. **Click on the app client name** (not the Client ID)

### Step 4: Edit Hosted UI Settings

1. Scroll down to the **"Hosted UI"** section
2. Click **"Edit"** button (usually in the top right of the Hosted UI section)

### Step 5: Add Callback URLs

1. Find the **"Callback URL(s)"** field
2. You should see: `http://localhost:3000/login` (or similar)
3. **Add the production URL** by clicking **"Add another URL"** or editing the existing field
4. Add both URLs (separate them with commas or use multiple lines):
   ```
   http://localhost:3000/login
   https://52.221.59.184/login
   ```

### Step 6: Add Sign-out URLs (Optional but Recommended)

1. Find the **"Sign-out URL(s)"** field
2. Add both URLs:
   ```
   http://localhost:3000/login
   https://52.221.59.184/login
   ```

### Step 7: Save Changes

1. Scroll down and click **"Save changes"**
2. Wait for confirmation that changes are saved

## Alternative: Using AWS CLI

If you prefer command line, you can also update it via AWS CLI:

```bash
# Get your User Pool ID (from the Cognito console URL or list)
USER_POOL_ID="ap-southeast-1_HtVo9Y0BB"  # Replace with your actual User Pool ID
CLIENT_ID="384id7i8oh9vci2ck2afip4vsn"

# Update the app client
aws cognito-idp update-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-id "$CLIENT_ID" \
  --callback-urls "http://localhost:3000/login" "https://52.221.59.184/login" \
  --logout-urls "http://localhost:3000/login" "https://52.221.59.184/login" \
  --region ap-southeast-1
```

## Verify It's Working

After updating:

1. **Test on AWS:**
   - Go to `https://52.221.59.184` (accept the self-signed cert warning)
   - Click "Sign in"
   - After Cognito login, it should redirect back to `https://52.221.59.184/login` (not localhost)

2. **Test on localhost (should still work):**
   - Go to `http://localhost:3000`
   - Click "Sign in"
   - Should redirect back to `http://localhost:3000/login`

## Troubleshooting

### "Invalid redirect URI" Error
- Make sure both URLs are exactly as shown (with `/login` at the end)
- Check for typos (especially `https://` vs `http://`)
- Wait a few seconds after saving - Cognito changes can take a moment to propagate

### Still Redirecting to localhost
- Clear your browser cache
- Try in an incognito/private window
- Check browser console for errors
- Verify the frontend code was updated (should auto-detect from `window.location.origin`)

### Can't Find App Client
- Make sure you're in the correct User Pool
- Check the Client ID matches: `384id7i8oh9vci2ck2afip4vsn`
- Look in "App integration" → "App clients and analytics"

## Quick Reference

**Your Cognito Details:**
- **Region:** ap-southeast-1
- **User Pool ID:** ap-southeast-1_HtVo9Y0BB (check in console)
- **Client ID:** 384id7i8oh9vci2ck2afip4vsn
- **Callback URLs to add:**
  - `http://localhost:3000/login` (development)
  - `https://52.221.59.184/login` (production)

