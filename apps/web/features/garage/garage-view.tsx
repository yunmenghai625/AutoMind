"use client";

import { CarFront, Gauge, HeartPulse, Search, ShieldAlert, Timer } from "lucide-react";
import * as React from "react";
import { PageHeader } from "@/components/common/page-header";
import { MockBadge } from "@/components/common/mock-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { getGarageVehicle, getRecalls } from "@/lib/api/garageApi";
import { IS_MOCK } from "@/lib/config";
import { AiPreferences } from "@/features/garage/ai-preferences";
import type { GarageVehicle, RecallRecord } from "@/types/vehicle";

const RISK_TONE: Record<RecallRecord["risk"], "warning" | "destructive" | "outline"> = {
  Low: "outline",
  Medium: "warning",
  High: "destructive",
};

const RISK_LABEL: Record<RecallRecord["risk"], string> = {
  Low: "低风险",
  Medium: "中风险",
  High: "高风险",
};

const RECALL_STATUS_LABEL = {
  success: "正常",
  cached: "缓存数据",
  degraded: "降级服务",
  unavailable: "暂不可用",
} as const;

export function GarageView() {
  const [vehicle, setVehicle] = React.useState<GarageVehicle | null>(null);
  const [recalls, setRecalls] = React.useState<RecallRecord[]>([]);
  const [recallStatus, setRecallStatus] = React.useState<
    "success" | "cached" | "degraded" | "unavailable"
  >("success");
  const [filter, setFilter] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    void Promise.all([getGarageVehicle(), getRecalls()])
      .then(([nextVehicle, recallResult]) => {
        setVehicle(nextVehicle);
        setRecalls(recallResult.recalls);
        setRecallStatus(recallResult.status);
      })
      .catch(() => setError("车库数据暂时不可用。"));
  }, []);

  if (error) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="我的车库" />
        <Card><CardContent className="py-6 text-sm text-muted-foreground">{error}</CardContent></Card>
      </div>
    );
  }

  if (!vehicle) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="我的车库" />
        <div className="grid gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-muted/50" />
          ))}
        </div>
      </div>
    );
  }

  const maskedVin = vehicle.vin;
  const firstRecall = recalls[0] ?? null;
  const items = [
    {
      id: "recall-" + (firstRecall?.id ?? "none"),
      kind: "recall" as const,
      title: firstRecall?.component ?? "-",
      detail: firstRecall?.recommendedAction ?? "-",
      meta: firstRecall ? `发布于 ${firstRecall.issuedAt} · ${RISK_LABEL[firstRecall.risk]}` : "-",
    },
    {
      id: "service-1",
      kind: "service" as const,
      title: "年度保养即将到期",
      detail: "建议在行驶里程达到 15,000 km 时进行保养。",
      meta: "距下次保养约 2,158 km",
    },
  ];

  const q = filter.trim().toLowerCase();
  const visible = items.filter(
    (i) =>
      !q ||
      i.title.toLowerCase().includes(q) ||
      i.detail.toLowerCase().includes(q) ||
      i.meta.toLowerCase().includes(q),
  );

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="我的车库"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description="集中查看已连接车辆的健康、电池、召回与保养提醒。"
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 bg-gradient-to-r from-primary/10 via-transparent to-transparent p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <CarFront className="h-6 w-6" />
            </span>
            <div>
              <h2 className="text-lg font-semibold">{vehicle.name}</h2>
              <p className="text-xs text-muted-foreground">
                {vehicle.trim} · {vehicle.color}
              </p>
              <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                VIN <span>{maskedVin}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success" className="text-[10px]">车辆已连接</Badge>
            <span className="text-[11px] text-muted-foreground">
              最近检查 · {vehicle.lastCheck}
            </span>
          </div>
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Readout
          icon={<Gauge className="h-4 w-4" />}
          label="行驶里程"
          value={`${(vehicle.mileageKm / 1000).toFixed(1)}k km`}
        />
        <Readout
          icon={<Timer className="h-4 w-4" />}
          label="电池电量"
          value={`${vehicle.batterySoc}%`}
          bar={vehicle.batterySoc}
        />
        <Readout
          icon={<HeartPulse className="h-4 w-4" />}
          label="电池健康度"
          value={vehicle.batteryHealth === null ? "—" : `${vehicle.batteryHealth}%`}
          bar={vehicle.batteryHealth ?? undefined}
        />
        <Readout
          icon={<Timer className="h-4 w-4" />}
          label="最近检查"
          value={vehicle.lastCheck}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className={recalls.length ? "border-warning/40 bg-warning/5" : ""}>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldAlert className="h-4 w-4 text-warning" />
              召回信息
              {recallStatus !== "success" && (
                <Badge variant="outline" className="ml-auto text-[10px]">
                  {RECALL_STATUS_LABEL[recallStatus]}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {recalls.length === 0 && recallStatus === "unavailable" && (
              <p className="text-sm text-muted-foreground">
                召回数据服务暂时不可用，请稍后重试。
              </p>
            )}
            {recalls.length === 0 && recallStatus !== "unavailable" && (
              <p className="text-sm text-muted-foreground">
                当前车辆没有未处理的召回项目。
              </p>
            )}
            {recalls.map((r) => (
              <div key={r.id} className="rounded-lg border bg-card p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{r.component}</p>
                  <Badge variant={RISK_TONE[r.risk]} className="text-[10px]">
                    {RISK_LABEL[r.risk]}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {r.recommendedAction}
                </p>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground/70">
                  {r.id} · 发布于 {r.issuedAt}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              保养与通知
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="筛选保养与通知…"
                className="pl-8"
                aria-label="筛选保养通知"
              />
            </div>
            {visible.length === 0 && (
              <p className="text-sm text-muted-foreground">
                没有与“{filter}”匹配的项目。
              </p>
            )}
            {visible.map((i) => (
              <div key={i.id} className="rounded-lg border bg-card p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{i.title}</p>
                  <Badge variant={i.kind === "recall" ? "warning" : "outline"} className="text-[10px]">
                    {i.kind === "recall" ? "召回" : "保养"}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{i.detail}</p>
                {i.meta && (
                  <p className="mt-1 text-[11px] text-muted-foreground/80">{i.meta}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <AiPreferences />
      </div>
    </div>
  );
}

function Readout({
  icon,
  label,
  value,
  bar,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  bar?: number;
}) {
  return (
    <Card>
      <CardContent className="space-y-1.5 pt-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-xs font-medium">{label}</span>
        </div>
        <p className="text-xl font-bold tabular-nums">{value}</p>
        {typeof bar === "number" && <Progress value={bar} className="h-1.5" />}
      </CardContent>
    </Card>
  );
}
