/**
 * API Client for FastAPI Backend
 */

import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth-related metadata if available
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const userId = localStorage.getItem("userId");
      if (userId) {
        if (!config.headers) {
          config.headers = {};
        }
        config.headers["x-user-id"] = userId;
        config.params = {
          ...(config.params || {}),
          user_id: userId,
        };
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export interface Client {
  name: string;
}

export interface Tenant {
  name: string;
}

export interface ClientsResponse {
  clients: string[];
  count: number;
}

export interface TenantsResponse {
  client: string;
  tenants: string[];
  count: number;
}

export interface BuildingsResponse {
  client: string;
  buildings: string[];
  count: number;
}

export interface ReportRequest {
  tenant_token: string;
  client_token?: string;
  month?: string; // Format: YYYY-MM
  cutoff_date?: string; // Format: YYYY-MM-DD
  cutoff_time?: string; // Format: HH:mm
  start_date?: string; // Format: YYYY-MM-DD
  start_time?: string; // Format: HH:mm
  end_date?: string; // Format: YYYY-MM-DD
  end_time?: string; // Format: HH:mm
  user_email?: string;
  floor?: number;
  unit_id?: number;
  load_ids?: number[];
}

export interface ReportResponse {
  status: string;
  message: string;
  client: string;
}

export interface BuildingReportRequest {
  client_token: string;
  building_token: string;
  month?: string; // Format: YYYY-MM
  user_email?: string;
}

export interface ClientReportRequest {
  client_token: string;
  user_email: string;
}

// Meter Logging Types
export interface Building {
  id: number;
  name: string;
  client_id: number;
}

export interface MeterBuildingsResponse {
  buildings: Building[];
}

export interface TenantSummary {
  tenant_id: number;
  tenant_name: string;
  client_id: number;
  building: {
    id: number;
    name: string;
    floor: number | null;
  };
  active_units: number;
  last_record_at: string | null;
}

export interface TenantSummaryResponse {
  tenants: TenantSummary[];
}

export interface FloorSummary {
  floor: number | null;
  unit_count: number;
  meter_count: number;
}

export interface FloorsResponse {
  tenant_id: number;
  floors: FloorSummary[];
}

export interface TenantUnitsResponse {
  tenant_id: number;
  tenant: string;
  units: TenantUnit[];
}

export interface TenantUnit {
  unit_id: number;
  unit_number: string | null;
  floor: number | null;
  name?: string | null;
}

export interface TenantFloorsResponse {
  tenant_id: number;
  tenant: string;
  floors: FloorSummary[];
}

export interface MeterAssignment {
  meter_id: string;
  meter_pk: number;
  unit: {
    id: number;
    unit_number: string | null;
    floor: number | null;
  };
  loads: number[];
  last_record: {
    timestamp_record: string;
    meter_kWh: number;
  } | null;
}

export interface MeterAssignmentsResponse {
  tenant_id: number;
  meters: MeterAssignment[];
}

export interface MeterRecordInput {
  client_record_id?: string;
  meter_id: string;
  timestamp_record: string; // ISO datetime string
  meter_kWh: number;
}

export interface MeterRecordBatchRequest {
  tenant_id: number;
  session_id: string;
  encoder_user_id?: number;
  records: MeterRecordInput[];
}

export interface MeterRecordAccepted {
  client_record_id: string;
  meter_record_id: number | null;
  status: string;
}

export interface MeterRecordWarning {
  client_record_id: string;
  type: string;
  message: string;
}

export interface MeterRecordBatchResponse {
  tenant_id: number;
  session_id: string;
  accepted: MeterRecordAccepted[];
  warnings: MeterRecordWarning[];
}

export interface ApprovalInfo {
  name: string;
  signature_blob?: string;
}

export interface ApprovalRequest {
  session_id: string;
  tenant_id: number;
  approver: ApprovalInfo;
}

export interface MeterRecordHistoryItem {
  meter_record_id: number;
  meter_id: string;
  meter_pk: number;
  tenant_id: number;
  session_id: string | null;
  client_record_id: string | null;
  timestamp_record: string;
  meter_kWh: number;
  encoder_user_id: number | null;
  approver_name: string | null;
  approver_signature: string | null;
  created_at: string;
}

export interface MeterRecordHistoryResponse {
  records: MeterRecordHistoryItem[];
}

export const api = {
  /**
   * Get list of all clients
   */
  getClients: async (): Promise<ClientsResponse> => {
    const response = await apiClient.get<ClientsResponse>("/clients");
    return response.data;
  },

  /**
   * Get list of buildings for a client
   */
  getBuildings: async (
    clientToken: string = "NEO"
  ): Promise<BuildingsResponse> => {
    const response = await apiClient.get<BuildingsResponse>("/buildings", {
      params: { client_token: clientToken },
    });
    return response.data;
  },

  /**
   * Get list of tenants for a client
   */
  getTenants: async (clientToken: string = "NEO"): Promise<TenantsResponse> => {
    const response = await apiClient.get<TenantsResponse>("/tenants", {
      params: { client_token: clientToken },
    });
    return response.data;
  },

  /**
   * Generate report for a tenant
   */
  generateReport: async (request: ReportRequest): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/tenant",
      request
    );
    return response.data;
  },

  /**
   * Get floors available for reporting for a specific tenant
   */
  getReportTenantFloors: async (
    clientToken: string,
    tenantToken: string
  ): Promise<TenantFloorsResponse> => {
    const response = await apiClient.get<TenantFloorsResponse>(
      "/tenant/floors",
      { params: { client_token: clientToken, tenant_token: tenantToken } }
    );
    return response.data;
  },

  /**
   * Get units available for reporting for a specific tenant (optional floor filter)
   */
  getReportTenantUnits: async (
    clientToken: string,
    tenantToken: string,
    floor?: number
  ): Promise<TenantUnitsResponse> => {
    const params: Record<string, string | number> = {
      client_token: clientToken,
      tenant_token: tenantToken,
    };
    if (floor !== undefined) {
      params.floor = floor;
    }
    const response = await apiClient.get<TenantUnitsResponse>("/tenant/units", {
      params,
    });
    return response.data;
  },

  /**
   * Generate billing info report for a building (deprecated - use generateBillingInfo)
   */
  generateBuildingBillingInfo: async (
    request: BuildingReportRequest
  ): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/building/billing-info",
      request
    );
    return response.data;
  },

  /**
   * Generate latest records report for a building (deprecated - use generateLastRecords)
   */
  generateBuildingLatestRecords: async (
    request: BuildingReportRequest
  ): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/building/latest-records",
      request
    );
    return response.data;
  },

  /**
   * Generate billing info CSV for a client (uses last 2 records per unit)
   */
  generateBillingInfo: async (
    request: ClientReportRequest
  ): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/generate_billing_info",
      request
    );
    return response.data;
  },

  /**
   * Generate billing comparison CSV for a client.
   */
  generateBillingComparison: async (
    request: ClientReportRequest
  ): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/generate_billing_comparison",
      request
    );
    return response.data;
  },

  /**
   * Generate last records CSV for a client (uses last 1 record per unit)
   */
  generateLastRecords: async (
    request: ClientReportRequest
  ): Promise<ReportResponse> => {
    const response = await apiClient.post<ReportResponse>(
      "/reports/generate_last_records",
      request
    );
    return response.data;
  },

  // Meter Logging API
  /**
   * Get buildings assigned to a user
   */
  getMeterBuildings: async (userId: number): Promise<MeterBuildingsResponse> => {
    const response = await apiClient.get<MeterBuildingsResponse>(
      "/meters/v1/buildings",
      { params: { user_id: userId } }
    );
    return response.data;
  },

  /**
   * Get tenants for a specific building
   */
  getMeterTenantsForBuilding: async (
    buildingId: number
  ): Promise<TenantSummaryResponse> => {
    const response = await apiClient.get<TenantSummaryResponse>(
      `/meters/v1/buildings/${buildingId}/tenants`
    );
    return response.data;
  },

  /**
   * Get floors for a tenant
   */
  getTenantFloors: async (tenantId: number): Promise<FloorsResponse> => {
    const response = await apiClient.get<FloorsResponse>(
      `/meters/v1/tenants/${tenantId}/floors`
    );
    return response.data;
  },

  /**
   * Get meter assignments for a tenant, optionally filtered by floor
   */
  getTenantMeters: async (
    tenantId: number,
    floor?: number
  ): Promise<MeterAssignmentsResponse> => {
    const params = floor !== undefined ? { floor } : {};
    const response = await apiClient.get<MeterAssignmentsResponse>(
      `/meters/v1/tenants/${tenantId}/meters`,
      { params }
    );
    return response.data;
  },

  /**
   * Submit meter records
   */
  submitMeterRecords: async (
    request: MeterRecordBatchRequest
  ): Promise<MeterRecordBatchResponse> => {
    const response = await apiClient.post<MeterRecordBatchResponse>(
      "/meters/v1/records",
      request
    );
    return response.data;
  },

  /**
   * Attach approval to a session
   */
  submitApproval: async (
    request: ApprovalRequest
  ): Promise<{ updated: number }> => {
    const response = await apiClient.post<{ updated: number }>(
      "/meters/v1/approvals",
      request
    );
    return response.data;
  },

  /**
   * Get meter record history
   */
  getMeterRecords: async (
    tenantId?: number,
    meterId?: string,
    fromTimestamp?: string,
    toTimestamp?: string,
    limit: number = 100
  ): Promise<MeterRecordHistoryResponse> => {
    const params: Record<string, string | number> = { limit };
    if (tenantId) params.tenant_id = tenantId;
    if (meterId) params.meter_id = meterId;
    if (fromTimestamp) params.from = fromTimestamp;
    if (toTimestamp) params.to = toTimestamp;

    const response = await apiClient.get<MeterRecordHistoryResponse>(
      "/meters/v1/meter-records",
      { params }
    );
    return response.data;
  },

  /**
   * Get user ID from email address
   */
  getUserIdByEmail: async (
    email: string
  ): Promise<{ user_id: number; email: string }> => {
    const response = await apiClient.get<{ user_id: number; email: string }>(
      "/meters/v1/user-id",
      { params: { email } }
    );
    return response.data;
  },

  /**
   * Get user information (ID, role, entity_id) from email address
   */
  getUserInfoByEmail: async (
    email: string
  ): Promise<{
    user_id: number;
    role: number;
    entity_id: number | null;
    email: string;
    company: string | null;
  }> => {
    const response = await apiClient.get<{
      user_id: number;
      role: number;
      entity_id: number | null;
      email: string;
      company: string | null;
    }>("/meters/v1/user-info", { params: { email } });
    return response.data;
  },
};

export default api;
