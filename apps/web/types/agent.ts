/** Agent / Trace / Monitoring domain types.
 * Mirror of future admin endpoints:
 * GET /api/v1/admin/overview, /metrics, /agent-runs, /agent-runs/{id}
 */

export interface AdminOverview {
  users: number;
  requests: number;
  testRequests: number;
  agentSuccessRate: number; // %
  p95Latency: number; // seconds
  toolSuccessRate: number; // %
  aiCost: number; // currency (mock ¥)
  generatedAt: string;
}

export type MetricPoint = {
  ts: string;
  value: number;
};

export interface TrafficMetric {
  requests: number;
  testRequests: number;
  agentSuccessRate: number;
  timestamp: string;
}

export interface AgentUsage {
  agent: string;
  calls: number;
}

export interface CostPoint {
  date: string;
  cost: number;
}

export interface LatencyPoint {
  date: string;
  p50: number;
  p95: number;
  p99: number;
}

export interface AdminMetrics {
  traffic: TrafficMetric[];
  usage: AgentUsage[];
  dailyCost: CostPoint[];
  latency: LatencyPoint[];
}

export type AgentRunStatus = "success" | "failed" | "blocked" | "rejected" | "running";

export interface AgentStep {
  name: string;
  durationMs: number;
  detail?: string;
}

export interface AgentRun {
  id: string;
  trafficClass?: "user" | "load_test";
  agent: string;
  latencyMs: number;
  steps: number;
  toolsUsed: string[];
  status: AgentRunStatus;
  time: string;
}

export interface AgentRunDetail extends AgentRun {
  query: string;
  trace: AgentStep[];
}

export type ComponentStatus = "operational" | "degraded" | "down";

export interface SystemComponent {
  name: string;
  status: ComponentStatus;
  latencyMs: number;
  detail: string;
}

export interface AgentSafetyEvent {
  id: string;
  rule: string;
  severity: "info" | "warning" | "blocked";
  message: string;
  at: string;
}
