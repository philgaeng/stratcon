"use client";

import { useAuthCompat } from "@/lib/hooks/useAuthCompat";

export default function AuthButtons() {
  const auth = useAuthCompat();

  const signOutRedirect = () => {
    auth.signoutRedirect();
  };

  if (auth.isLoading) {
    return null;
  }

  // Get email from user object (works for both mock and Cognito auth)
  const userEmail = auth.user?.email || "";


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
