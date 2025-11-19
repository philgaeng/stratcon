"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { CognitoUser, CognitoAuthState } from "./cognito-auth";
import {
  getAuthorizationUrl,
  handleCallback,
  getCurrentUser,
  isAuthenticated,
  signOut as cognitoSignOut,
} from "./cognito-auth";

interface CognitoAuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: CognitoUser | null;
  error: string | null;
  signinRedirect: () => void;
  signoutRedirect: () => void;
}

const CognitoAuthContext = createContext<CognitoAuthContextType | undefined>(undefined);

export function useCognitoAuth() {
  const context = useContext(CognitoAuthContext);
  if (!context) {
    throw new Error("useCognitoAuth must be used within CognitoAuthProvider");
  }
  return context;
}

interface CognitoAuthProviderProps {
  children: React.ReactNode;
}

function CognitoAuthProviderInner({ children }: CognitoAuthProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<CognitoAuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    error: null,
  });

  // Check for callback (code and state in URL)
  useEffect(() => {
    const code = searchParams.get("code");
    const stateParam = searchParams.get("state");
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (error) {
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: errorDescription || error,
      });
      return;
    }

    if (code && stateParam) {
      // Handle OAuth callback
      setState((prev) => ({ ...prev, isLoading: true }));
      
      handleCallback(code, stateParam)
        .then((user) => {
          setState({
            isAuthenticated: true,
            isLoading: false,
            user,
            error: null,
          });
          // Clear URL parameters
          router.replace("/login");
          // Redirect to reports after a brief delay
          setTimeout(() => {
            router.push("/reports");
          }, 100);
        })
        .catch((err) => {
          console.error("[CognitoAuth] Callback error:", err);
          setState({
            isAuthenticated: false,
            isLoading: false,
            user: null,
            error: err.message || "Authentication failed",
          });
        });
      return;
    }

    // Not a callback - check existing auth state
    const checkAuth = () => {
      const authenticated = isAuthenticated();
      const user = authenticated ? getCurrentUser() : null;
      
      setState({
        isAuthenticated: authenticated,
        isLoading: false,
        user,
        error: null,
      });
    };

    checkAuth();
  }, [searchParams, router]);

  const signinRedirect = useCallback(() => {
    const authUrl = getAuthorizationUrl();
    console.log("[CognitoAuth] Redirecting to:", authUrl);
    window.location.href = authUrl;
  }, []);

  const signoutRedirect = useCallback(() => {
    cognitoSignOut();
  }, []);

  const value: CognitoAuthContextType = {
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    user: state.user,
    error: state.error,
    signinRedirect,
    signoutRedirect,
  };

  return (
    <CognitoAuthContext.Provider value={value}>
      {children}
    </CognitoAuthContext.Provider>
  );
}

export function CognitoAuthProvider({ children }: CognitoAuthProviderProps) {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CognitoAuthProviderInner>{children}</CognitoAuthProviderInner>
    </Suspense>
  );
}

