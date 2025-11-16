"use client";

import { useAuth } from "react-oidc-context";

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN || "";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "";
const LOGOUT_URI =
  process.env.NEXT_PUBLIC_LOGOUT_URI || "http://localhost:3000/";

export default function AuthButtons() {
  const auth = useAuth();

  const signOutRedirect = () => {
    if (!COGNITO_DOMAIN || !CLIENT_ID) {
      auth.removeUser();
      return;
    }
    const url = `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${encodeURIComponent(
      LOGOUT_URI
    )}`;
    window.location.href = url;
  };

  if (auth.isLoading) {
    return null;
  }

  return auth.isAuthenticated ? (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-600">{auth.user?.profile?.email}</span>
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
