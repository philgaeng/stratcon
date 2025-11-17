/**
 * AWS Amplify Configuration
 * 
 * Note: These values should be set via environment variables
 * Create a .env.local file with:
 * NEXT_PUBLIC_COGNITO_USER_POOL_ID=...
 * NEXT_PUBLIC_COGNITO_CLIENT_ID=...
 * NEXT_PUBLIC_COGNITO_DOMAIN=...
 * NEXT_PUBLIC_REDIRECT_SIGN_IN=http://localhost:3000/reports
 * NEXT_PUBLIC_REDIRECT_SIGN_OUT=http://localhost:3000/login
 */

export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
      loginWith: {
        oauth: {
          domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN || '',
          scopes: ['email', 'openid', 'profile'],
          redirectSignIn: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_IN || 'http://localhost:3000/reports'],
          redirectSignOut: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_OUT || 'http://localhost:3000/login'],
          responseType: 'code' as const,
        },
        username: 'false',
        email: 'true',
      },
    },
  },
};

// Check if required config is present
export const isAmplifyConfigured = (): boolean => {
  return !!(
    amplifyConfig.Auth.Cognito.userPoolId &&
    amplifyConfig.Auth.Cognito.userPoolClientId &&
    amplifyConfig.Auth.Cognito.loginWith.oauth.domain
  );
};

