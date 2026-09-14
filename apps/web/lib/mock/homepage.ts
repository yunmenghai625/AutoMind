/** Landing page mock content. */

export const CORE_CAPABILITIES = [
  {
    icon: "CarFront",
    title: "AI 智能座舱",
    description:
      "通过自然语言与车辆对话，并安全控制座舱功能。",
  },
  {
    icon: "Layers",
    title: "车辆数字孪生",
    description:
      "实时映射车速、空调、电池和车窗等车辆状态。",
  },
  {
    icon: "Database",
    title: "汽车知识 RAG",
    description:
      "基于车辆手册、使用指南和维修资料提供可追溯回答。",
  },
  {
    icon: "ScanSearch",
    title: "多模态智能诊断",
    description:
      "上传仪表照片，快速获得结构化故障诊断建议。",
  },
  {
    icon: "ShieldCheck",
    title: "智能体安全防护",
    description:
      "通过安全门拦截行驶中开门等高风险车辆操作。",
  },
  {
    icon: "Activity",
    title: "生产级可观测性",
    description:
      "覆盖智能体链路、延迟预算和 AI 成本的生产级监控。",
  },
] as const;

export const HERO_METRICS = [
  { label: "智能体成功率", value: "96.2%", icon: "CheckCircle2" },
  { label: "工具调用成功率", value: "97.4%", icon: "Wrench" },
  { label: "P95 延迟", value: "1.8 秒", icon: "Timer" },
  { label: "已支持工具", value: "12", icon: "Blocks" },
] as const;

export const ARCHITECTURE_FLOW = [
  "用户",
  "AutoMind",
  "监督智能体",
  "座舱 / RAG / 诊断 / 车辆智能体",
  "工具层",
  "车辆数字孪生",
] as const;
