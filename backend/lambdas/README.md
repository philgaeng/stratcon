# Cognito Lambda Triggers

These Lambda functions are triggered by AWS Cognito to enforce domain allowlist and assign default roles.

## Setup Instructions

### Prerequisites

1. AWS Lambda service access
2. IAM role with permissions (see below)
3. Cognito User Pool created (`ap-southeast-1_HtVo9Y0BB`)

### Step 1: Create IAM Role for Lambdas

1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **Lambda**
3. Attach policies:
   - `AWSLambdaBasicExecutionRole` (for CloudWatch logs)
4. Add inline policy (replace with your account ID if different):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AddUserToGroup",
      "Effect": "Allow",
      "Action": ["cognito-idp:AdminAddUserToGroup"],
      "Resource": "arn:aws:cognito-idp:ap-southeast-1:149536467104:userpool/ap-southeast-1_HtVo9Y0BB"
    }
  ]
}
```

5. Name the role: `cognito-lambda-triggers-role`
6. Save

### Step 2: Create User Groups in Cognito

1. Go to **Cognito Console** → **stratcon-users** → **Users and groups** → **Groups**
2. Create these groups (one by one):
   - `viewer`
   - `tenant_user`
   - `client_manager`
   - `client_admin`
   - `super_admin`

### Step 3: Create PreSignUp Lambda

1. Go to **Lambda Console** → **Create function**
2. **Function name**: `stratcon-cognito-pre-signup`
3. **Runtime**: Python 3.12
4. **Architecture**: x86_64
5. **Execution role**: Use existing role → Select `cognito-lambda-triggers-role`
6. Click **Create function**

7. **Paste code**: Copy contents of `cognito_pre_signup.py` into the code editor

8. **Set environment variables**:

   - Key: `ALLOWLIST_DOMAINS`
   - Value: `stratcon.ph,neooffice.ph`

9. **Deploy** (click Deploy button)

### Step 4: Create PostConfirmation Lambda

1. Go to **Lambda Console** → **Create function**
2. **Function name**: `stratcon-cognito-post-confirmation`
3. **Runtime**: Python 3.12
4. **Architecture**: x86_64
5. **Execution role**: Use existing role → Select `cognito-lambda-triggers-role`
6. Click **Create function**

7. **Paste code**: Copy contents of `cognito_post_confirmation.py` into the code editor

8. **Set environment variables**:

   - Key: `USER_POOL_ID`
   - Value: `ap-southeast-1_HtVo9Y0BB`
   - Key: `DEFAULT_GROUP`
   - Value: `viewer`

9. **Deploy** (click Deploy button)

### Step 5: Wire Triggers to Cognito

1. Go to **Cognito Console** → **stratcon-users** → **User pool properties** → **Lambda triggers**

2. **Pre sign-up trigger**:

   - Select `stratcon-cognito-pre-signup`
   - Click **Save changes**

3. **Post confirmation trigger**:
   - Select `stratcon-cognito-post-confirmation`
   - Click **Save changes**

### Step 6: Test

1. Try signing up with an allowed email (e.g., `test@stratcon.ph`):

   - Should succeed and send verification email
   - After email verification, user should be in `viewer` group

2. Try signing up with a disallowed email (e.g., `test@gmail.com`):
   - Should be rejected with error message

## Environment Variables

### PreSignUp Lambda

- `ALLOWLIST_DOMAINS`: Comma-separated list of allowed email domains (e.g., `stratcon.ph,neooffice.ph`)

### PostConfirmation Lambda

- `USER_POOL_ID`: Cognito User Pool ID (e.g., `ap-southeast-1_HtVo9Y0BB`)
- `DEFAULT_GROUP`: Default group name (default: `viewer`)

## Updating Allowlist

To add/remove domains:

1. Go to Lambda Console → `stratcon-cognito-pre-signup`
2. **Configuration** → **Environment variables**
3. Edit `ALLOWLIST_DOMAINS` value
4. **Save** (no need to redeploy)

## Troubleshooting

### Lambda not triggering

- Check Lambda logs in CloudWatch
- Verify trigger is saved in Cognito
- Check IAM permissions

### User not added to group

- Check PostConfirmation Lambda logs
- Verify group exists in Cognito
- Check IAM permissions for `AdminAddUserToGroup`

### Domain allowlist not working

- Check PreSignUp Lambda logs
- Verify environment variable is set correctly
- Check email format (should be lowercase)
