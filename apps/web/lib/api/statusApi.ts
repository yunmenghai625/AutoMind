import { http, simulate } from "@/lib/api/apiClient";
import { API_MODE } from "@/lib/config";

export interface HealthDependency {
  status: "ok" | "unavailable" | "disabled";
  detail?: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  dependencies: Record<string, HealthDependency>;
}

export interface HealthSnapshot {
  health: HealthResponse;
  latencyMs: number;
}

export async function getHealthSnapshot(): Promise<HealthSnapshot> {
  if (API_MODE === "mock") {
    return simulate(() => ({
      health: {
        status: "ok",
        service: "automind-api-local",
        version: "dev",
        environment: "development",
        timestamp: new Date().toISOString(),
        dependencies: { database: { status: "ok" } },
      },
      latencyMs: 0,
    }));
  }

  const startedAt = performance.now();
  const health = await http<HealthResponse>("/health");
  return { health, latencyMs: Math.max(1, Math.round(performance.now() - startedAt)) };
}
