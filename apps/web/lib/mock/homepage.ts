/** Landing page mock content. */

export const CORE_CAPABILITIES = [
  {
    icon: "CarFront",
    title: "AI Cockpit",
    description:
      "Natural-language driving companion that talks to and controls your vehicle.",
  },
  {
    icon: "Layers",
    title: "Vehicle Digital Twin",
    description:
      "A live, real-time model of your car — speed, climate, battery and windows.",
  },
  {
    icon: "Database",
    title: "Automotive RAG",
    description:
      "Grounds every answer in your manuals, guides and service documentation.",
  },
  {
    icon: "ScanSearch",
    title: "Multimodal Diagnosis",
    description:
      "Upload a dashboard photo and get a structured fault diagnosis in seconds.",
  },
  {
    icon: "ShieldCheck",
    title: "Agent Safety",
    description:
      "A safety guard that blocks risky actions like opening doors while driving.",
  },
  {
    icon: "Activity",
    title: "Production Observability",
    description:
      "Agent traces, latency budgets and AI cost monitoring — production-grade.",
  },
] as const;

export const HERO_METRICS = [
  { label: "Agent Success Rate", value: "96.2%", icon: "CheckCircle2" },
  { label: "Tool Success Rate", value: "97.4%", icon: "Wrench" },
  { label: "P95 Latency", value: "1.8s", icon: "Timer" },
  { label: "Supported Tools", value: "12", icon: "Blocks" },
] as const;

export const ARCHITECTURE_FLOW = [
  "User",
  "AutoMind",
  "Supervisor",
  "Cockpit / RAG / Diagnosis / Vehicle",
  "Tools",
  "Vehicle Digital Twin",
] as const;
