/**
 * Central runtime configuration.
 *
 * The app boots in full Mock mode by default (`NEXT_PUBLIC_API_MODE=mock`).
 * Switching to `live` makes every API Service Layer call hit the real
 * FastAPI backend instead — no UI changes required.
 */

export type ApiMode = "mock" | "live";

export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME ?? "AutoMind";

export const APP_TAGLINE =
  process.env.NEXT_PUBLIC_APP_TAGLINE ??
  "Production Automotive AI Cockpit Platform";

export const API_MODE: ApiMode =
  process.env.NEXT_PUBLIC_API_MODE === "live" ? "live" : "mock";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const IS_MOCK = API_MODE === "mock";
