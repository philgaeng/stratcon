"use client";

/**
 * Unified auth hook that works with both real Cognito and mock auth
 * 
 * This hook tries to use the appropriate auth provider based on which one
 * is actually rendered in the component tree (via AuthProviderWrapper)
 */
export function useAuthCompat() {
  const bypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === "true";

  if (bypassAuth) {
    // Use mock auth when bypass is enabled
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { useMockAuth } = require("@/app/providers/MockAuthProvider");
    return useMockAuth();
  } else {
    // Use real Cognito auth
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { useAuth } = require("react-oidc-context");
    const oidcAuth = useAuth();
    return {
      isAuthenticated: oidcAuth.isAuthenticated,
      isLoading: oidcAuth.isLoading,
      user: oidcAuth.user,
      error: oidcAuth.error,
      signinRedirect: oidcAuth.signinRedirect,
      signoutRedirect: oidcAuth.signoutRedirect,
    };
  }
}

