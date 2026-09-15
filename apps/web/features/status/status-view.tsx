"use client";

import { Activity, AlertTriangle, CheckCircle2, Clock, Server, ShieldCheck } from "lucide-react";
import * as React from "react";
import { MockBadge } from "@/components/common/mock-badge";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getHealthSnapshot } from "@/lib/api/statusApi";
import { IS_MOCK } from "@/lib/config";
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

const DEPENDENCY_LABELS: Record<string, string> = {
  database: "数据库",
  redis: "Redis",
  storage: "对象存储",
};

export function StatusView() {
  const [components, setComponents] = React.useState<SystemComponent[]>([]);
  const [updatedAt, setUpdatedAt] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    void getHealthSnapshot()
      .then(({ health, latencyMs }) => {
        const dependencies = Object.entries(health.dependencies).map(
          ([name, dependency]): SystemComponent => ({
            name: DEPENDENCY_LABELS[name] ?? name,
            status:
              dependency.status === "ok"
                ? "operational"
                : dependency.status === "disabled"
                  ? "degraded"
                  : "down",
            latencyMs: 0,
            detail:
              dependency.detail ??
              (dependency.status === "disabled" ? "当前环境未启用" : "由 API 健康检查返回"),
          }),
        );

        setComponents([
          { name: "Web 前端", status: "operational", latencyMs: 0, detail: "当前页面已成功加载" },
          {
            name: "AutoMind API",
            status: health.status === "ok" ? "operational" : "degraded",
            latencyMs,
            detail: `${health.service} · v${health.version} · ${health.environment}`,
          },
          ...dependencies,
        ]);
        setUpdatedAt(health.timestamp);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const allOperational = components.length > 0 && components.every((c) => c.status === "operational");

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6">
      <PageHeader
        title="系统状态"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description="展示 AutoMind API 健康检查返回的实时状态。"
      />

      <Card className="mt-6 overflow-hidden">
        <div className="flex flex-col items-center gap-3 p-8 text-center">
          <span
            className={`flex h-14 w-14 items-center justify-center rounded-full ${
              error
                ? "bg-destructive/15 text-destructive"
                : allOperational
                  ? "bg-success/15 text-success"
                  : "bg-warning/15 text-warning"
            }`}
          >
            {error ? <AlertTriangle className="h-7 w-7" /> : <ShieldCheck className="h-7 w-7" />}
          </span>
          <h2 className="text-xl font-semibold">
            {loading
              ? "正在检查系统状态"
              : error
                ? "无法获取实时状态"
                : allOperational
                  ? "系统运行正常"
                  : "部分服务异常"}
          </h2>
          <p className="text-sm text-muted-foreground">
            {error
              ? "API 健康检查当前不可用，请稍后刷新页面重试。"
              : "本页不估算历史可用率，仅展示当前健康检查结果。"}
          </p>
          {!loading && !error && (
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Badge variant={allOperational ? "success" : "warning"} className="text-[11px]">
                <CheckCircle2 className="h-3 w-3" />
                {allOperational ? "运行正常" : "需要关注"}
              </Badge>
              {updatedAt && (
                <Badge variant="outline" className="text-[11px]">
                  <Clock className="h-3 w-3" />
                  {new Date(updatedAt).toLocaleString("zh-CN")}
                </Badge>
              )}
            </div>
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <div className="flex items-center gap-2 border-b px-5 py-3">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">服务组件</h3>
        </div>
        <div className="divide-y">
          {loading && (
            <CardContent className="py-6 text-sm text-muted-foreground">正在读取实时数据…</CardContent>
          )}
          {!loading && error && (
            <CardContent className="py-6 text-sm text-muted-foreground">暂无可展示的实时组件数据。</CardContent>
          )}
          {components.map((component) => (
            <div key={component.name} className="flex items-center justify-between gap-3 px-5 py-3.5">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Server className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-medium">{component.name}</p>
                  <p className="text-[11px] text-muted-foreground">{component.detail}</p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                {component.latencyMs > 0 && (
                  <span className="hidden text-[11px] tabular-nums text-muted-foreground sm:inline">
                    {component.latencyMs}ms
                  </span>
                )}
                <Badge variant={STATUS_TONE[component.status]} className="text-[10px]">
                  {STATUS_LABEL[component.status]}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
