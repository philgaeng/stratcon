"use client";

import React from "react";
import { AuthProvider } from "react-oidc-context";

type OidcProviderProps = {
  children: React.ReactNode;
};

// Cognito configuration - simplified for localhost development
// Revert to simple configuration that works with localhost
const cognitoIssuer =
  process.env.NEXT_PUBLIC_COGNITO_ISSUER ||
  "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_HtVo9Y0BB";
const clientId =
  process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "384id7i8oh9vci2ck2afip4vsn";

// Simple redirect URI - default to localhost for local development
const getRedirectUri = (): string => {
  // 1. Explicit environment variable (highest priority)
  if (process.env.NEXT_PUBLIC_REDIRECT_URI) {
    return process.env.NEXT_PUBLIC_REDIRECT_URI;
  }
  
  // 2. Auto-detect from browser (for production)
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    // If accessing from localhost, use localhost
    if (origin.includes('localhost') || origin.includes('127.0.0.1')) {
      return "http://localhost:3000/login";
    }
    // Otherwise use the detected origin
    return `${origin}/login`;
  }
  
  // 3. Default to localhost for SSR/local development
  return "http://localhost:3000/login";
};

const cognitoAuthConfig = {
  // Use the Cognito issuer URL for OIDC discovery
  authority: cognitoIssuer,
  client_id: clientId,
  redirect_uri: getRedirectUri(),
  response_type: "code" as const,
  scope: "openid email profile",
  automaticSilentRenew: true,
  loadUserInfo: true,
};

export default function OidcProvider({ children }: OidcProviderProps) {
  if (typeof window !== 'undefined') {
    console.log('[OIDC] Config:', {
      redirect_uri: cognitoAuthConfig.redirect_uri,
      authority: cognitoIssuer,
    });
  }
  
  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>;
}
