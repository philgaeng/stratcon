"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useAuthCompat } from "@/lib/hooks/useAuthCompat";

function LoginContent() {
  const auth = useAuthCompat();
  const router = useRouter();
  const search = useSearchParams();
  const [isRedirecting, setIsRedirecting] = useState(false);
  
  // Extract error parameters from URL
  const error = search.get("error");
  const errorDescription = search.get("error_description");

  useEffect(() => {
    // If already authenticated, redirect to reports
    if (auth.isAuthenticated) {
      router.replace("/reports");
      return;
    }

    // Check if this is a callback from Cognito
    const code = search.get("code");
    const state = search.get("state");
    const isCallback = !!code && !!state;
    
    // If callback, let AuthProvider handle it automatically
    if (isCallback) {
      return;
    }

    // If there's an error, show it (don't auto-redirect)
    if (error) {
      console.error("[AUTH] OAuth error:", error, errorDescription);
      return;
    }

    // Auto-redirect to Cognito Hosted UI if not loading and not authenticated
    if (!auth.isLoading && !auth.isAuthenticated && !isRedirecting) {
      setIsRedirecting(true);
      auth.signinRedirect();
    }
  }, [auth.isAuthenticated, auth.isLoading, isRedirecting, router, search, error, errorDescription, auth]);

  // Show simple loading state while redirecting
  if (isRedirecting || auth.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mb-4">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Stratcon</h1>
            <p className="text-gray-600">Redirecting to sign in...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error || auth.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto px-4">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Stratcon</h1>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-left">
            <p className="font-semibold text-red-800 mb-2">Authentication Error</p>
            <p className="text-sm text-red-700">
              {errorDescription || (auth.error ? String(auth.error) : null) || error || "An error occurred during authentication"}
            </p>
          </div>
          <button
            onClick={() => {
              setIsRedirecting(false);
              auth.signinRedirect();
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Default: show simple login prompt
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Stratcon</h1>
        <p className="text-gray-600 mb-6">Please sign in to continue</p>
        <button
          onClick={() => {
            setIsRedirecting(true);
            auth.signinRedirect();
          }}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
        >
          Sign In
        </button>
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
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Stratcon</h1>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
