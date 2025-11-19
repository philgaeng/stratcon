"use client";

import React from "react";
import OidcProvider from "./OidcProvider";
import MockAuthProvider from "./MockAuthProvider";

type AuthProviderWrapperProps = {
  children: React.ReactNode;
};

/**
 * Auth Provider - Uses Cognito by default, falls back to Mock Auth if bypass is enabled
 * 
 * To use mock auth: Set NEXT_PUBLIC_BYPASS_AUTH=true in environment variables
 */
export default function AuthProviderWrapper({ children }: AuthProviderWrapperProps) {
  // Check if mock auth is enabled via environment variable
  const useMockAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";
  
  if (useMockAuth) {
    console.log("[AUTH] Using mock authentication (bypass enabled)");
    return <MockAuthProvider>{children}</MockAuthProvider>;
  }
  
  console.log("[AUTH] Using Cognito authentication");
  return <OidcProvider>{children}</OidcProvider>;
}

