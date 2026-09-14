import type {
  AdminOverview,
  AdminMetrics,
  AgentRun,
  AgentRunDetail,
  AgentStep,
  SystemComponent,
} from "@/types/agent";

export const MOCK_ADMIN_OVERVIEW: AdminOverview = {
  users: 187,
  requests: 3421,
  testRequests: 0,
  agentSuccessRate: 96.2,
  p95Latency: 1.82,
  toolSuccessRate: 97.4,
  aiCost: 8.43,
  generatedAt: new Date().toISOString(),
};

function generateTraffic(days = 14) {
  const out = [];
  const now = Date.now();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now - i * 86400000);
    const weekday = d.getUTCDay();
    const base = weekday === 0 || weekday === 6 ? 120 : 260;
    const jitter = Math.round(Math.sin(i * 1.7) * 70 + Math.random() * 40);
    out.push({
      timestamp: d.toISOString().slice(0, 10),
      requests: Math.max(60, base + jitter),
      testRequests: 0,
      agentSuccessRate: Math.min(
        100,
        Math.max(88, 97 - Math.round(Math.random() * 3)),
      ),
    });
  }
  return out;
}

function generateUsage() {
  return [
    { agent: "Cockpit" as const, calls: 1820 },
    { agent: "Knowledge" as const, calls: 640 },
    { agent: "Diagnosis" as const, calls: 275 },
    { agent: "Vehicle" as const, calls: 686 },
  ];
}

function generateDailyCost() {
  const out = [];
  const now = Date.now();
  for (let i = 9; i >= 0; i--) {
    const d = new Date(now - i * 86400000);
    out.push({
      date: d.toISOString().slice(0, 10).slice(5),
      cost: Math.round((1.2 + Math.random() * 3.4) * 100) / 100,
    });
  }
  return out;
}

function generateLatency() {
  const out = [];
  const now = Date.now();
  for (let i = 9; i >= 0; i--) {
    const d = new Date(now - i * 86400000);
    out.push({
      date: d.toISOString().slice(0, 10).slice(5),
      p50: Math.round((0.7 + Math.random() * 0.5) * 100) / 100,
      p95: Math.round((1.4 + Math.random() * 0.8) * 100) / 100,
      p99: Math.round((2.4 + Math.random() * 1.4) * 100) / 100,
    });
  }
  return out;
}

export const MOCK_ADMIN_METRICS: AdminMetrics = {
  traffic: generateTraffic(),
  usage: generateUsage(),
  dailyCost: generateDailyCost(),
  latency: generateLatency(),
};

export const MOCK_AGENT_RUNS: AgentRun[] = [
  {
    id: "run_a91f2c",
    agent: "Cockpit",
    latencyMs: 748,
    steps: 6,
    toolsUsed: ["set_temperature", "set_seat_heating"],
    status: "success",
    time: new Date(Date.now() - 12 * 60000).toISOString(),
  },
  {
    id: "run_b73d01",
    agent: "Knowledge",
    latencyMs: 1230,
    steps: 5,
    toolsUsed: ["knowledge_search", "rerank"],
    status: "success",
    time: new Date(Date.now() - 47 * 60000).toISOString(),
  },
  {
    id: "run_c22e88",
    agent: "Diagnosis",
    latencyMs: 2104,
    steps: 8,
    toolsUsed: ["vision_model", "warning_detect", "knowledge_retrieval"],
    status: "success",
    time: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: "run_d1f0ab",
    agent: "Cockpit",
    latencyMs: 312,
    steps: 4,
    toolsUsed: ["door_unlock"],
    status: "blocked",
    time: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
  {
    id: "run_e884c3",
    agent: "Vehicle",
    latencyMs: 189,
    steps: 3,
    toolsUsed: ["get_vehicle_state"],
    status: "success",
    time: new Date(Date.now() - 5 * 3600000).toISOString(),
  },
  {
    id: "run_f9027a",
    agent: "Knowledge",
    latencyMs: 4310,
    steps: 7,
    toolsUsed: ["knowledge_search"],
    status: "failed",
    time: new Date(Date.now() - 8 * 3600000).toISOString(),
  },
  {
    id: "run_ab12cd",
    agent: "Cockpit",
    latencyMs: 965,
    steps: 5,
    toolsUsed: ["set_climate"],
    status: "success",
    time: new Date(Date.now() - 26 * 3600000).toISOString(),
  },
];

export function buildTrace(runId: string): AgentStep[] {
  const base: AgentStep[] = [
    { name: "接收请求", durationMs: 8, detail: "POST /api/v1/chat" },
    { name: "意图路由", durationMs: 22, detail: "已匹配监督智能体路由" },
    { name: "加载上下文", durationMs: 13, detail: "已加载会话与车辆数字孪生" },
  ];
  if (runId === "run_d1f0ab") {
    base.push(
      { name: "座舱智能体", durationMs: 420, detail: "规划车门解锁操作" },
      { name: "安全防护", durationMs: 4, detail: "已拦截：车辆速度大于 0" },
    );
    return base;
  }
  if (runId === "run_f9027a") {
    base.push(
      { name: "知识智能体", durationMs: 3900, detail: "向量检索超时" },
    );
    return base;
  }
  base.push(
    { name: "座舱智能体", durationMs: 420, detail: "规划并调用工具" },
    { name: "安全防护", durationMs: 4, detail: "策略校验通过" },
    { name: "工具执行", durationMs: 9, detail: "已作用于车辆数字孪生" },
    { name: "生成响应", durationMs: 280, detail: "已完成流式响应组装" },
  );
  return base;
}

let traceCache = new Map<string, AgentStep[]>();

export function getAgentRunDetail(runId: string): AgentRunDetail | null {
  const run = MOCK_AGENT_RUNS.find((r) => r.id === runId);
  if (!run) return null;
  if (!traceCache.has(runId)) traceCache.set(runId, buildTrace(runId));
  const trace = traceCache.get(runId)!;
  return {
    ...run,
    query:
      run.agent === "Cockpit"
        ? "我有点冷，请打开主驾座椅加热"
        : run.agent === "Knowledge"
          ? "胎压报警灯亮了还能继续开吗？"
          : run.agent === "Diagnosis"
            ? "[上传仪表警告照片]"
            : "获取车辆状态",
    trace,
  };
}

export const MOCK_SYSTEM_COMPONENTS: SystemComponent[] = [
  { name: "Web 前端", status: "operational", latencyMs: 182, detail: "边缘网络运行正常" },
  { name: "API 服务", status: "operational", latencyMs: 210, detail: "FastAPI 服务正常" },
  { name: "数据库", status: "operational", latencyMs: 45, detail: "PostgreSQL 运行正常" },
  { name: "向量检索", status: "operational", latencyMs: 87, detail: "pgvector 连接正常" },
  { name: "AI 模型服务", status: "operational", latencyMs: 620, detail: "模型端点响应正常" },
  { name: "对象存储", status: "operational", latencyMs: 34, detail: "对象存储运行正常" },
];
