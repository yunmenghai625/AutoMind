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
      .catch(() => setError("Garage data is temporarily unavailable."));
  }, []);

  if (error) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="Garage" />
        <Card><CardContent className="py-6 text-sm text-muted-foreground">{error}</CardContent></Card>
      </div>
    );
  }

  if (!vehicle) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-6">
        <PageHeader title="Garage" />
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
      meta: firstRecall ? `Issued ${firstRecall.issuedAt} · ${firstRecall.risk} risk` : "-",
    },
    {
      id: "service-1",
      kind: "service" as const,
      title: "Annual maintenance due",
      detail: "Recommended at the 15,000 km mark.",
      meta: "Next service in 2,158 km",
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
        title="Garage"
        badge={IS_MOCK ? <MockBadge /> : undefined}
        description="Your connected vehicle at a glance — health, battery and service notifications."
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
            <Badge variant="success" className="text-[10px]">Vehicle Connected</Badge>
            <span className="text-[11px] text-muted-foreground">
              Last check · {vehicle.lastCheck}
            </span>
          </div>
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Readout
          icon={<Gauge className="h-4 w-4" />}
          label="Mileage"
          value={`${(vehicle.mileageKm / 1000).toFixed(1)}k km`}
        />
        <Readout
          icon={<Timer className="h-4 w-4" />}
          label="Battery SoC"
          value={`${vehicle.batterySoc}%`}
          bar={vehicle.batterySoc}
        />
        <Readout
          icon={<HeartPulse className="h-4 w-4" />}
          label="Battery Health"
          value={vehicle.batteryHealth === null ? "—" : `${vehicle.batteryHealth}%`}
          bar={vehicle.batteryHealth ?? undefined}
        />
        <Readout
          icon={<Timer className="h-4 w-4" />}
          label="Last Check"
          value={vehicle.lastCheck}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className={recalls.length ? "border-warning/40 bg-warning/5" : ""}>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldAlert className="h-4 w-4 text-warning" />
              Recalls
              {recallStatus !== "success" && (
                <Badge variant="outline" className="ml-auto text-[10px]">
                  {recallStatus}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {recalls.length === 0 && recallStatus === "unavailable" && (
              <p className="text-sm text-muted-foreground">
                Recall provider is temporarily unavailable. Try again later.
              </p>
            )}
            {recalls.length === 0 && recallStatus !== "unavailable" && (
              <p className="text-sm text-muted-foreground">
                No open recalls for this vehicle.
              </p>
            )}
            {recalls.map((r) => (
              <div key={r.id} className="rounded-lg border bg-card p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{r.component}</p>
                  <Badge variant={RISK_TONE[r.risk]} className="text-[10px]">
                    {r.risk}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {r.recommendedAction}
                </p>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground/70">
                  {r.id} · issued {r.issuedAt}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              Service & Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter service items…"
                className="pl-8"
                aria-label="Filter service notifications"
              />
            </div>
            {visible.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No items match “{filter}”.
              </p>
            )}
            {visible.map((i) => (
              <div key={i.id} className="rounded-lg border bg-card p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{i.title}</p>
                  <Badge variant={i.kind === "recall" ? "warning" : "outline"} className="text-[10px]">
                    {i.kind}
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
