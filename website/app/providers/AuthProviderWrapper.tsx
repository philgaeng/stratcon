"use client";

import React from "react";
import OidcProvider from "./OidcProvider";
import MockAuthProvider from "./MockAuthProvider";

type AuthProviderWrapperProps = {
  children: React.ReactNode;
};

/**
 * Conditional Auth Provider
 * 
 * Set NEXT_PUBLIC_BYPASS_AUTH=true in .env.local to use mock authentication
 * (useful for local development/demos without AWS Cognito)
 * 
 * Otherwise, uses real AWS Cognito via OidcProvider
 */
export default function AuthProviderWrapper({ children }: AuthProviderWrapperProps) {
  const bypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";

  if (bypassAuth) {
    console.log("[AUTH] Using mock authentication (BYPASS_AUTH=true)");
    return <MockAuthProvider>{children}</MockAuthProvider>;
  }

  return <OidcProvider>{children}</OidcProvider>;
}

