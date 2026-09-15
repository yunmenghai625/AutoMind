/**
 * Central runtime configuration.
 *
 * Mock mode is available only during local development. Production builds
 * always fail closed to the live API so sample data can never be presented as
 * production telemetry when an environment variable is missing.
 */

export type ApiMode = "mock" | "live";

export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME ?? "AutoMind";

export const APP_TAGLINE =
  process.env.NEXT_PUBLIC_APP_TAGLINE ??
  "生产级汽车智能座舱平台";

export const API_MODE: ApiMode =
  process.env.NODE_ENV !== "production" &&
  process.env.NEXT_PUBLIC_API_MODE === "mock"
    ? "mock"
    : "live";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const IS_MOCK = API_MODE === "mock";
