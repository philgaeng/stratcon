"use client";

import { useAuth } from "react-oidc-context";
import { useMockAuth } from "@/app/providers/MockAuthProvider";

/**
 * Auth hook - Compatible with both Cognito and Mock Auth
 * 
 * Uses Cognito by default, falls back to Mock Auth if NEXT_PUBLIC_BYPASS_AUTH=true
 */
export function useAuthCompat() {
  // Check if mock auth is enabled via environment variable
  const useMockAuthMode = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";
  
  if (useMockAuthMode) {
    return useMockAuth();
  }
  
  // Use Cognito auth
  return useAuth();
}

