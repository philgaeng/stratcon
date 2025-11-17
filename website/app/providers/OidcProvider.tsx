"use client";

import React from "react";
import { AuthProvider } from "react-oidc-context";

type OidcProviderProps = {
  children: React.ReactNode;
};

// Cognito configuration - use issuer URL for OIDC discovery
// The library will discover endpoints from the issuer
// Use the issuer URL (not domain) for proper OIDC discovery
// The issuer URL points to the correct metadata endpoint
const cognitoIssuer =
  process.env.NEXT_PUBLIC_COGNITO_ISSUER ||
  "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_HtVo9Y0BB";
const clientId =
  process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "384id7i8oh9vci2ck2afip4vsn";

// Get redirect URI - automatically detects environment
// Priority: 1) Environment variable, 2) Auto-detect from browser, 3) Default to localhost
const getRedirectUri = (): string => {
  // 1. Explicit environment variable (highest priority)
  if (process.env.NEXT_PUBLIC_REDIRECT_URI) {
    const uri = process.env.NEXT_PUBLIC_REDIRECT_URI;
    if (typeof window !== 'undefined') {
      console.log('[OIDC] Using redirect URI from env:', uri);
    }
    return uri;
  }
  
  // 2. Auto-detect from browser (works in both dev and prod)
  if (typeof window !== 'undefined') {
    const uri = `${window.location.origin}/login`;
    console.log('[OIDC] Auto-detected redirect URI:', uri, '(from:', window.location.origin, ')');
    return uri;
  }
  
  // 3. Server-side default (fallback to localhost for SSR)
  return "http://localhost:3000/login";
};

// Base config - redirect_uri will be set dynamically in the component
const getBaseConfig = () => ({
  // Use the Cognito issuer URL for OIDC discovery
  // This allows the library to discover authorization/token endpoints
  authority: cognitoIssuer,
  client_id: clientId,
  response_type: "code" as const,
  scope: "openid email profile", // Include profile scope (matches Cognito allowed scopes)
  // Enable automatic silent signin to handle callbacks
  automaticSilentRenew: true,
  // Additional settings for better state management
  loadUserInfo: true,
  // PKCE is enabled by default in react-oidc-context for security
  // Use sessionStorage for state (more reliable across redirects)
  // The library will automatically handle callback processing
});

export default function OidcProvider({ children }: OidcProviderProps) {
  // Compute redirect_uri at component render time (not module load time)
  // This ensures we get the correct value based on the actual browser location
  const redirectUri = getRedirectUri();
  
  const cognitoAuthConfig = {
    ...getBaseConfig(),
    redirect_uri: redirectUri,
  };
  
  if (typeof window !== 'undefined') {
    console.log('[OIDC] Final config redirect_uri:', redirectUri);
  }
  
  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>;
}
