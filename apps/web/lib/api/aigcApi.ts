import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_BASE_URL, API_MODE } from "@/lib/config";
import type { AppliedCockpitTheme, CockpitTheme } from "@/types/aigc";

function absoluteWallpaper(url: string | null): string | null {
  if (!url || /^https?:\/\//.test(url) || url.startsWith("data:")) return url;
  return `${API_BASE_URL}${url}`;
}

export async function generateCockpitTheme(
  prompt: string,
  regenerate = false,
): Promise<CockpitTheme> {
  if (API_MODE === "mock") {
    return simulate(() => ({
      request_id: "mock-theme-request",
      theme_id: window.crypto.randomUUID(),
      theme_spec: {
        name: "静谧海岸",
        ambient_color: "#123B5D",
        ambient_brightness: 22,
        display_mode: "night" as const,
        music_style: "静谧氛围音乐",
        temperature: 22,
        wallpaper_prompt: prompt,
      },
      wallpaper_url: null,
      metadata: {
        generation_id: window.crypto.randomUUID(),
        provider: "local",
        model: "automind-theme-local-v1",
        image_provider: "mock",
        image_model: "automind-svg-v1",
        latency_ms: 120,
        cost_est_cny: 0,
        image_cost_est_cny: 0,
        status: "success",
        cached: false,
        degraded_reason: null,
        quota_used: 1,
        quota_limit: 1,
        budget_state: "normal" as const,
      },
    }));
  }
  const result = await http<CockpitTheme>("/api/v1/aigc/themes", {
    method: "POST",
    headers: authHeaders(),
    body: { prompt, regenerate },
  });
  return { ...result, wallpaper_url: absoluteWallpaper(result.wallpaper_url) };
}

export async function applyCockpitTheme(
  themeId: string,
): Promise<AppliedCockpitTheme> {
  if (API_MODE === "mock") {
    return simulate(() => ({
      request_id: "mock-apply-request",
      theme_id: themeId,
      applied: true,
      theme_spec: {
        name: "静谧海岸",
        ambient_color: "#123B5D",
        ambient_brightness: 22,
        display_mode: "night" as const,
        music_style: "静谧氛围音乐",
        temperature: 22,
        wallpaper_prompt: "静谧海岸夜景",
      },
      wallpaper_url: null,
      vehicle_state_version: 2,
      agent_run_id: window.crypto.randomUUID(),
    }));
  }
  const state = await http<{ state: { version: number } }>("/api/v1/vehicle/state", {
    headers: authHeaders(),
  });
  const result = await http<AppliedCockpitTheme>(
    `/api/v1/aigc/themes/${themeId}/apply`,
    {
      method: "POST",
      headers: authHeaders(),
      body: { confirmed: true, expected_version: state.state.version },
    },
  );
  return { ...result, wallpaper_url: absoluteWallpaper(result.wallpaper_url) };
}
