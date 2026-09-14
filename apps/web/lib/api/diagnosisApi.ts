import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import { mockDiagnosis } from "@/lib/mock/diagnosis";
import type { DiagnosisResult } from "@/types/diagnosis";

/**
 * POST /api/v1/diagnosis
 * Sends multipart image data to the Phase 4 diagnosis workflow in live mode.
 */
export async function runDiagnosis(file: File): Promise<DiagnosisResult> {
  if (API_MODE !== "live") {
    return simulate(() => mockDiagnosis(file.name), 1800);
  }
  const form = new FormData();
  form.append("file", file);
  return http<DiagnosisResult>("/api/v1/diagnosis", {
    method: "POST",
    body: form,
    headers: authHeaders(),
  });
}
