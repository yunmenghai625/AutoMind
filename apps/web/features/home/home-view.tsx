"use client";

import {
  Activity,
  ArrowRight,
  Blocks,
  CarFront,
  CheckCircle2,
  Database,
  Gauge,
  Layers,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Timer,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { MockBadge } from "@/components/common/mock-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ARCHITECTURE_FLOW, CORE_CAPABILITIES, HERO_METRICS } from "@/lib/mock/homepage";

const ICONS: Record<string, LucideIcon> = {
  CarFront,
  Layers,
  Database,
  ScanSearch,
  ShieldCheck,
  Activity,
  CheckCircle2,
  Wrench,
  Timer,
  Blocks,
};

const EXPLORE = [
  { href: "/cockpit", title: "智能座舱", desc: "用自然语言控制车辆", icon: Gauge },
  { href: "/knowledge", title: "汽车知识库", desc: "查询车辆使用与养护知识", icon: Database },
  { href: "/diagnosis", title: "智能诊断", desc: "分析仪表与警告灯照片", icon: ScanSearch },
  { href: "/garage", title: "我的车库", desc: "查看车辆健康与召回信息", icon: CarFront },
];

export function HomeView() {
  return (
    <div className="relative overflow-hidden">
      {/* Hero */}
      <section className="container mx-auto max-w-7xl px-4 pt-16 pb-10">
        <div className="flex flex-col items-start gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl space-y-5">
            <div className="inline-flex items-center gap-2">
              <Badge className="border-primary/40 bg-primary/10 text-primary">
                <Sparkles className="h-3 w-3" />
                面向汽车场景的生产级 LLMOps
              </Badge>
            </div>
            <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              你的智能，
              <br />
              你的爱车，
              <br />
              你的旅程。
            </h1>
            <p className="text-base text-muted-foreground">
              融合智能体、RAG、多模态 AI 与车辆数字孪生，按照真实生产系统标准构建的汽车智能平台。
            </p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/cockpit">
                  进入智能座舱 <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/architecture">查看技术架构</Link>
              </Button>
            </div>
          </div>

          <div className="grid w-full max-w-md grid-cols-2 gap-3">
            {HERO_METRICS.map((m) => {
              const Icon = ICONS[m.icon] ?? ActivitiesFallback;
              return (
                <div key={m.label} className="rounded-xl border bg-card p-4">
                  <Icon className="h-4 w-4 text-primary" />
                  <p className="mt-2 text-xl font-bold tabular-nums">{m.value}</p>
                  <p className="text-xs text-muted-foreground">{m.label}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Architecture flow */}
      <section className="container mx-auto max-w-7xl px-4 pb-10">
        <Card className="bg-muted/30">
          <CardContent className="flex flex-wrap items-center justify-center gap-1.5 p-5">
            {ARCHITECTURE_FLOW.map((node, i) => (
              <React.Fragment key={node}>
                <span className="rounded-lg border bg-card px-3 py-1.5 text-xs font-medium">
                  {node}
                </span>
                {i < ARCHITECTURE_FLOW.length - 1 && (
                  <ArrowRight className="h-3 w-3 text-muted-foreground/60" />
                )}
              </React.Fragment>
            ))}
          </CardContent>
        </Card>
      </section>

      {/* Capabilities */}
      <section className="container mx-auto max-w-7xl px-4 pb-14">
        <div className="mb-6 flex items-center gap-2">
          <h2 className="text-xl font-semibold">核心能力</h2>
          <MockBadge />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CORE_CAPABILITIES.map((c) => {
            const Icon = ICONS[c.icon] ?? ActivitiesFallback;
            return (
              <Card key={c.title} className="transition-colors hover:border-primary/40">
                <CardHeader className="pb-2">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                  <CardTitle className="pt-2 text-base">{c.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm">{c.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Explore */}
      <section className="container mx-auto max-w-7xl px-4 pb-14">
        <h2 className="mb-6 text-xl font-semibold">开始探索</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {EXPLORE.map((e) => {
            const Icon = e.icon;
            return (
              <Link key={e.href} href={e.href} className="group">
                <Card className="h-full transition-colors group-hover:border-primary/40">
                  <CardContent className="flex items-start gap-3 pt-5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{e.title}</p>
                      <p className="text-xs text-muted-foreground">{e.desc}</p>
                    </div>
                    <ArrowRight className="ml-auto h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function ActivitiesFallback({ className }: { className?: string }) {
  return <Activity className={className} />;
}
