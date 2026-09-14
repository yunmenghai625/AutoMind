"use client";

import { Button } from "@/components/ui/button";

interface ModelStatusBadgeProps {
  online?: boolean;
}

/** Header model status indicator (mock). */
export function ModelStatusBadge({ online = true }: ModelStatusBadgeProps) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground"
      title={online ? "AI 模型服务在线" : "AI 模型服务离线"}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          online ? "bg-success" : "bg-destructive",
        )}
      />
      <span className="hidden sm:inline">
        {online ? "模型在线" : "模型离线"}
      </span>
      <span className="sm:hidden">API</span>
    </div>
  );
}

import { cn } from "@/lib/utils";
