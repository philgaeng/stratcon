"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useAuthCompat } from "@/lib/hooks/useAuthCompat";

function LoginContent() {
  const auth = useAuthCompat();
  const router = useRouter();
  const search = useSearchParams();
  const [redirectAttempted, setRedirectAttempted] = useState(false);
  const [callbackProcessed, setCallbackProcessed] = useState(false);
  
  // Extract error parameters from URL (available in render scope)
  const error = search.get("error");
  const errorDescription = search.get("error_description");

  useEffect(() => {
    // If already authenticated, go to reports
    if (auth.isAuthenticated) {
      router.replace("/reports");
      return;
    }

    // Check if this is a callback from Cognito (or mock auth)
    const code = search.get("code");
    const state = search.get("state");
    const isCallback = !!code && !!state;
    
    // Log any OAuth errors
    if (error) {
      console.error("[AUTH] OAuth error:", error, errorDescription);
    }

    // If callback, let AuthProvider handle it automatically
    if (isCallback && !callbackProcessed) {
      setCallbackProcessed(true);
      console.log(
        "[AUTH] Callback detected, AuthProvider will process automatically..."
      );
      return;
    }

    // Otherwise, redirect to sign in (Cognito or mock auth)
    if (
      !auth.isLoading &&
      !auth.isAuthenticated &&
      !redirectAttempted &&
      !isCallback
    ) {
      setRedirectAttempted(true);
      console.log("[AUTH] Attempting redirect to sign in...");
      
      // Use the auth provider's signinRedirect method
      // This will use /oauth2/authorize for Cognito or mock auth for bypass mode
      auth.signinRedirect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    auth.isAuthenticated,
    auth.isLoading,
    redirectAttempted,
    callbackProcessed,
  ]);

  // After successful auth from callback, redirect to reports
  useEffect(() => {
    if (auth.isAuthenticated) {
      router.replace("/reports");
    }
  }, [auth.isAuthenticated, router]);

  // Show minimal loading state while redirecting or processing
  return (
    <div className="text-center">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Stratcon</h1>
        <p className="text-gray-600">
          {auth.isLoading ? "Processing..." : "Redirecting to sign in..."}
        </p>
        {(auth.error || error) && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            <p className="font-semibold">
              {error ? `Authentication Error: ${error}` : auth.error ? `Error: ${auth.error}` : "Authentication error"}
            </p>
            {errorDescription && (
              <p className="mt-1 text-xs">{errorDescription}</p>
            )}
            {auth.error && (
              <p className="mt-1 text-xs">Check console for details</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
