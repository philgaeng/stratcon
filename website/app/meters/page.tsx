"use client";

import api from "@/lib/api-client";
import { useRouteGuard } from "@/lib/hooks/useRouteGuard";
import { useUserInfo } from "@/lib/hooks/useUserInfo";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";

const resolveErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return "An unexpected error occurred";
  }
};

export default function MetersPage() {
  const auth = useAuth();
  const router = useRouter();
  const { userInfo, isLoading: isLoadingUserInfo } = useUserInfo();
  const [buildings, setBuildings] = useState<api.Building[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Protect route - only allow super_admin, client_admin, encoder
  useRouteGuard("meters");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  const loadBuildings = useCallback(async () => {
    if (!userInfo) {
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");

      const response = await api.getMeterBuildings(userInfo.user_id);
      setBuildings(response.buildings);
    } catch (error: unknown) {
      setErrorMessage(
        `Failed to load buildings: ${resolveErrorMessage(error)}`
      );
    } finally {
      setIsLoading(false);
    }
  }, [userInfo]);

  // Protect route - redirect to login if not authenticated
  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  // Load buildings on mount when user info is available
  useEffect(() => {
    if (
      !auth.isLoading &&
      auth.isAuthenticated &&
      !isLoadingUserInfo &&
      userInfo
    ) {
      void loadBuildings();
    }
  }, [
    auth.isLoading,
    auth.isAuthenticated,
    isLoadingUserInfo,
    userInfo,
    loadBuildings,
  ]);

  const handleBuildingSelect = (buildingId: number) => {
    router.push(`/meters/buildings/${buildingId}/tenants`);
  };

  if (auth.isLoading || isLoadingUserInfo || isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading buildings...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Meter Logging</h1>
      <h2 className="text-xl font-semibold mb-4">Select Building</h2>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search buildings..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {errorMessage && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {errorMessage}
        </div>
      )}

      {(() => {
        const filteredBuildings = buildings.filter((building) =>
          building.name.toLowerCase().startsWith(searchQuery.toLowerCase())
        );

        if (filteredBuildings.length === 0) {
          if (buildings.length === 0) {
            return (
              <div className="p-6 bg-gray-50 rounded border">
                <p className="text-gray-600">
                  No buildings assigned to your account.
                </p>
              </div>
            );
          }
          return (
            <div className="p-6 bg-gray-50 rounded border">
              <p className="text-gray-600">
                No buildings found matching "{searchQuery}".
              </p>
            </div>
          );
        }

        return (
          <div className="space-y-3">
            {filteredBuildings.map((building) => (
              <button
                key={building.id}
                onClick={() => handleBuildingSelect(building.id)}
                className="w-full p-4 text-left bg-white border rounded hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-lg">{building.name}</div>
                    <div className="text-sm text-gray-600">
                      Building ID: {building.id}
                    </div>
                  </div>
                  <div className="text-gray-400">▶</div>
                </div>
              </button>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
