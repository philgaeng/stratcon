/**
 * Custom Cognito Authentication Implementation
 * 
 * This provides a clean, custom implementation of AWS Cognito OAuth2 flow
 * without relying on react-oidc-context's metadata discovery which finds /login endpoint.
 * 
 * Uses the standard OAuth2 authorization code flow with /oauth2/authorize endpoint.
 */

export interface CognitoUser {
  sub: string;
  email: string;
  email_verified: boolean;
  name?: string;
}

export interface CognitoAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: CognitoUser | null;
  error: string | null;
}

// Cognito configuration
const COGNITO_DOMAIN = "ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "384id7i8oh9vci2ck2afip4vsn";
const REDIRECT_URI = typeof window !== "undefined" 
  ? `${window.location.origin}/login`
  : "http://localhost:3000/login";

// Storage keys
const STATE_KEY = "cognito_oauth_state";
const TOKEN_KEY = "cognito_access_token";
const ID_TOKEN_KEY = "cognito_id_token";
const USER_KEY = "cognito_user";

/**
 * Generate a random state for OAuth2 flow
 */
function generateState(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

/**
 * Get the authorization URL for Cognito OAuth2
 */
export function getAuthorizationUrl(): string {
  const state = generateState();
  
  // Store state in sessionStorage for validation on callback
  if (typeof window !== "undefined") {
    sessionStorage.setItem(STATE_KEY, state);
  }
  
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    scope: "openid email",
    redirect_uri: REDIRECT_URI,
    state: state,
  });
  
  return `https://${COGNITO_DOMAIN}/oauth2/authorize?${params.toString()}`;
}

/**
 * Exchange authorization code for tokens
 */
async function exchangeCodeForTokens(code: string): Promise<{
  access_token: string;
  id_token: string;
  token_type: string;
  expires_in: number;
}> {
  const tokenEndpoint = `https://${COGNITO_DOMAIN}/oauth2/token`;
  
  const response = await fetch(tokenEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code: code,
      redirect_uri: REDIRECT_URI,
    }),
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Token exchange failed: ${error}`);
  }
  
  return await response.json();
}

/**
 * Get user info from ID token or userinfo endpoint
 */
async function getUserInfo(accessToken: string): Promise<CognitoUser> {
  // Decode ID token (JWT) to get user info
  const idToken = localStorage.getItem(ID_TOKEN_KEY);
  if (idToken) {
    try {
      // Decode JWT (base64url decode the payload)
      const payload = idToken.split(".")[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
      
      return {
        sub: decoded.sub,
        email: decoded.email,
        email_verified: decoded.email_verified === "true" || decoded.email_verified === true,
        name: decoded.name,
      };
    } catch (e) {
      console.warn("Failed to decode ID token, using userinfo endpoint", e);
    }
  }
  
  // Fallback to userinfo endpoint
  const userinfoEndpoint = `https://${COGNITO_DOMAIN}/oauth2/userInfo`;
  const response = await fetch(userinfoEndpoint, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error("Failed to get user info");
  }
  
  return await response.json();
}

/**
 * Handle OAuth2 callback - exchange code for tokens
 */
export async function handleCallback(code: string, state: string): Promise<CognitoUser> {
  // Validate state
  const storedState = sessionStorage.getItem(STATE_KEY);
  if (!storedState || storedState !== state) {
    throw new Error("Invalid state parameter");
  }
  
  // Clear state
  sessionStorage.removeItem(STATE_KEY);
  
  // Exchange code for tokens
  const tokens = await exchangeCodeForTokens(code);
  
  // Store tokens
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(ID_TOKEN_KEY, tokens.id_token);
  
  // Get user info
  const user = await getUserInfo(tokens.access_token);
  
  // Store user
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  
  return user;
}

/**
 * Get current user from storage
 */
export function getCurrentUser(): CognitoUser | null {
  if (typeof window === "undefined") return null;
  
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  
  const accessToken = localStorage.getItem(TOKEN_KEY);
  const user = getCurrentUser();
  
  return !!(accessToken && user);
}

/**
 * Sign out - clear all stored data
 */
export function signOut(): void {
  if (typeof window === "undefined") return;
  
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ID_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  
  // Redirect to Cognito logout
  const logoutUrl = `https://${COGNITO_DOMAIN}/logout?` +
    `client_id=${CLIENT_ID}&` +
    `logout_uri=${encodeURIComponent(REDIRECT_URI)}`;
  
  window.location.href = logoutUrl;
}

/**
 * Get access token for API calls
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

