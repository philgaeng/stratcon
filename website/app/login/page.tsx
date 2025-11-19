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
      
      // For Cognito, manually construct the authorization URL to use /oauth2/authorize
      // This bypasses the library's metadata discovery which finds /login endpoint
      if (process.env.NEXT_PUBLIC_BYPASS_AUTH !== "true") {
        const cognitoDomain = "ap-southeast-1htvo9y0bb.auth.ap-southeast-1.amazoncognito.com";
        const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "384id7i8oh9vci2ck2afip4vsn";
        const redirectUri = `${window.location.origin}/login`;
        const state = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        
        // Store state in sessionStorage for validation on callback
        sessionStorage.setItem("oidc_state", state);
        
        // Construct authorization URL with /oauth2/authorize (not /login)
        const authUrl = `https://${cognitoDomain}/oauth2/authorize?` +
          `client_id=${encodeURIComponent(clientId)}&` +
          `response_type=code&` +
          `scope=${encodeURIComponent("openid email")}&` +
          `redirect_uri=${encodeURIComponent(redirectUri)}&` +
          `state=${encodeURIComponent(state)}`;
        
        console.log("[AUTH] Redirecting to Cognito OAuth2 endpoint:", authUrl);
        window.location.href = authUrl;
        return;
      }
      
      // For mock auth, use the library's signinRedirect
      auth
        .signinRedirect()
        .then(() => {
          console.log("[AUTH] Redirect initiated successfully");
        })
        .catch((error) => {
          console.error("[AUTH] Redirect error:", error);
          alert(
            `Redirect failed: ${
              error.message || error
            }. Check console for details.`
          );
        });
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
              {error ? `Authentication Error: ${error}` : `Error: ${auth.error?.message}`}
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
