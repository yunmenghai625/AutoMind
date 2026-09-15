"use client";

import * as React from "react";
import { getHealthSnapshot } from "@/lib/api/statusApi";
import { cn } from "@/lib/utils";

/** Reports only the API state verified by the backend health endpoint. */
export function ModelStatusBadge() {
  const [status, setStatus] = React.useState<"checking" | "online" | "offline">("checking");

  React.useEffect(() => {
    let alive = true;
    void getHealthSnapshot()
      .then(({ health }) => {
        if (alive) setStatus(health.status === "ok" ? "online" : "offline");
      })
      .catch(() => {
        if (alive) setStatus("offline");
      });
    return () => {
      alive = false;
    };
  }, []);

  const online = status === "online";
  const label = status === "checking" ? "API 检查中" : online ? "API 在线" : "API 不可用";

  return (
    <div
      className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground"
      title={label}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          status === "checking" ? "bg-muted-foreground" : online ? "bg-success" : "bg-destructive",
        )}
      />
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">API</span>
    </div>
  );
}
