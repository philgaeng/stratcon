"use client";

import { useMockAuth } from "@/app/providers/MockAuthProvider";

/**
 * Auth hook - Currently using mock auth for demo
 * 
 * TODO: Make this conditional after demo to support both mock and real Cognito
 */
export function useAuthCompat() {
  // Force mock auth for demo
  return useMockAuth();
}

