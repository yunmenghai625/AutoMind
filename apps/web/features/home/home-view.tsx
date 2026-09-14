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
  { href: "/cockpit", title: "AI Cockpit", desc: "Talk to your car", icon: Gauge },
  { href: "/knowledge", title: "Knowledge RAG", desc: "Ask about your vehicle", icon: Database },
  { href: "/diagnosis", title: "Diagnosis", desc: "Analyze dashboard photos", icon: ScanSearch },
  { href: "/garage", title: "Garage", desc: "Vehicle health & recalls", icon: CarFront },
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
                Production-grade LLMOps for your car
              </Badge>
            </div>
            <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Your AI.
              <br />
              Your Car.
              <br />
              Your Journey.
            </h1>
            <p className="text-base text-muted-foreground">
              An intelligent automotive AI platform powered by Agent, RAG,
              Multimodal AI and Vehicle Digital Twin — orchestrated like a real
              production system.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/cockpit">
                  Launch Cockpit <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/architecture">Explore Architecture</Link>
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
          <h2 className="text-xl font-semibold">Capabilities</h2>
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
        <h2 className="mb-6 text-xl font-semibold">Explore</h2>
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
