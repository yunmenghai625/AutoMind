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
  operational: "运行正常",
  degraded: "服务降级",
  down: "服务中断",
};

const INCIDENTS = [
  {
    id: "inc_1",
    title: "最近 90 天未报告服务事故。",
    status: "resolved",
    note: "所有系统保持健康运行。",
  },
  {
    id: "inc_2",
    title: "计划维护窗口（演示）",
    status: "maintenance",
    note: "仅用于演示计划维护信息。",
  },
];

export function StatusView() {
  const [components] = React.useState<SystemComponent[]>(MOCK_SYSTEM_COMPONENTS);
  const allOperational = components.every((c) => c.status === "operational");

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6">
      <PageHeader
        title="系统状态"
        description="实时查看 AutoMind 平台各项服务的健康状态。"
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
          <h2 className="text-xl font-semibold">所有系统运行正常</h2>
          <p className="text-sm text-muted-foreground">
            AutoMind 服务当前运行正常，最近 90 天可用率：{" "}
            <span className="font-medium text-foreground">99.98%</span>
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Badge variant="success" className="text-[11px]">
              <CheckCircle2 className="h-3 w-3" />
              运行正常
            </Badge>
            <Badge variant="outline" className="text-[11px]">
              <Clock className="h-3 w-3" />
              刚刚更新
            </Badge>
          </div>
        </div>
      </Card>

      <Card className="mt-6">
        <div className="flex items-center gap-2 border-b px-5 py-3">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">服务组件</h3>
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
          <h3 className="text-sm font-semibold">事故记录</h3>
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
