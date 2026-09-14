import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";

export async function saveFeedback(
  runId: string,
  rating: -1 | 1,
): Promise<void> {
  if (API_MODE === "mock") return simulate(() => undefined, 120);
  await http("/api/v1/feedback", {
    method: "POST",
    headers: authHeaders(),
    body: { run_id: runId, rating },
  });
}
