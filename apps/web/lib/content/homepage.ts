/** Static product copy. These values describe capabilities and architecture, not runtime metrics. */

export const CORE_CAPABILITIES = [
  { icon: "CarFront", title: "AI 智能座舱", description: "通过自然语言与车辆对话，并安全控制座舱功能。" },
  { icon: "Layers", title: "车辆数字孪生", description: "实时映射车速、空调、电池和车窗等车辆状态。" },
  { icon: "Database", title: "汽车知识 RAG", description: "基于车辆手册、使用指南和维修资料提供可追溯回答。" },
  { icon: "ScanSearch", title: "多模态智能诊断", description: "上传仪表照片，快速获得结构化故障诊断建议。" },
  { icon: "ShieldCheck", title: "智能体安全防护", description: "通过安全门拦截行驶中开门等高风险车辆操作。" },
  { icon: "Activity", title: "生产级可观测性", description: "使用 OpenTelemetry 与 Grafana 观测服务链路和运行状态。" },
] as const;

export const PLATFORM_STACK = [
  { label: "前端", value: "Next.js", icon: "Layers" },
  { label: "API", value: "FastAPI", icon: "Activity" },
  { label: "数据层", value: "PostgreSQL + Redis", icon: "Database" },
  { label: "可观测性", value: "OpenTelemetry", icon: "ShieldCheck" },
] as const;

export const ARCHITECTURE_FLOW = [
  "用户",
  "AutoMind",
  "监督智能体",
  "座舱 / RAG / 诊断 / 车辆智能体",
  "工具层",
  "车辆数字孪生",
] as const;
