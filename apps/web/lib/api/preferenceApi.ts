import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import type { PreferencesState } from "@/types/preferences";

export async function getPreferences(): Promise<PreferencesState> {
  if (API_MODE === "mock") {
    throw new Error("模拟模式下偏好设置保存在本地。 ");
  }
  return http<PreferencesState>("/api/v1/preferences", {
    headers: authHeaders(),
  });
}

export async function savePreferences(
  preferences: PreferencesState,
): Promise<PreferencesState> {
  if (API_MODE === "mock") return simulate(() => preferences);
  return http<PreferencesState>("/api/v1/preferences", {
    method: "PUT",
    headers: authHeaders(),
    body: preferences,
  });
}

export async function deletePreferences(): Promise<void> {
  if (API_MODE === "mock") return simulate(() => undefined);
  await http<{ deleted: boolean }>("/api/v1/preferences", {
    method: "DELETE",
    headers: authHeaders(),
  });
}
