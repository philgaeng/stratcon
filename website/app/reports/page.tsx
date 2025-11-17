"use client";

import { useSelection } from "@/app/providers/SelectionProvider";
import api, { ClientReportRequest, ReportRequest } from "@/lib/api-client";
import { format } from "date-fns";
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

export default function ReportsPage() {
  const auth = useAuth();
  const { selection, setClient, setTenant } = useSelection();
  const [clients, setClients] = useState<string[]>([]);
  const [tenants, setTenants] = useState<string[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>("");
  const [selectedTenant, setSelectedTenant] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [startTime, setStartTime] = useState<string>("23:59");
  const [endDate, setEndDate] = useState<string>("");
  const [endTime, setEndTime] = useState<string>("23:59");
  const [isLoading, setIsLoading] = useState(false);

  // Get authenticated user's email
  const userEmail = auth.user?.profile?.email || "";
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isBuildingSubmitting, setIsBuildingSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  const shouldRedirect = !auth.isLoading && !auth.isAuthenticated;

  const loadClients = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await api.getClients();
      setClients(response.clients);
      if (response.clients.length > 0) {
        setSelectedClient(response.clients[0]);
      }
    } catch (error: unknown) {
      setErrorMessage(`Failed to load clients: ${resolveErrorMessage(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadTenants = useCallback(async (clientToken: string) => {
    try {
      setIsLoading(true);
      const response = await api.getTenants(clientToken);
      setTenants(response.tenants);
      if (response.tenants.length > 0) {
        setSelectedTenant(response.tenants[0]);
      }
    } catch (error: unknown) {
      setErrorMessage(`Failed to load tenants: ${resolveErrorMessage(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Protect route - redirect to login if not authenticated
  useEffect(() => {
    if (shouldRedirect) {
      window.location.href = "/login";
    }
  }, [shouldRedirect]);

  // Load clients on mount
  useEffect(() => {
    if (!auth.isLoading && auth.isAuthenticated) {
      void loadClients();
    }
  }, [auth.isLoading, auth.isAuthenticated, loadClients]);

  // Load tenants when client changes
  useEffect(() => {
    if (!auth.isLoading && auth.isAuthenticated && selectedClient) {
      void loadTenants(selectedClient);
    } else {
      setTenants([]);
      setSelectedTenant("");
    }
  }, [auth.isLoading, auth.isAuthenticated, selectedClient, loadTenants]);

  // Sync from explorer selection to form
  useEffect(() => {
    if (selection.client && selection.client !== selectedClient) {
      setSelectedClient(selection.client);
    }
    if (selection.tenant && selection.tenant !== selectedTenant) {
      setSelectedTenant(selection.tenant);
    }
  }, [selection.client, selection.tenant, selectedClient, selectedTenant]);

  // Sync form changes back to explorer (so user can also select from dropdowns)
  const handleClientChange = (client: string) => {
    setSelectedClient(client);
    setClient(client);
  };

  const handleTenantChange = (tenant: string) => {
    setSelectedTenant(tenant);
    setTenant(tenant);
  };

  const handleBuildingReport = async (
    reportType: "billing-info" | "latest-records"
  ) => {
    setErrorMessage("");
    setSuccessMessage("");

    if (!selectedClient) {
      setErrorMessage("Please select a client");
      return;
    }

    if (!auth.isAuthenticated || !userEmail) {
      setErrorMessage("You must be authenticated to generate reports");
      return;
    }

    try {
      setIsBuildingSubmitting(true);
      const request: ClientReportRequest = {
        client_token: selectedClient,
        user_email: userEmail,
      };

      const response =
        reportType === "billing-info"
          ? await api.generateBillingInfo(request)
          : await api.generateLastRecords(request);

      setSuccessMessage(
        `Report generation started! ${response.message}. You will receive an email at ${userEmail} when the report is ready.`
      );
    } catch (error: unknown) {
      setErrorMessage(
        `Failed to generate report: ${resolveErrorMessage(error)}`
      );
    } finally {
      setIsBuildingSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    if (!selectedClient || !selectedTenant) {
      setErrorMessage("Please select both client and tenant");
      return;
    }

    if (!auth.isAuthenticated || !userEmail) {
      setErrorMessage("You must be authenticated to generate reports");
      return;
    }

    try {
      setIsSubmitting(true);
      const request: ReportRequest = {
        tenant_token: selectedTenant,
        client_token: selectedClient,
        user_email: userEmail,
      };

      if (startDate && startTime) {
        request.start_date = startDate;
        request.start_time = startTime;
      }
      if (endDate && endTime) {
        request.end_date = endDate;
        request.end_time = endTime;
      }

      const response = await api.generateReport(request);
      setSuccessMessage(
        `Report generation started! ${response.message}. You will receive an email at ${userEmail} when the report is ready.`
      );

      // Reset form (except client/tenant)
      setSelectedMonth("");
      setStartDate("");
      setStartTime("23:59");
      setEndDate("");
      setEndTime("23:59");
    } catch (error: unknown) {
      setErrorMessage(
        `Failed to generate report: ${resolveErrorMessage(error)}`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Generate month options (current month and last 12 months)
  const getMonthOptions = () => {
    const options = [];
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const value = format(date, "yyyy-MM");
      const label = format(date, "MMMM yyyy");
      options.push({ value, label });
    }
    return options;
  };

  // Show loading while checking auth
  if (auth.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (redirect will happen)
  if (!auth.isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-full">
      <div
        className="px-4 sm:px-6 lg:px-8"
        style={{ paddingTop: "1.2rem", paddingBottom: "1.5rem" }}
      >
        {/* Content grid: 60/40 split */}
        <div className="flex items-start" style={{ gap: "1.5rem" }}>
          <div
            style={{
              flex: "0 0 calc(60% - 1rem)",
              display: "flex",
              flexDirection: "column",
              gap: "1.2rem",
            }}
          >
            {/* Month Report tile */}
            <section className="tile">
              <div className="tile-content">
                {/* h2 uses Montserrat - standard font for headings */}
                <h2 className="text-lg font-semibold text-gray-800">
                  Generate Month Report
                </h2>
                {/* p uses Inter via globals.css body font */}
                <p className="text-sm text-gray-700">
                  Generates reports for the last complete cutoff month for the
                  selected scope.
                </p>
                {selection.client && (
                  <div className="text-xs text-gray-600">
                    Selected: {selection.client}
                    {selection.tenant && ` → ${selection.tenant}`}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="form-label">Client</label>
                    <select
                      value={selectedClient}
                      onChange={(e) => handleClientChange(e.target.value)}
                      disabled={isLoading}
                      className="form-input"
                    >
                      <option value="">Select client...</option>
                      {clients.map((client) => (
                        <option key={client} value={client}>
                          {client}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Tenant</label>
                    <select
                      value={selectedTenant}
                      onChange={(e) => handleTenantChange(e.target.value)}
                      disabled={isLoading || !selectedClient}
                      className="form-input"
                    >
                      <option value="">Select tenant...</option>
                      {tenants.map((tenant) => (
                        <option key={tenant} value={tenant}>
                          {tenant}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {/* Month Selection */}
                <div>
                  <label htmlFor="month" className="form-label">
                    Month (Optional)
                  </label>
                  <select
                    id="month"
                    value={selectedMonth}
                    onChange={(e) => setSelectedMonth(e.target.value)}
                    className="form-input"
                  >
                    <option value="">All available months</option>
                    {getMonthOptions().map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  disabled={
                    !selection.client ||
                    !selection.tenant ||
                    isLoading ||
                    isSubmitting
                  }
                  onClick={async () => {
                    if (!selection.client || !selection.tenant) {
                      setErrorMessage(
                        "Please select a client and tenant from the explorer"
                      );
                      return;
                    }
                    if (!auth.isAuthenticated || !userEmail) {
                      setErrorMessage(
                        "You must be authenticated to generate reports"
                      );
                      return;
                    }
                    // Trigger last complete month generation by calling tenant report without month
                    try {
                      setIsSubmitting(true);
                      setErrorMessage("");
                      setSuccessMessage("");
                      const request: ReportRequest = {
                        tenant_token: selection.tenant,
                        client_token: selection.client,
                        user_email: userEmail,
                      };
                      if (selectedMonth) {
                        request.month = selectedMonth;
                      }
                      const res = await api.generateReport(request);
                      setSuccessMessage(
                        `Report generation started! ${res.message}. You will receive an email at ${userEmail} when the report is ready.`
                      );
                    } catch (error: unknown) {
                      setErrorMessage(
                        `Failed to start monthly report: ${resolveErrorMessage(
                          error
                        )}`
                      );
                    } finally {
                      setIsSubmitting(false);
                    }
                  }}
                  className="btn-primary"
                >
                  {isSubmitting ? "Working…" : "Generate Last Complete Month"}
                </button>
              </div>
            </section>

            {/* Custom report tile */}
            <form onSubmit={handleSubmit} className="tile-spaced">
              <div className="tile-content">
                <h2 className="text-lg font-semibold text-gray-800">
                  Generate Custom Report
                </h2>
                {/* Client Selection */}
                <div>
                  <label htmlFor="client" className="form-label-spaced">
                    Client
                  </label>
                  <select
                    id="client"
                    value={selectedClient}
                    onChange={(e) => handleClientChange(e.target.value)}
                    disabled={isLoading}
                    className="form-input shadow-sm"
                  >
                    <option value="">Select client...</option>
                    {clients.map((client) => (
                      <option key={client} value={client}>
                        {client}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Tenant Selection */}
                <div>
                  <label htmlFor="tenant" className="form-label-spaced">
                    Tenant
                  </label>
                  <select
                    id="tenant"
                    value={selectedTenant}
                    onChange={(e) => handleTenantChange(e.target.value)}
                    disabled={isLoading || !selectedClient}
                    className="form-input shadow-sm"
                  >
                    <option value="">Select tenant...</option>
                    {tenants.map((tenant) => (
                      <option key={tenant} value={tenant}>
                        {tenant}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Start Date and Time - side by side */}
                <div className="form-row">
                  <div>
                    <label htmlFor="startDate" className="form-label-spaced">
                      Start Date (Optional)
                    </label>
                    <input
                      type="date"
                      id="startDate"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="form-input shadow-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="startTime" className="form-label-spaced">
                      Start Time (Optional)
                    </label>
                    <input
                      type="time"
                      id="startTime"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      className="form-input shadow-sm"
                    />
                  </div>
                </div>

                {/* End Date and Time - side by side */}
                <div className="form-row">
                  <div>
                    <label htmlFor="endDate" className="form-label-spaced">
                      End Date (Optional)
                    </label>
                    <input
                      type="date"
                      id="endDate"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="form-input shadow-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="endTime" className="form-label-spaced">
                      End Time (Optional)
                    </label>
                    <input
                      type="time"
                      id="endTime"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      className="form-input shadow-sm"
                    />
                  </div>
                </div>

                {/* Email info - using authenticated user's email */}
                {userEmail && (
                  <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded">
                    <p className="text-sm">
                      <strong>Report will be sent to:</strong> {userEmail}
                    </p>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={
                    isSubmitting ||
                    isLoading ||
                    !selectedClient ||
                    !selectedTenant ||
                    !auth.isAuthenticated ||
                    !userEmail
                  }
                  className="btn-primary"
                >
                  {isSubmitting ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Generating Report...
                    </>
                  ) : (
                    "Generate Report"
                  )}
                </button>
              </div>
            </form>
          </div>
          {/* Client Reports column */}
          <section
            className="tile-spaced"
            style={{
              flex: "0 0 calc(40% - 1rem)",
            }}
          >
            <div className="tile-content">
              <div>
                <h2 className="text-lg font-semibold text-gray-800">
                  Generate Client Reports
                </h2>
                <p className="text-sm text-gray-700">
                  Generate CSV reports for all tenants in the selected client.
                  Reports will be emailed to you.
                </p>
              </div>

              <div className="btn-group-two">
                <button
                  type="button"
                  onClick={() => handleBuildingReport("billing-info")}
                  disabled={
                    isBuildingSubmitting ||
                    isLoading ||
                    !selectedClient ||
                    !auth.isAuthenticated ||
                    !userEmail
                  }
                  className="btn-primary"
                >
                  {isBuildingSubmitting ? "Working…" : "Generate Billing Info"}
                </button>
                <button
                  type="button"
                  onClick={() => handleBuildingReport("latest-records")}
                  disabled={
                    isBuildingSubmitting ||
                    isLoading ||
                    !selectedClient ||
                    !auth.isAuthenticated ||
                    !userEmail
                  }
                  className="btn-primary"
                >
                  {isBuildingSubmitting ? "Working…" : "Generate Last Records"}
                </button>
              </div>
            </div>
          </section>
        </div>
        {(errorMessage || successMessage) && (
          <div className="mt-6 space-y-4">
            {errorMessage && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {errorMessage}
              </div>
            )}
            {successMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                {successMessage}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
