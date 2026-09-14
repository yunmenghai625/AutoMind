import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import { mockChatReply } from "@/lib/mock/chat";
import { useVehicleStore } from "@/lib/store/vehicle-store";
import type { SendChatRequest, SendChatResponse } from "@/types/chat";

/**
 * POST /api/v1/chat
 *
 * Unified service used by the Cockpit assistant. In mock mode it mutates the
 * shared Vehicle Store so AI controls and manual controls stay in sync.
 * In live mode it posts to FastAPI and applies the returned vehicle snapshot.
 */
export async function sendChat(
  req: SendChatRequest,
): Promise<SendChatResponse> {
  if (API_MODE === "live") {
    const outcome = await http<SendChatResponse>("/api/v1/chat", {
      method: "POST",
      headers: authHeaders(),
      body: req,
    });
    if (outcome.vehicle) {
      useVehicleStore.getState().setVehicle(outcome.vehicle);
    }
    return outcome;
  }
  return simulate(() => {
    const vehicle = useVehicleStore.getState().vehicle;
    const outcome = mockChatReply(req.message, vehicle);
    useVehicleStore.getState().setVehicle(outcome.nextVehicle);
    return outcome.send;
  }, 500);
}
