"use client";

import {
  ArrowDown,
  Bot,
  BrainCircuit,
  CarFront,
  Cloud,
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
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SYSTEM_LAYERS = [
  {
    title: "前端应用",
    desc: "Next.js · TypeScript · Tailwind · shadcn/ui · Framer Motion",
    icon: Layers,
  },
  {
    title: "FastAPI",
    desc: "REST + SSE 流式网关 · `/api/v1/*` 接口契约",
    icon: Server,
  },
  {
    title: "LangGraph",
    desc: "有状态智能体编排 · 监督智能体路由",
    icon: GitBranch,
  },
  {
    title: "智能体层",
    desc: "座舱 · 知识 RAG · 诊断 · 车辆",
    icon: Bot,
  },
  {
    title: "工具层",
    desc: "set_temperature · door_lock · knowledge_search · vision_model",
    icon: FileSearch,
  },
  {
    title: "数据层",
    desc: "PostgreSQL · pgvector · Redis · 对象存储",
    icon: Database,
  },
];

const AGENTS = [
  {
    name: "监督智能体",
    icon: BrainCircuit,
    desc: "识别用户意图、路由至对应智能体并执行安全策略。",
    accent: true,
  },
  {
    name: "座舱智能体",
    icon: Gauge,
    desc: "通过自然语言控制实时车辆数字孪生。",
  },
  {
    name: "知识智能体",
    icon: FileSearch,
    desc: "通过 RAG 与重排序，依据手册生成可追溯回答。",
  },
  {
    name: "诊断智能体",
    icon: ScanSearch,
    desc: "根据仪表图片执行多模态故障识别。",
  },
  {
    name: "车辆智能体",
    icon: CarFront,
    desc: "提供数字孪生状态读写、召回与 VIN 服务。",
  },
];

const DATA_LAYERS = [
  { name: "PostgreSQL", icon: Container, note: "认证 · 车辆 · 智能体运行记录" },
  { name: "pgvector", icon: Database, note: "RAG 向量嵌入存储" },
  { name: "Redis", icon: HardDrive, note: "会话 · 限流 · 缓存" },
  { name: "对象存储", icon: Cloud, note: "诊断图片 · 生成资产" },
];

const INFRA = [
  { name: "Vercel", icon: Cloud, note: "Next.js 前端托管" },
  { name: "Railway", icon: Server, note: "FastAPI 容器托管" },
  { name: "Railway PostgreSQL", icon: Database, note: "PostgreSQL 与 pgvector" },
  { name: "Railway Redis", icon: HardDrive, note: "限流、会话与缓存" },
  { name: "Railway Bucket", icon: Container, note: "S3 兼容对象存储" },
  { name: "Grafana Cloud", icon: ShieldCheck, note: "OpenTelemetry 可观测性" },
  { name: "GitHub Actions", icon: GitBranch, note: "持续集成与部署" },
];

const fade = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
};

export function ArchitectureView() {
  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="技术架构"
        description="展示 AutoMind 前端、智能体运行时与数据层之间的协作关系。"
      />

      {/* System architecture flow */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3 }}
        className="mt-6"
        aria-label="系统架构分层"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
          系统架构
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
        aria-label="智能体架构"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
          智能体架构
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
          监督智能体负责请求路由与上下文维护，每次工具调用在执行前都必须通过安全防护校验。
        </p>
      </motion.section>

      {/* Data layer */}
      <motion.section
        {...fade}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="mt-10"
        aria-label="数据层"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">数据层</h2>
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
        aria-label="基础设施"
      >
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">基础设施</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
            每次工具调用均经过安全防护
          </Badge>
          <Badge variant="outline" className="text-xs">
            已预留 SSE 流式通道
          </Badge>
          <Badge variant="outline" className="text-xs">
            公开环境强制连接在线 API
          </Badge>
        </div>
      </motion.section>
    </div>
  );
}
