"use client";

import { Activity, CheckCircle2, Clock, Server, ShieldCheck } from "lucide-react";
import * as React from "react";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { MOCK_SYSTEM_COMPONENTS } from "@/lib/mock/metrics";
import type { SystemComponent } from "@/types/agent";

const STATUS_TONE: Record<SystemComponent["status"], "success" | "warning" | "destructive"> = {
  operational: "success",
  degraded: "warning",
  down: "destructive",
};

const STATUS_LABEL: Record<SystemComponent["status"], string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
};

const INCIDENTS = [
  {
    id: "inc_1",
    title: "No incidents reported in the last 90 days.",
    status: "resolved",
    note: "All systems remain healthy.",
  },
  {
    id: "inc_2",
    title: "Scheduled maintenance window (demo)",
    status: "maintenance",
    note: "Planned for demonstration purposes only.",
  },
];

export function StatusView() {
  const [components] = React.useState<SystemComponent[]>(MOCK_SYSTEM_COMPONENTS);
  const allOperational = components.every((c) => c.status === "operational");

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6">
      <PageHeader
        title="System Status"
        description="Real-time service health for the AutoMind platform."
      />

      <Card className="mt-6 overflow-hidden">
        <div className="flex flex-col items-center gap-3 p-8 text-center">
          <span
            className={`flex h-14 w-14 items-center justify-center rounded-full ${
              allOperational ? "bg-success/15 text-success" : "bg-warning/15 text-warning"
            }`}
          >
            <ShieldCheck className="h-7 w-7" />
          </span>
          <h2 className="text-xl font-semibold">All Systems Operational</h2>
          <p className="text-sm text-muted-foreground">
            AutoMind services are running normally. Uptime over the last 90 days:{" "}
            <span className="font-medium text-foreground">99.98%</span>
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Badge variant="success" className="text-[11px]">
              <CheckCircle2 className="h-3 w-3" />
              Operational
            </Badge>
            <Badge variant="outline" className="text-[11px]">
              <Clock className="h-3 w-3" />
              Updated just now
            </Badge>
          </div>
        </div>
      </Card>

      <Card className="mt-6">
        <div className="flex items-center gap-2 border-b px-5 py-3">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">Components</h3>
        </div>
        <div className="divide-y">
          {components.map((c) => (
            <div key={c.name} className="flex items-center justify-between gap-3 px-5 py-3.5">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Server className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-medium">{c.name}</p>
                  <p className="text-[11px] text-muted-foreground">{c.detail}</p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="hidden text-[11px] tabular-nums text-muted-foreground sm:inline">
                  {c.latencyMs}ms
                </span>
                <Badge variant={STATUS_TONE[c.status]} className="text-[10px]">
                  {STATUS_LABEL[c.status]}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="mt-6">
        <div className="flex items-center gap-2 border-b px-5 py-3">
          <Clock className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">Incident History</h3>
        </div>
        <div className="space-y-2 p-5">
          {INCIDENTS.map((inc) => (
            <div key={inc.id} className="flex items-start gap-3 rounded-lg border bg-card p-3">
              <span
                className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                  inc.status === "resolved" ? "bg-success" : "bg-accent"
                }`}
              />
              <div>
                <p className="text-sm font-medium">{inc.title}</p>
                <p className="text-xs text-muted-foreground">{inc.note}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
