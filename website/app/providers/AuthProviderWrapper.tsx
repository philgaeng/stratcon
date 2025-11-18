"use client";

import React from "react";
import MockAuthProvider from "./MockAuthProvider";

type AuthProviderWrapperProps = {
  children: React.ReactNode;
};

/**
 * Auth Provider - Currently using Mock Auth for demo
 * 
 * TODO: Switch back to OidcProvider after demo
 * To use real Cognito: import OidcProvider and conditionally render based on env var
 */
export default function AuthProviderWrapper({ children }: AuthProviderWrapperProps) {
  // Force mock auth for demo
  console.log("[AUTH] Using mock authentication for demo");
  return <MockAuthProvider>{children}</MockAuthProvider>;
}

