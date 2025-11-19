"use client";

import { useAuthCompat } from "@/lib/hooks/useAuthCompat";

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN || "";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "";
const LOGOUT_URI =
  process.env.NEXT_PUBLIC_LOGOUT_URI || "http://localhost:3000/";

export default function AuthButtons() {
  const auth = useAuthCompat();

  const signOutRedirect = async () => {
    // Use mock auth signout for demo
    if (process.env.NEXT_PUBLIC_BYPASS_AUTH === "true" || !COGNITO_DOMAIN || !CLIENT_ID) {
      await auth.signoutRedirect();
      return;
    }
    // Real Cognito logout
    const url = `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${encodeURIComponent(
      LOGOUT_URI
    )}`;
    window.location.href = url;
  };

  if (auth.isLoading) {
    return null;
  }

  // Get email from user object (works for both mock and real auth)
  // MockUser has email at top level, real auth may have it in profile
  const userEmail = auth.user?.email || (auth.user as any)?.profile?.email || "";

  return auth.isAuthenticated ? (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-600">{userEmail}</span>
      <button
        onClick={signOutRedirect}
        className="px-3 py-1 text-sm rounded bg-gray-200 hover:bg-gray-300"
      >
        Sign out
      </button>
    </div>
  ) : (
    <button
      onClick={() => auth.signinRedirect()}
      className="px-3 py-1 text-sm rounded bg-[#4CAF50] text-white hover:bg-[#388E3C]"
    >
      Sign in
    </button>
  );
}
