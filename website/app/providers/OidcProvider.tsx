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

const cognitoAuthConfig = {
  // Use the Cognito issuer URL for OIDC discovery
  // This allows the library to discover authorization/token endpoints
  authority: cognitoIssuer,
  client_id: clientId,
  redirect_uri: "http://localhost:3000/login",
  response_type: "code",
  scope: "openid email",
  // Enable automatic silent signin to handle callbacks
  automaticSilentRenew: true,
  // Additional settings for better state management
  loadUserInfo: true,
  // Use sessionStorage for state (more reliable across redirects)
  // The library will automatically handle callback processing
};

export default function OidcProvider({ children }: OidcProviderProps) {
  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>;
}
