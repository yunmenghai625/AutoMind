import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import type {
  AdminMetrics,
  AdminOverview,
  AgentRun,
  AgentRunDetail,
  AgentSafetyEvent,
  SystemComponent,
} from "@/types/agent";

/**
 * Admin services.
 * Live mode uses the administrator-protected production metrics and trace APIs.
 * Mock mode remains available for standalone interface development.
 */

export async function getAdminOverview(): Promise<AdminOverview> {
  if (API_MODE === "live") {
    return http<AdminOverview>("/api/v1/admin/overview", { headers: authHeaders() });
  }
  const { MOCK_ADMIN_OVERVIEW } = await import("@/lib/mock/metrics");
  return simulate(() => ({ ...MOCK_ADMIN_OVERVIEW, generatedAt: new Date().toISOString() }));
}

export async function getAdminMetrics(): Promise<AdminMetrics> {
  if (API_MODE === "live") {
    return http<AdminMetrics>("/api/v1/admin/metrics", { headers: authHeaders() });
  }
  const { MOCK_ADMIN_METRICS } = await import("@/lib/mock/metrics");
  return simulate(() => MOCK_ADMIN_METRICS);
}

export async function getAgentRuns(): Promise<AgentRun[]> {
  if (API_MODE === "live") {
    return http<AgentRun[]>("/api/v1/admin/agent-runs", { headers: authHeaders() });
  }
  const { MOCK_AGENT_RUNS } = await import("@/lib/mock/metrics");
  return simulate(() => MOCK_AGENT_RUNS);
}

export async function getAgentRunDetailById(
  id: string,
): Promise<AgentRunDetail | null> {
  if (API_MODE === "live") {
    return http<AgentRunDetail>(`/api/v1/admin/agent-runs/${id}`, {
      headers: authHeaders(),
    });
  }
  const { getAgentRunDetail } = await import("@/lib/mock/metrics");
  return simulate(() => getAgentRunDetail(id), 200);
}

export async function getSystemComponents(): Promise<SystemComponent[]> {
  if (API_MODE === "live") {
    return http<SystemComponent[]>("/api/v1/admin/components", { headers: authHeaders() });
  }
  const { MOCK_SYSTEM_COMPONENTS } = await import("@/lib/mock/metrics");
  return simulate(() => MOCK_SYSTEM_COMPONENTS);
}

export async function getSafetyEvents(): Promise<AgentSafetyEvent[]> {
  if (API_MODE === "live") {
    return http<AgentSafetyEvent[]>("/api/v1/admin/safety-events", {
      headers: authHeaders(),
    });
  }
  return simulate(() => []);
}
