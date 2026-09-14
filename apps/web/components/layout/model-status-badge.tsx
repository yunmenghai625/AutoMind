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
      title={online ? "AI Model Provider Online" : "AI Model Provider Offline"}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          online ? "bg-success" : "bg-destructive",
        )}
      />
      <span className="hidden sm:inline">
        {online ? "Model Online" : "Model Offline"}
      </span>
      <span className="sm:hidden">API</span>
    </div>
  );
}

import { cn } from "@/lib/utils";
