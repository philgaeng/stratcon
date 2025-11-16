"use client";

import api from "@/lib/api-client";
import { formatMeterId, generateSessionId } from "@/lib/meter-utils";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
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

interface ReadingEntry {
  meterId: string;
  meterPk: number;
  reading: number;
  timestamp: Date;
  notes: string;
  photo: string | null;
}

export default function ReviewPage() {
  const auth = useAuth();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const tenantId = parseInt(params.tenantId as string, 10);
  const floorParam = searchParams.get("floor");
  const floor = floorParam ? parseInt(floorParam, 10) : undefined;

  const [meters, setMeters] = useState<api.MeterAssignment[]>([]);
  const [readings, setReadings] = useState<Map<number, ReadingEntry>>(
    new Map()
  );
  const [approverName, setApproverName] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);

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

      // Load readings from localStorage (set by meters page)
      const storedReadings = localStorage.getItem(
        `readings-${tenantId}-${floor || "all"}`
      );
      if (storedReadings) {
        const parsed = JSON.parse(storedReadings);
        const readingsMap = new Map<number, ReadingEntry>();
        Object.entries(parsed).forEach(([key, value]) => {
          const meterPk = parseInt(key, 10);
          const entry = value as any;
          readingsMap.set(meterPk, {
            ...entry,
            timestamp: new Date(entry.timestamp),
          });
        });
        setReadings(readingsMap);
      }
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

  // Initialize signature canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    const startDrawing = (e: MouseEvent | TouchEvent) => {
      setIsDrawing(true);
      const rect = canvas.getBoundingClientRect();
      const x =
        "touches" in e
          ? e.touches[0].clientX - rect.left
          : e.clientX - rect.left;
      const y =
        "touches" in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;
      ctx.beginPath();
      ctx.moveTo(x, y);
    };

    const draw = (e: MouseEvent | TouchEvent) => {
      if (!isDrawing) return;
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const x =
        "touches" in e
          ? e.touches[0].clientX - rect.left
          : e.clientX - rect.left;
      const y =
        "touches" in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;
      ctx.lineTo(x, y);
      ctx.stroke();
    };

    const stopDrawing = () => {
      if (isDrawing) {
        setIsDrawing(false);
        setSignature(canvas.toDataURL());
      }
    };

    canvas.addEventListener("mousedown", startDrawing);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", stopDrawing);
    canvas.addEventListener("mouseout", stopDrawing);
    canvas.addEventListener("touchstart", startDrawing);
    canvas.addEventListener("touchmove", draw);
    canvas.addEventListener("touchend", stopDrawing);

    return () => {
      canvas.removeEventListener("mousedown", startDrawing);
      canvas.removeEventListener("mousemove", draw);
      canvas.removeEventListener("mouseup", stopDrawing);
      canvas.removeEventListener("mouseout", stopDrawing);
      canvas.removeEventListener("touchstart", startDrawing);
      canvas.removeEventListener("touchmove", draw);
      canvas.removeEventListener("touchend", stopDrawing);
    };
  }, [isDrawing]);

  const handleSubmit = async () => {
    if (!approverName.trim()) {
      setErrorMessage("Please enter approver name");
      return;
    }

    if (!signature) {
      setErrorMessage("Please provide a signature");
      return;
    }

    const entriesWithReadings = Array.from(readings.values()).filter(
      (entry) => entry.reading !== null
    );

    if (entriesWithReadings.length === 0) {
      setErrorMessage("No readings to submit");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage("");

      // Get building ID from first meter (we need it for session ID)
      const firstMeter = meters[0];
      if (!firstMeter) {
        throw new Error("No meters found");
      }

      // Generate session ID
      const sessionId = generateSessionId(tenantId);

      // Submit meter records
      const records: api.MeterRecordInput[] = entriesWithReadings.map(
        (entry) => ({
          meter_id: entry.meterId,
          timestamp_record: entry.timestamp.toISOString(),
          meter_kW: entry.reading,
          client_record_id: `${sessionId}:${
            entry.meterPk
          }:${entry.timestamp.toISOString()}`,
        })
      );

      const userId = localStorage.getItem("userId");
      const recordResponse = await api.submitMeterRecords({
        tenant_id: tenantId,
        session_id: sessionId,
        encoder_user_id: userId ? parseInt(userId, 10) : undefined,
        records,
      });

      // Submit approval
      await api.submitApproval({
        session_id: sessionId,
        tenant_id: tenantId,
        approver: {
          name: approverName,
          signature_blob: signature,
        },
      });

      // Clear stored readings
      localStorage.removeItem(`readings-${tenantId}-${floor || "all"}`);

      setSuccessMessage("Session submitted successfully!");

      // Redirect to confirmation page after a delay
      setTimeout(() => {
        router.push(
          `/meters/tenants/${tenantId}/confirmation?session=${sessionId}`
        );
      }, 2000);
    } catch (error: unknown) {
      setErrorMessage(`Failed to submit: ${resolveErrorMessage(error)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBack = () => {
    router.push(`/meters/tenants/${tenantId}/meters?floor=${floor || ""}`);
  };

  const entriesWithReadings = Array.from(readings.values()).filter(
    (entry) => entry.reading !== null
  );

  // Calculate deltas
  const readingsWithDeltas = entriesWithReadings.map((entry) => {
    const meter = meters.find((m) => m.meter_pk === entry.meterPk);
    const lastReading = meter?.last_record;
    const delta = lastReading ? entry.reading - lastReading.meter_kW : null;
    return { entry, meter, delta, lastReading };
  });

  if (auth.isLoading || isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading review...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={handleBack}
        className="mb-4 text-sm text-gray-600 hover:text-gray-900"
      >
        ← Back to Meters
      </button>

      <h1 className="text-2xl font-bold mb-4">Review & Approval</h1>

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

      <div className="mb-6">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">Meter</th>
              <th className="text-right p-2">Last (kWh)</th>
              <th className="text-right p-2">New (kWh)</th>
              <th className="text-right p-2">Δ</th>
            </tr>
          </thead>
          <tbody>
            {readingsWithDeltas.map(({ entry, meter, delta, lastReading }) => (
              <tr key={entry.meterPk} className="border-b">
                <td className="p-2 font-medium">
                  {formatMeterId(entry.meterId)}
                </td>
                <td className="p-2 text-right text-gray-600">
                  {lastReading ? lastReading.meter_kW.toFixed(1) : "—"}
                </td>
                <td className="p-2 text-right">{entry.reading.toFixed(1)}</td>
                <td
                  className={`p-2 text-right ${
                    delta !== null && delta < 0
                      ? "text-red-600"
                      : "text-green-600"
                  }`}
                >
                  {delta !== null
                    ? (delta >= 0 ? "+" : "") + delta.toFixed(1)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Approver Name *
          </label>
          <input
            type="text"
            value={approverName}
            onChange={(e) => setApproverName(e.target.value)}
            className="w-full px-3 py-2 border rounded"
            placeholder="Enter approver name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Signature *
          </label>
          <div className="border rounded p-4 bg-white">
            <canvas
              ref={canvasRef}
              width={600}
              height={200}
              className="border rounded cursor-crosshair w-full"
              style={{ maxWidth: "100%", height: "auto" }}
            />
            <button
              onClick={() => {
                const canvas = canvasRef.current;
                if (canvas) {
                  const ctx = canvas.getContext("2d");
                  if (ctx) {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    setSignature(null);
                  }
                }
              }}
              className="mt-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || !approverName.trim() || !signature}
          className="px-6 py-2 bg-[#4CAF50] text-white rounded hover:bg-[#388E3C] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Submitting..." : "Submit Session"}
        </button>
      </div>
    </div>
  );
}
