"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "react-oidc-context";

export default function ConfirmationPage() {
  const auth = useAuth();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const tenantId = parseInt(params.tenantId as string, 10);
  const sessionId = searchParams.get("session");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  const handleBackToMeters = () => {
    router.push("/meters");
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="text-center py-12">
        <div className="mb-4">
          <div className="inline-block w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>
        <h1 className="text-2xl font-bold mb-2">
          Session Submitted Successfully!
        </h1>
        <p className="text-gray-600 mb-6">
          Your meter readings have been submitted and approved.
        </p>
        {sessionId && (
          <p className="text-sm text-gray-500 mb-6">Session ID: {sessionId}</p>
        )}
        <button
          onClick={handleBackToMeters}
          className="px-6 py-2 bg-[#4CAF50] text-white rounded hover:bg-[#388E3C]"
        >
          Back to Meters
        </button>
      </div>
    </div>
  );
}
