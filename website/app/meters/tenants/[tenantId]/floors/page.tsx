"use client";

import api from "@/lib/api-client";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuthCompat } from "@/lib/hooks/useAuthCompat";

const resolveErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return "An unexpected error occurred";
  }
};

export default function FloorsPage() {
  const auth = useAuthCompat();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const tenantId = parseInt(params.tenantId as string, 10);

  const buildingName = searchParams.get("building") || "";
  const tenantName = searchParams.get("tenant") || "";

  const [floors, setFloors] = useState<api.FloorSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  const loadFloors = useCallback(async () => {
    if (isNaN(tenantId)) {
      setErrorMessage("Invalid tenant ID");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");
      const response = await api.getTenantFloors(tenantId);
      setFloors(response.floors);

      // If only one floor, automatically proceed to meters
      if (response.floors.length === 1 && response.floors[0].floor !== null) {
        const params = new URLSearchParams({
          floor: response.floors[0].floor.toString(),
        });
        if (buildingName) params.set("building", buildingName);
        if (tenantName) params.set("tenant", tenantName);
        router.push(`/meters/tenants/${tenantId}/meters?${params.toString()}`);
        return;
      }
    } catch (error: unknown) {
      setErrorMessage(`Failed to load floors: ${resolveErrorMessage(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId, router]);

  // Protect route - redirect to login if not authenticated
  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  // Load floors on mount
  useEffect(() => {
    if (!auth.isLoading && auth.isAuthenticated && !isNaN(tenantId)) {
      void loadFloors();
    }
  }, [auth.isLoading, auth.isAuthenticated, tenantId, loadFloors]);

  const handleFloorSelect = (floor: number | null) => {
    if (floor === null) return;
    const params = new URLSearchParams({
      floor: floor.toString(),
    });
    if (buildingName) params.set("building", buildingName);
    if (tenantName) params.set("tenant", tenantName);
    router.push(`/meters/tenants/${tenantId}/meters?${params.toString()}`);
  };

  const handleBack = () => {
    // Go back to building tenants - we need to get building ID from somewhere
    // For now, just go back to meters home
    router.push("/meters");
  };

  if (auth.isLoading || isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading floors...</div>
      </div>
    );
  }

  // If no floors or only one floor, skip this page
  if (floors.length <= 1) {
    return null;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={handleBack}
        className="mb-4 text-sm text-gray-600 hover:text-gray-900"
      >
        ← Back
      </button>

      {buildingName && tenantName && (
        <div className="text-sm text-gray-500 mb-2">
          {buildingName} / {tenantName}
        </div>
      )}
      <h1 className="text-2xl font-bold mb-4">Select Floor</h1>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search floors..."
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
        const filteredFloors = floors.filter((floor) => {
          if (floor.floor === null) return false;
          const floorNumber = floor.floor.toString();
          return floorNumber.startsWith(searchQuery);
        });

        if (filteredFloors.length === 0) {
          if (floors.length === 0) {
            return (
              <div className="p-6 bg-gray-50 rounded border">
                <p className="text-gray-600">
                  No floors found for this tenant.
                </p>
              </div>
            );
          }
          return (
            <div className="p-6 bg-gray-50 rounded border">
              <p className="text-gray-600">
                No floors found matching "{searchQuery}".
              </p>
            </div>
          );
        }

        return (
          <div className="space-y-3">
            {filteredFloors.map((floor) => (
              <button
                key={floor.floor ?? "unknown"}
                onClick={() => handleFloorSelect(floor.floor)}
                disabled={floor.floor === null}
                className="w-full p-4 text-left bg-white border rounded hover:bg-gray-50 hover:border-gray-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-lg">
                      Floor {floor.floor ?? "Unknown"}
                    </div>
                    <div className="text-sm text-gray-600">
                      {floor.unit_count} unit{floor.unit_count !== 1 ? "s" : ""}{" "}
                      • {floor.meter_count} meter
                      {floor.meter_count !== 1 ? "s" : ""}
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
