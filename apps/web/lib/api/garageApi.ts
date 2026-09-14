import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import { MOCK_GARAGE_VEHICLE, MOCK_RECALLS } from "@/lib/mock/garage";
import type { GarageVehicle, RecallRecord } from "@/types/vehicle";

/**
 * Garage services.
 * GET /api/v1/garage/vehicle, GET /api/v1/vehicle/recalls (future backend).
 */

export async function getGarageVehicle(): Promise<GarageVehicle> {
  if (API_MODE === "live") {
    return http<GarageVehicle>("/api/v1/garage/vehicle", {
      headers: authHeaders(),
    });
  }
  return simulate(() => MOCK_GARAGE_VEHICLE);
}

export interface RecallResult {
  recalls: RecallRecord[];
  status: "success" | "cached" | "degraded" | "unavailable";
  cached: boolean;
}

export async function getRecalls(): Promise<RecallResult> {
  if (API_MODE === "live") {
    return http<RecallResult>(
      "/api/v1/vehicle/recalls",
      { headers: authHeaders() },
    );
  }
  return simulate(() => ({ recalls: MOCK_RECALLS, status: "success", cached: false }));
}
