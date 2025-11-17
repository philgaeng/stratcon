"use client";

import React from "react";
import { AuthProvider } from "react-oidc-context";

type OidcProviderProps = {
  children: React.ReactNode;
};

// Cognito configuration - use issuer URL for OIDC discovery
// The library will discover endpoints from the issuer
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
    return process.env.NEXT_PUBLIC_REDIRECT_URI;
  }
  
  // 2. Auto-detect from browser (works in both dev and prod)
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/login`;
  }
  
  // 3. Server-side default (fallback to localhost for SSR)
  return "http://localhost:3000/login";
};

const cognitoAuthConfig = {
  // Use the Cognito issuer URL for OIDC discovery
  // This allows the library to discover authorization/token endpoints
  authority: cognitoIssuer,
  client_id: clientId,
  redirect_uri: getRedirectUri(),
  response_type: "code",
  scope: "openid email profile", // Include profile scope (matches Cognito allowed scopes)
  // Enable automatic silent signin to handle callbacks
  automaticSilentRenew: true,
  // Additional settings for better state management
  loadUserInfo: true,
  // PKCE is enabled by default in react-oidc-context for security
  // Use sessionStorage for state (more reliable across redirects)
  // The library will automatically handle callback processing
};

export default function OidcProvider({ children }: OidcProviderProps) {
  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>;
}
