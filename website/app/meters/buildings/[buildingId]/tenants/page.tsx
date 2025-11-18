"use client";

import api, { type TenantSummary } from "@/lib/api-client";
import { format } from "date-fns";
import { useParams, useRouter } from "next/navigation";
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

export default function TenantsPage() {
  const auth = useAuthCompat();
  const router = useRouter();
  const params = useParams();
  const buildingId = parseInt(params.buildingId as string, 10);

  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [buildingName, setBuildingName] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  const loadTenants = useCallback(async () => {
    if (isNaN(buildingId)) {
      setErrorMessage("Invalid building ID");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");
      const response = await api.getMeterTenantsForBuilding(buildingId);
      setTenants(response.tenants);
      if (response.tenants.length > 0) {
        setBuildingName(response.tenants[0].building.name);
      }
    } catch (error: unknown) {
      setErrorMessage(`Failed to load tenants: ${resolveErrorMessage(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, [buildingId]);

  // Protect route - redirect to login if not authenticated
  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  // Load tenants on mount
  useEffect(() => {
    if (!auth.isLoading && auth.isAuthenticated && !isNaN(buildingId)) {
      void loadTenants();
    }
  }, [auth.isLoading, auth.isAuthenticated, buildingId, loadTenants]);

  const handleTenantSelect = (tenantId: number, tenantName: string) => {
    router.push(
      `/meters/tenants/${tenantId}/floors?building=${encodeURIComponent(
        buildingName
      )}&tenant=${encodeURIComponent(tenantName)}`
    );
  };

  const handleBack = () => {
    router.push("/meters");
  };

  if (auth.isLoading || isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading tenants...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={handleBack}
        className="mb-4 text-sm text-gray-600 hover:text-gray-900"
      >
        ← Back to Buildings
      </button>

      {buildingName && (
        <div className="text-sm text-gray-500 mb-2">{buildingName}</div>
      )}
      <h1 className="text-2xl font-bold mb-4">Select Tenant</h1>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search tenants..."
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
        const filteredTenants = tenants.filter((tenant) =>
          tenant.tenant_name.toLowerCase().startsWith(searchQuery.toLowerCase())
        );

        if (filteredTenants.length === 0) {
          if (tenants.length === 0) {
            return (
              <div className="p-6 bg-gray-50 rounded border">
                <p className="text-gray-600">
                  No tenants found for this building.
                </p>
              </div>
            );
          }
          return (
            <div className="p-6 bg-gray-50 rounded border">
              <p className="text-gray-600">
                No tenants found matching "{searchQuery}".
              </p>
            </div>
          );
        }

        return (
          <div className="space-y-3">
            {filteredTenants.map((tenant) => (
              <button
                key={tenant.tenant_id}
                onClick={() =>
                  handleTenantSelect(tenant.tenant_id, tenant.tenant_name)
                }
                className="w-full p-4 text-left bg-white border rounded hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-lg">
                      {tenant.tenant_name}
                    </div>
                    <div className="text-sm text-gray-600">
                      {tenant.active_units} active unit
                      {tenant.active_units !== 1 ? "s" : ""}
                      {tenant.last_record_at && (
                        <>
                          {" "}
                          • Last approved:{" "}
                          {format(
                            new Date(tenant.last_record_at),
                            "MMM d, yyyy"
                          )}
                        </>
                      )}
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
