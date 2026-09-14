"use client";

import {
  ArrowDown,
  Bot,
  BrainCircuit,
  CarFront,
  Cloud,
  CloudCog,
  Container,
  Database,
  FileSearch,
  Gauge,
  GitBranch,
  HardDrive,
  Layers,
  ScanSearch,
  Server,
  ShieldCheck,
} from "lucide-react";
import { motion } from "framer-motion";
import { MockBadge } from "@/components/common/mock-badge";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SYSTEM_LAYERS = [
  {
    title: "Frontend",
    desc: "Next.js · TypeScript · Tailwind · shadcn/ui · Framer Motion",
    icon: Layers,
  },
  {
    title: "FastAPI",
    desc: "REST + SSE streaming gateway · `/api/v1/*` contract",
    icon: Server,
  },
  {
    title: "LangGraph",
    desc: "Stateful agent orchestration · supervisor routing",
    icon: GitBranch,
  },
  {
    title: "Agents",
    desc: "Cockpit · Knowledge RAG · Diagnosis · Vehicle",
    icon: Bot,
  },
  {
    title: "Tools",
    desc: "set_temperature · door_lock · knowledge_search · vision_model",
    icon: FileSearch,
  },
  {
    title: "Data",
    desc: "PostgreSQL · pgvector · Redis · Object Storage",
    icon: Database,
  },
];

const AGENTS = [
  {
    name: "Supervisor",
    icon: BrainCircuit,
    desc: "Classifies intent, routes to the right agent and enforces safety policies.",
    accent: true,
  },
  {
    name: "Cockpit",
    icon: Gauge,
    desc: "Natural-language vehicle control against the live digital twin.",
  },
  {
    name: "Knowledge",
    icon: FileSearch,
    desc: "Grounded answers over manuals via RAG + reranking.",
  },
  {
    name: "Diagnosis",
    icon: ScanSearch,
    desc: "Multimodal fault detection from dashboard imagery.",
  },
  {
    name: "Vehicle",
    icon: CarFront,
    desc: "State read/write, recall & VIN services for the twin.",
  },
];

const DATA_LAYERS = [
  { name: "PostgreSQL", icon: Container, note: "Auth · vehicles · agent runs" },
  { name: "pgvector", icon: Database, note: "Embedding store for RAG" },
  { name: "Redis", icon: HardDrive, note: "Session · rate limits · cache" },
  { name: "Object Storage", icon: Cloud, note: "Diagnosis images · assets" },
];

const INFRA = [
  { name: "Cloudflare", icon: CloudCog, note: "CDN & edge" },
  { name: "Railway", icon: Server, note: "API hosting" },
  { name: "Supabase", icon: Cloud, note: "Postgres + auth" },
  { name: "Upstash", icon: Container, note: "Serverless Redis" },
  { name: "Grafana", icon: ShieldCheck, note: "Observability" },
  { name: "GitHub Actions", icon: GitBranch, note: "CI/CD" },
];

const fade = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
};

export function ArchitectureView() {
  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="System Architecture"
        badge={<MockBadge />}
        description="How the AutoMind frontend, agent runtime and data plane fit together."
      />

      {/* System architecture flow */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3 }}
        className="mt-6"
        aria-label="System architecture layers"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
          System Architecture
        </h2>
        <div className="space-y-1">
          {SYSTEM_LAYERS.map((layer, i) => (
            <div key={layer.title} className="space-y-1">
              <Card className="border-primary/15 bg-gradient-to-r from-primary/5 to-transparent transition-colors hover:border-primary/40">
                <CardContent className="flex items-center gap-3 p-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <layer.icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{layer.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{layer.desc}</p>
                  </div>
                  <span className="ml-auto rounded-md bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                    L{i + 1}
                  </span>
                </CardContent>
              </Card>
              {i < SYSTEM_LAYERS.length - 1 && (
                <div className="flex justify-center py-0.5 text-muted-foreground/50" aria-hidden="true">
                  <ArrowDown className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}
        </div>
      </motion.section>

      {/* Agent architecture */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="mt-10"
        aria-label="Agent architecture"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
          Agent Architecture
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {AGENTS.map((agent, i) => (
            <Card
              key={agent.name}
              className={
                agent.accent
                  ? "border-primary/40 bg-primary/5 lg:col-span-1"
                  : "transition-colors hover:border-primary/40"
              }
            >
              <CardHeader className="pb-2">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    agent.accent ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
                  }`}
                >
                  <agent.icon className="h-5 w-5" />
                </span>
                <CardTitle className="pt-2 text-sm">{agent.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{agent.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="mt-3 text-center text-[11px] text-muted-foreground/70">
          Supervisor routes requests, maintains context, and gates every tool call
          through the Safety Guard before execution.
        </p>
      </motion.section>

      {/* Data layer */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="mt-10"
        aria-label="Data layer"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">Data Layer</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {DATA_LAYERS.map((d) => (
            <Card key={d.name} className="transition-colors hover:border-primary/40">
              <CardContent className="flex items-start gap-3 pt-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <d.icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{d.name}</p>
                  <p className="text-xs text-muted-foreground">{d.note}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </motion.section>

      {/* Infrastructure */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3, delay: 0.15 }}
        className="mt-10 pb-2"
        aria-label="Infrastructure"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">Infrastructure</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {INFRA.map((f) => (
            <Card key={f.name} className="transition-colors hover:border-primary/40">
              <CardContent className="flex items-center gap-3 pt-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <f.icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{f.name}</p>
                  <p className="text-xs text-muted-foreground">{f.note}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">
            Safety Guard on every tool call
          </Badge>
          <Badge variant="outline" className="text-xs">
            SSE streaming paths reserved
          </Badge>
          <Badge variant="outline" className="text-xs">
            Mock ↔ Live API toggle ready
          </Badge>
        </div>
      </motion.section>
    </div>
  );
}
