"use client";

import React, { useMemo } from "react";
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

// Use OAuth2 authorization endpoint directly instead of Hosted UI /login
// This avoids PKCE issues with the Hosted UI endpoint
const cognitoDomain = "ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com";
const authorizationEndpoint = `https://${cognitoDomain}/oauth2/authorize`;
const tokenEndpoint = `https://${cognitoDomain}/oauth2/token`;

export default function OidcProvider({ children }: OidcProviderProps) {
  // Determine redirect URI based on environment (computed on client-side)
  const redirectUri = useMemo(() => {
    if (typeof window !== "undefined") {
      // Client-side: use current origin
      return `${window.location.origin}/login`;
    }
    // Server-side: use environment variable or default to localhost
    return (
      process.env.NEXT_PUBLIC_REDIRECT_URI ||
      (process.env.NEXT_PUBLIC_API_URL?.replace("/api", "") + "/login") ||
      "http://localhost:3000/login"
    );
  }, []);

  const cognitoAuthConfig = useMemo(
    () => ({
      // Use the Cognito issuer URL for OIDC discovery
      authority: cognitoIssuer,
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: "code" as const,
      scope: "openid email",
      // Enable automatic silent signin to handle callbacks
      automaticSilentRenew: true,
      // Additional settings for better state management
      loadUserInfo: true,
      // Override metadata to use OAuth2 endpoints directly (not Hosted UI /login)
      metadata: {
        authorization_endpoint: authorizationEndpoint,
        token_endpoint: tokenEndpoint,
        // Disable PKCE by not including code_challenge_method in metadata
      },
      // Explicitly disable PKCE
      code_challenge_method: undefined,
    }),
    [redirectUri]
  );

  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>;
}
