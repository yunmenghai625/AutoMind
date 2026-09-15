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
import { useRouter } from "next/navigation";
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
import { HttpClientError } from "@/lib/api/apiClient";
import { clearAccessToken, hasAccessToken } from "@/lib/api/identity";
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
    message: "车辆速度大于 0（当前 120 km/h），车门解锁请求已被拦截。",
    at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
  {
    id: "se_2",
    rule: "speed_limit_120",
    severity: "warning",
    message: "车辆正在接近 AI 管理的速度上限。",
    at: new Date(Date.now() - 7 * 3600000).toISOString(),
  },
  {
    id: "se_3",
    rule: "battery_low_guard",
    severity: "info",
    message: "电量低于 20% 时，座椅加热限制为 1 挡。",
    at: new Date(Date.now() - 22 * 3600000).toISOString(),
  },
];

const AGENT_LABEL: Record<string, string> = {
  Cockpit: "座舱智能体",
  Knowledge: "知识智能体",
  Diagnosis: "诊断智能体",
  Vehicle: "车辆智能体",
};

const RUN_STATUS_LABEL: Record<string, string> = {
  success: "成功",
  failed: "失败",
  blocked: "已拦截",
  rejected: "已拒绝",
  running: "运行中",
};

const COMPONENT_STATUS_LABEL: Record<SystemComponent["status"], string> = {
  operational: "正常",
  degraded: "降级",
  down: "中断",
};

const SAFETY_SEVERITY_LABEL: Record<AgentSafetyEvent["severity"], string> = {
  info: "提示",
  warning: "警告",
  blocked: "已拦截",
};

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
          系统组件
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
                {COMPONENT_STATUS_LABEL[c.status]}
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
          安全事件
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pt-4">
        {events.map((e) => (
          <div key={e.id} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between gap-2">
              <span className={cn("text-[10px] font-mono uppercase", tone[e.severity])}>
                {SAFETY_SEVERITY_LABEL[e.severity]}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {formatTime(e.at)}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{e.message}</p>
            <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/60">
              规则：{e.rule}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function AdminView() {
  const router = useRouter();
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
    if (!IS_MOCK && !hasAccessToken()) {
      router.replace("/admin/login");
      return;
    }
    void Promise.all([
      getAdminOverview().then(setOverview),
      getAdminMetrics().then(setMetrics),
      getAgentRuns().then(setRuns),
      getSystemComponents().then(setComponents),
      getSafetyEvents().then((events) => {
        if (!IS_MOCK) setSafetyEvents(events);
      }),
    ]).catch((cause) => {
      if (cause instanceof HttpClientError && [401, 403].includes(cause.status)) {
        clearAccessToken();
        router.replace("/admin/login");
        return;
      }
      setError("运营指标暂时无法加载，请稍后重试。");
    });
  }, [router]);

  if (error) {
    return <div className="container mx-auto max-w-7xl px-4 py-6"><PageHeader title="运营管理" /><p className="mt-6 text-sm text-destructive">{error}</p></div>;
  }

  if (!overview || !metrics) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="运营管理" />
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
    name: "智能体成功率",
    color: "hsl(var(--success))",
    values: metrics.traffic.map((t) => t.agentSuccessRate),
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="运营管理看板"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description={`平台可观测性——智能体成功率、延迟、工具调用与成本。更新时间：${new Date(overview.generatedAt).toLocaleTimeString("zh-CN")}`}
      />

      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <OverviewCard icon={<Users className="h-4 w-4" />} label="用户数" value={String(overview.users)} />
        <OverviewCard
          icon={<Activity className="h-4 w-4" />}
          label="请求数"
          value={Intl.NumberFormat("zh-CN").format(overview.requests)}
          hint={`最近 24 小时 · 已排除 ${overview.testRequests} 条压测请求`}
          spark={trafficValues.slice(-8)}
        />
        <OverviewCard
          icon={<Bot className="h-4 w-4" />}
          label="智能体成功率"
          value={String(overview.agentSuccessRate)}
          suffix="%"
          hint="滚动统计窗口"
          spark={successSeries.values.slice(-8)}
        />
        <OverviewCard
          icon={<Clock className="h-4 w-4" />}
          label="P95 延迟"
          value={String(overview.p95Latency)}
          suffix="s"
          hint="智能体响应"
        />
        <OverviewCard
          icon={<Waypoints className="h-4 w-4" />}
          label="工具成功率"
          value={String(overview.toolSuccessRate)}
          suffix="%"
          hint="全部工具"
        />
        <OverviewCard
          icon={<DollarSign className="h-4 w-4" />}
          label="AI 成本"
          value={String(overview.aiCost)}
          suffix="¥"
          hint="今日"
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-primary" />
              流量与成功率
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div>
              <p className="mb-2 text-xs text-muted-foreground">
                每日请求量 · 压测流量不计入真实用户统计
              </p>
              <MultiLines
                labels={trafficLabels}
                series={[
                  {
                    name: "用户流量",
                    color: "hsl(var(--primary))",
                    values: trafficValues,
                  },
                  {
                    name: "压测流量",
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
                智能体每日成功率
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
              智能体使用量
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <UsageBars
              data={metrics.usage.map((u) => ({ label: AGENT_LABEL[u.agent] ?? u.agent, value: u.calls }))}
            />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cpu className="h-4 w-4 text-primary" />
              响应延迟（秒）
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
              每日 AI 成本（¥）
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <MultiLines
              labels={metrics.dailyCost.map((c) => c.date)}
              series={[
                { name: "成本", color: "hsl(var(--accent))", values: metrics.dailyCost.map((c) => c.cost) },
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
              最近智能体运行记录
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto pt-2">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 font-medium">运行 ID</th>
                  <th className="pb-2 font-medium">智能体</th>
                  <th className="pb-2 font-medium">延迟</th>
                  <th className="pb-2 font-medium">工具</th>
                  <th className="pb-2 font-medium">状态</th>
                  <th className="pb-2 font-medium">时间</th>
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
                    <td className="py-2.5">{AGENT_LABEL[r.agent] ?? r.agent}</td>
                    <td className="py-2.5 tabular-nums">{r.latencyMs}ms · {r.steps} 步</td>
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
                        {RUN_STATUS_LABEL[r.status] ?? r.status}
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
              运行记录 {detail.id}
              <Badge
                variant={detail.status === "success" ? "success" : detail.status === "failed" ? "destructive" : "warning"}
                className="text-[10px]"
              >
                {RUN_STATUS_LABEL[detail.status] ?? detail.status}
              </Badge>
            </DialogTitle>
            <DialogDescription>
              {AGENT_LABEL[detail.agent] ?? detail.agent} · {detail.latencyMs}ms ·{" "}
              {new Date(detail.time).toLocaleString("zh-CN")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-lg bg-muted/40 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                用户问题
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
              关闭
            </Button>
          </DialogFooter>
        </>
      )}
    </Dialog>
  );
}
