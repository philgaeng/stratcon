"use client";

import api, { type MeterAssignment } from "@/lib/api-client";
import { useAuthCompat } from "@/lib/hooks/useAuthCompat";
import { formatMeterId } from "@/lib/meter-utils";
import { format } from "date-fns";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const resolveErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return "An unexpected error occurred";
  }
};

interface ReadingEntry {
  meterId: string;
  meterPk: number;
  reading: number | null;
  timestamp: Date;
  notes: string;
  photo: string | null;
}

export default function MetersPage() {
  const auth = useAuthCompat();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const tenantId = parseInt(params.tenantId as string, 10);
  const floorParam = searchParams.get("floor");
  const floor = floorParam ? parseInt(floorParam, 10) : undefined;
  const buildingName = searchParams.get("building") || "";
  const tenantNameFromParams = searchParams.get("tenant") || "";

  const [meters, setMeters] = useState<MeterAssignment[]>([]);
  const [tenantName, setTenantName] = useState<string>(tenantNameFromParams);
  const [readings, setReadings] = useState<Map<number, ReadingEntry>>(
    new Map()
  );
  const [selectedMeter, setSelectedMeter] = useState<MeterAssignment | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  const loadMeters = useCallback(async () => {
    if (isNaN(tenantId)) {
      setErrorMessage("Invalid tenant ID");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");
      const response = await api.getTenantMeters(tenantId, floor);
      setMeters(response.meters);

      // Use tenant name from URL params if available, otherwise fallback to ID
      if (!tenantNameFromParams) {
        setTenantName(`Tenant ${tenantId}`);
      }

      // Initialize readings map with current timestamp for each meter
      const initialReadings = new Map<number, ReadingEntry>();
      response.meters.forEach((meter) => {
        initialReadings.set(meter.meter_pk, {
          meterId: meter.meter_id,
          meterPk: meter.meter_pk,
          reading: null,
          timestamp: new Date(),
          notes: "",
          photo: null,
        });
      });
      setReadings(initialReadings);
    } catch (error: unknown) {
      setErrorMessage(`Failed to load meters: ${resolveErrorMessage(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId, floor]);

  // Protect route - redirect to login if not authenticated
  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  // Load meters on mount
  useEffect(() => {
    if (!auth.isLoading && auth.isAuthenticated && !isNaN(tenantId)) {
      void loadMeters();
    }
  }, [auth.isLoading, auth.isAuthenticated, tenantId, loadMeters]);

  const handleReadingChange = (meterPk: number, reading: number | null) => {
    setReadings((prev) => {
      const newReadings = new Map(prev);
      const entry = newReadings.get(meterPk) || {
        meterId: "",
        meterPk,
        reading: null,
        timestamp: new Date(),
        notes: "",
        photo: null,
      };
      newReadings.set(meterPk, { ...entry, reading });
      return newReadings;
    });
  };

  const handleTimestampChange = (meterPk: number, timestamp: Date) => {
    setReadings((prev) => {
      const newReadings = new Map(prev);
      const entry = newReadings.get(meterPk);
      if (entry) {
        newReadings.set(meterPk, { ...entry, timestamp });
      }
      return newReadings;
    });
  };

  const handleNotesChange = (meterPk: number, notes: string) => {
    setReadings((prev) => {
      const newReadings = new Map(prev);
      const entry = newReadings.get(meterPk);
      if (entry) {
        newReadings.set(meterPk, { ...entry, notes });
      }
      return newReadings;
    });
  };

  const handleReview = () => {
    const entriesWithReadings = Array.from(readings.values()).filter(
      (entry) => entry.reading !== null
    );

    if (entriesWithReadings.length === 0) {
      setErrorMessage("Please enter at least one reading before reviewing.");
      return;
    }

    // Store readings in localStorage for review page
    const readingsObj: Record<string, any> = {};
    entriesWithReadings.forEach((entry) => {
      readingsObj[entry.meterPk] = {
        ...entry,
        timestamp: entry.timestamp.toISOString(),
      };
    });
    localStorage.setItem(
      `readings-${tenantId}-${floor || "all"}`,
      JSON.stringify(readingsObj)
    );

    // Navigate to review page with session data
    router.push(`/meters/tenants/${tenantId}/review?floor=${floor || ""}`);
  };

  const handleBack = () => {
    if (floor !== undefined) {
      router.push(`/meters/tenants/${tenantId}/floors`);
    } else {
      router.push("/meters");
    }
  };

  const entriesWithReadings = Array.from(readings.values()).filter(
    (entry) => entry.reading !== null
  );

  if (auth.isLoading || isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading meters...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={handleBack}
        className="mb-4 text-sm text-gray-600 hover:text-gray-900"
      >
        ← Back
      </button>

      {(() => {
        const pathParts: string[] = [];
        if (buildingName) pathParts.push(buildingName);
        if (tenantName) pathParts.push(tenantName);
        if (floor !== undefined) pathParts.push(`Floor ${floor}`);

        return (
          <>
            {pathParts.length > 0 && (
              <div className="text-sm text-gray-500 mb-2">
                {pathParts.join(" / ")}
              </div>
            )}
          </>
        );
      })()}
      <h1 className="text-2xl font-bold mb-4">Select Meter</h1>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search meters..."
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

      {successMessage && (
        <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          {successMessage}
        </div>
      )}

      {(() => {
        const filteredMeters = meters.filter((meter) => {
          const meterDisplayId = formatMeterId(meter.meter_id);
          return meterDisplayId
            .toLowerCase()
            .startsWith(searchQuery.toLowerCase());
        });

        if (filteredMeters.length === 0) {
          if (meters.length === 0) {
            return (
              <div className="p-6 bg-gray-50 rounded border">
                <p className="text-gray-600">
                  No meters found for this tenant.
                </p>
              </div>
            );
          }
          return (
            <div className="p-6 bg-gray-50 rounded border">
              <p className="text-gray-600">
                No meters found matching "{searchQuery}".
              </p>
            </div>
          );
        }

        return (
          <>
            <div className="space-y-3 mb-6">
              {filteredMeters.map((meter) => {
                const entry = readings.get(meter.meter_pk);
                const hasReading = entry?.reading !== null;
                const lastReading = meter.last_record;

                return (
                  <div
                    key={meter.meter_pk}
                    className="p-4 bg-white border rounded"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="font-semibold text-lg">
                          {formatMeterId(meter.meter_id)}
                        </div>
                        <div className="text-sm text-gray-600">
                          {meter.unit.unit_number &&
                            `Unit ${meter.unit.unit_number}`}
                          {lastReading && (
                            <>
                              {" "}
                              • Last: {lastReading.meter_kWh.toFixed(1)} kWh (
                              {format(
                                new Date(lastReading.timestamp_record),
                                "MMM d"
                              )}
                              )
                            </>
                          )}
                        </div>
                      </div>
                      {hasReading && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                          ✓ Reading entered
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Reading (kWh)
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          value={entry?.reading ?? ""}
                          onChange={(e) =>
                            handleReadingChange(
                              meter.meter_pk,
                              e.target.value ? parseFloat(e.target.value) : null
                            )
                          }
                          className="w-full px-3 py-2 border rounded"
                          placeholder="Enter reading"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Timestamp
                        </label>
                        <input
                          type="datetime-local"
                          value={
                            entry?.timestamp
                              ? format(entry.timestamp, "yyyy-MM-dd'T'HH:mm")
                              : format(new Date(), "yyyy-MM-dd'T'HH:mm")
                          }
                          onChange={(e) =>
                            handleTimestampChange(
                              meter.meter_pk,
                              new Date(e.target.value)
                            )
                          }
                          className="w-full px-3 py-2 border rounded"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Notes (optional)
                        </label>
                        <textarea
                          value={entry?.notes ?? ""}
                          onChange={(e) =>
                            handleNotesChange(meter.meter_pk, e.target.value)
                          }
                          className="w-full px-3 py-2 border rounded"
                          rows={2}
                          placeholder="Add notes..."
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Photo (optional)
                        </label>
                        <input
                          type="file"
                          accept="image/*"
                          capture="environment"
                          className="w-full px-3 py-2 border rounded"
                          onChange={(e) => {
                            // TODO: Handle photo upload
                            console.log("Photo selected:", e.target.files?.[0]);
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-sm text-gray-600">
                {entriesWithReadings.length} of {filteredMeters.length} meters
                with readings
              </div>
              <button
                onClick={handleReview}
                disabled={entriesWithReadings.length === 0}
                className="px-6 py-2 bg-[#4CAF50] text-white rounded hover:bg-[#388E3C] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Review & Submit
              </button>
            </div>
          </>
        );
      })()}
    </div>
  );
}
