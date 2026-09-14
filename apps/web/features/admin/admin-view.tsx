"use client";

import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  CircuitBoard,
  Clock,
  Cpu,
  DollarSign,
  FileWarning,
  Layers,
  ShieldAlert,
  Users,
  Waypoints,
} from "lucide-react";
import * as React from "react";
import { PageHeader } from "@/components/common/page-header";
import { MockBadge } from "@/components/common/mock-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  getAdminMetrics,
  getAdminOverview,
  getAgentRuns,
  getAgentRunDetailById,
  getSafetyEvents,
  getSystemComponents,
} from "@/lib/api/adminApi";
import { IS_MOCK } from "@/lib/config";
import { MultiLines, Sparkline, UsageBars, VerticalBars } from "@/features/admin/charts";
import type {
  AdminMetrics,
  AdminOverview,
  AgentRun,
  AgentRunDetail,
  AgentSafetyEvent,
  SystemComponent,
} from "@/types/agent";

const MOCK_SAFETY_EVENTS: AgentSafetyEvent[] = [
  {
    id: "se_1",
    rule: "doors_blocked_while_moving",
    severity: "blocked",
    message: "Door unlock request blocked while vehicle speed > 0 (120 km/h).",
    at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
  {
    id: "se_2",
    rule: "speed_limit_120",
    severity: "warning",
    message: "Vehicle approaching AI-managed speed cap.",
    at: new Date(Date.now() - 7 * 3600000).toISOString(),
  },
  {
    id: "se_3",
    rule: "battery_low_guard",
    severity: "info",
    message: "Seat heating capped to level 1 when battery below 20%.",
    at: new Date(Date.now() - 22 * 3600000).toISOString(),
  },
];

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function OverviewCard({
  icon,
  label,
  value,
  suffix,
  hint,
  spark,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  suffix?: string;
  hint?: string;
  spark?: number[];
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-2 pt-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-xs font-medium">{label}</span>
        </div>
        <p className="text-2xl font-bold tabular-nums">
          {value}
          {suffix && (
            <span className="ml-0.5 text-sm font-medium text-muted-foreground">
              {suffix}
            </span>
          )}
        </p>
        {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
        {spark && (
          <div className="flex items-end justify-end">
            <Sparkline values={spark} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const STATUS_BADGE: Record<SystemComponent["status"], string> = {
  operational: "success",
  degraded: "warning",
  down: "destructive",
};

function ComponentStatus({ items }: { items: SystemComponent[] }) {
  return (
    <Card>
      <CardHeader className="border-b py-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <CircuitBoard className="h-4 w-4 text-primary" />
          System Components
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pt-4">
        {items.map((c) => (
          <div
            key={c.name}
            className="flex items-center justify-between gap-2 rounded-lg border bg-card px-3 py-2"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium">{c.name}</p>
              <p className="truncate text-[11px] text-muted-foreground">{c.detail}</p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="tabular-nums text-[11px] text-muted-foreground">
                {c.latencyMs}ms
              </span>
              <Badge
                variant={STATUS_BADGE[c.status] as "success" | "warning" | "destructive"}
                className="text-[10px]"
              >
                {c.status}
              </Badge>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function SafetyEvents({ events }: { events: AgentSafetyEvent[] }) {
  const tone: Record<AgentSafetyEvent["severity"], string> = {
    info: "text-primary",
    warning: "text-warning",
    blocked: "text-destructive",
  };
  return (
    <Card>
      <CardHeader className="border-b py-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <ShieldAlert className="h-4 w-4 text-primary" />
          Safety Events
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pt-4">
        {events.map((e) => (
          <div key={e.id} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between gap-2">
              <span className={cn("text-[10px] font-mono uppercase", tone[e.severity])}>
                {e.severity}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {formatTime(e.at)}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{e.message}</p>
            <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/60">
              rule: {e.rule}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function AdminView() {
  const [overview, setOverview] = React.useState<AdminOverview | null>(null);
  const [metrics, setMetrics] = React.useState<AdminMetrics | null>(null);
  const [runs, setRuns] = React.useState<AgentRun[]>([]);
  const [detail, setDetail] = React.useState<AgentRunDetail | null>(null);
  const [components, setComponents] = React.useState<SystemComponent[]>([]);
  const [safetyEvents, setSafetyEvents] = React.useState<AgentSafetyEvent[]>(
    IS_MOCK ? MOCK_SAFETY_EVENTS : [],
  );
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    void Promise.all([
      getAdminOverview().then(setOverview),
      getAdminMetrics().then(setMetrics),
      getAgentRuns().then(setRuns),
      getSystemComponents().then(setComponents),
      getSafetyEvents().then((events) => {
        if (!IS_MOCK) setSafetyEvents(events);
      }),
    ]).catch(() => setError("Admin metrics require a valid administrator session."));
  }, []);

  if (error) {
    return <div className="container mx-auto max-w-7xl px-4 py-6"><PageHeader title="Admin" /><p className="mt-6 text-sm text-destructive">{error}</p></div>;
  }

  if (!overview || !metrics) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="Admin" />
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-muted/50" />
          ))}
        </div>
      </div>
    );
  }

  const trafficLabels = metrics.traffic.map((t) => t.timestamp.slice(5));
  const trafficValues = metrics.traffic.map((t) => t.requests);
  const testTrafficValues = metrics.traffic.map((t) => t.testRequests);
  const successSeries = {
    name: "Agent Success Rate",
    color: "hsl(var(--success))",
    values: metrics.traffic.map((t) => t.agentSuccessRate),
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="Admin Dashboard"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description={`Platform observability — agent success rate, latency, tool usage and cost. Refreshed ${new Date(overview.generatedAt).toLocaleTimeString("zh-CN")}`}
      />

      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <OverviewCard icon={<Users className="h-4 w-4" />} label="Users" value={String(overview.users)} />
        <OverviewCard
          icon={<Activity className="h-4 w-4" />}
          label="Requests"
          value={Intl.NumberFormat("en-US").format(overview.requests)}
          hint={`last 24h · ${overview.testRequests} load-test excluded`}
          spark={trafficValues.slice(-8)}
        />
        <OverviewCard
          icon={<Bot className="h-4 w-4" />}
          label="Agent Success"
          value={String(overview.agentSuccessRate)}
          suffix="%"
          hint="rolling window"
          spark={successSeries.values.slice(-8)}
        />
        <OverviewCard
          icon={<Clock className="h-4 w-4" />}
          label="P95 Latency"
          value={String(overview.p95Latency)}
          suffix="s"
          hint="agent responses"
        />
        <OverviewCard
          icon={<Waypoints className="h-4 w-4" />}
          label="Tool Success"
          value={String(overview.toolSuccessRate)}
          suffix="%"
          hint="all tools"
        />
        <OverviewCard
          icon={<DollarSign className="h-4 w-4" />}
          label="AI Cost"
          value={String(overview.aiCost)}
          suffix="¥"
          hint="today"
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-primary" />
              Traffic & Success Rate
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div>
              <p className="mb-2 text-xs text-muted-foreground">
                Requests per day · load-test traffic is excluded from user totals
              </p>
              <MultiLines
                labels={trafficLabels}
                series={[
                  {
                    name: "User traffic",
                    color: "hsl(var(--primary))",
                    values: trafficValues,
                  },
                  {
                    name: "Load test",
                    color: "hsl(var(--muted-foreground))",
                    values: testTrafficValues,
                  },
                ]}
                height={110}
              />
              <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                <span>{trafficLabels[0]}</span>
                <span>{trafficLabels.at(-1)}</span>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs text-muted-foreground">
                Agent success rate (daily)
              </p>
              <VerticalBars
                labels={trafficLabels}
                values={successSeries.values}
                height={70}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Layers className="h-4 w-4 text-primary" />
              Agent Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <UsageBars
              data={metrics.usage.map((u) => ({ label: u.agent, value: u.calls }))}
            />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cpu className="h-4 w-4 text-primary" />
              Response Latency (s)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <MultiLines
              labels={metrics.latency.map((l) => l.date)}
              series={[
                { name: "p99", color: "hsl(var(--destructive))", values: metrics.latency.map((l) => l.p99) },
                { name: "p95", color: "hsl(var(--warning))", values: metrics.latency.map((l) => l.p95) },
                { name: "p50", color: "hsl(var(--primary))", values: metrics.latency.map((l) => l.p50) },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-primary" />
              Daily AI Cost (¥)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <MultiLines
              labels={metrics.dailyCost.map((c) => c.date)}
              series={[
                { name: "cost", color: "hsl(var(--accent))", values: metrics.dailyCost.map((c) => c.cost) },
              ]}
            />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-primary" />
              Recent Agent Runs
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto pt-2">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 font-medium">Run</th>
                  <th className="pb-2 font-medium">Agent</th>
                  <th className="pb-2 font-medium">Latency</th>
                  <th className="pb-2 font-medium">Tools</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => {
                      void getAgentRunDetailById(r.id).then(setDetail);
                    }}
                    className="cursor-pointer border-b transition-colors hover:bg-muted/40"
                  >
                    <td className="py-2.5 font-mono text-xs">{r.id}</td>
                    <td className="py-2.5">{r.agent}</td>
                    <td className="py-2.5 tabular-nums">{r.latencyMs}ms · {r.steps} steps</td>
                    <td className="max-w-[220px] py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {r.toolsUsed.map((t) => (
                          <span key={t} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5">
                      <Badge
                        variant={r.status === "success" ? "success" : r.status === "failed" ? "destructive" : "warning"}
                        className="text-[10px]"
                      >
                        {r.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 text-xs text-muted-foreground">{formatTime(r.time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <ComponentStatus items={components} />
          <SafetyEvents events={safetyEvents} />
        </div>
      </div>

      <RunDetailDialog
        detail={detail}
        onClose={() => setDetail(null)}
      />
    </div>
  );
}

function RunDetailDialog({
  detail,
  onClose,
}: {
  detail: AgentRunDetail | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={!!detail} onOpenChange={(o) => !o && onClose()}>
      {detail && (
        <>
          <DialogClose onClose={onClose} />
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Run {detail.id}
              <Badge
                variant={detail.status === "success" ? "success" : detail.status === "failed" ? "destructive" : "warning"}
                className="text-[10px]"
              >
                {detail.status}
              </Badge>
            </DialogTitle>
            <DialogDescription>
              {detail.agent} agent · {detail.latencyMs}ms ·{" "}
              {new Date(detail.time).toLocaleString("zh-CN")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-lg bg-muted/40 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                User Query
              </p>
              <p className="mt-1 text-sm">{detail.query}</p>
            </div>

            <ol className="space-y-1.5">
              {detail.trace.map((step, i) => (
                <li key={i} className="flex items-start gap-3 rounded-lg border bg-card p-2.5">
                  <span className="mt-1 flex h-2 w-2 shrink-0 rounded-full bg-primary" />
                  <div className="flex flex-1 items-center justify-between gap-2">
                    <div>
                      <p className="text-xs font-medium">{step.name}</p>
                      {step.detail && (
                        <p className="text-[11px] text-muted-foreground">{step.detail}</p>
                      )}
                    </div>
                    <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                      {step.durationMs}ms
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </DialogFooter>
        </>
      )}
    </Dialog>
  );
}
