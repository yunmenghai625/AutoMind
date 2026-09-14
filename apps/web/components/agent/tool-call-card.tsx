"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ToolCall } from "@/types/chat";

const STATUS_STYLES: Record<ToolCall["status"], string> = {
  SUCCESS: "bg-success/15 text-success",
  RUNNING: "bg-amber-500/15 text-amber-500",
  FAILED: "bg-destructive/15 text-destructive",
  BLOCKED: "bg-destructive/15 text-destructive",
};

const STATUS_LABEL: Record<ToolCall["status"], string> = {
  SUCCESS: "成功",
  RUNNING: "执行中",
  FAILED: "失败",
  BLOCKED: "已拦截",
};

function formatParamValue(v: string | number | boolean): string {
  if (typeof v === "number") return String(v);
  if (typeof v === "boolean") return v ? "是" : "否";
  const labels: Record<string, string> = {
    Driver: "主驾",
    "Front Passenger": "前排乘客",
    driver_door: "主驾车门",
  };
  return labels[v] ?? v;
}

function paramLabel(key: string): string {
  const map: Record<string, string> = {
    zone: "区域",
    target: "目标值",
    level: "挡位",
    value: "数值",
    speed: "车速",
    window: "车窗",
    light: "灯光",
    ac: "空调",
  };
  return map[key] ?? key;
}

/**
 * Renders a single Tool Call invocation as a structured card,
 * mirroring the "Tool / Zone / Target / Status" spec from the 设计书.
 */
export function ToolCallCard({ tool }: { tool: ToolCall }) {
  return (
    <Card className="w-full max-w-sm border-muted bg-muted/30">
      <CardContent className="p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
              <WrenchIcon />
            </span>
            <span className="font-mono text-xs text-foreground">{tool.name}</span>
          </div>
          <Badge
            variant="outline"
            className={cn("font-mono text-[10px]", STATUS_STYLES[tool.status])}
          >
            {STATUS_LABEL[tool.status]}
          </Badge>
        </div>

        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
          {Object.entries(tool.params).map(([k, v]) => (
            <div key={k} className="col-span-1 contents text-xs">
              <dt className="text-muted-foreground">{paramLabel(k)}</dt>
              <dd className="font-medium text-foreground tabular-nums">
                {formatParamValue(v)}
                {k.toLowerCase().includes("target") &&
                typeof v === "number" ? (
                  "°C"
                ) : (
                  <></>
                )}
              </dd>
            </div>
          ))}
        </dl>

        {tool.durationMs !== undefined && (
          <p className="mt-2 text-[10px] text-muted-foreground">
            执行耗时 {tool.durationMs}ms
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function WrenchIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}
