"use client";

import { Info, MessageSquare, ShieldAlert, ThumbsDown, ThumbsUp } from "lucide-react";
import * as React from "react";
import { ToolCallCard } from "@/components/agent/tool-call-card";
import { saveFeedback } from "@/lib/api/feedbackApi";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground">
        {content}
      </div>
    </div>
  );
}

function AssistantBubble({ message }: { message: ChatMessage }) {
  const meta = message.meta;
  const [rating, setRating] = React.useState<-1 | 1 | null>(null);

  const rate = async (value: -1 | 1) => {
    if (!meta?.runId) return;
    setRating(value);
    try {
      await saveFeedback(meta.runId, value);
    } catch {
      setRating(null);
    }
  };
  return (
    <div className="flex gap-2.5">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <MessageSquare className="h-3.5 w-3.5" />
      </div>
      <div className="max-w-[90%] space-y-1">
        <div className="rounded-2xl rounded-tl-sm border bg-card px-3.5 py-2.5 text-sm leading-relaxed text-foreground">
          {message.content}
        </div>
        {meta?.latencyMs !== undefined && (
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span>AutoMind · {meta.latencyMs}ms</span>
            {meta.runId && (
              <span className="flex items-center gap-1" aria-label="评价此回答">
                <button
                  type="button"
                  className={cn("rounded p-1 hover:text-foreground", rating === 1 && "text-primary")}
                  onClick={() => void rate(1)}
                  aria-label="回答有帮助"
                >
                  <ThumbsUp className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  className={cn("rounded p-1 hover:text-foreground", rating === -1 && "text-destructive")}
                  onClick={() => void rate(-1)}
                  aria-label="回答没有帮助"
                >
                  <ThumbsDown className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SafetyWarning({ message }: { message: ChatMessage }) {
  return (
    <div
      role="alert"
      className="flex gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-3"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-destructive/15 text-destructive">
        <ShieldAlert className="h-4 w-4" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-destructive">
          操作已拒绝
        </p>
        <p className="text-xs text-muted-foreground">{message.meta?.safetyReason}</p>
        <p className="text-sm text-foreground">{message.content}</p>
      </div>
    </div>
  );
}

function SystemEvent({ message }: { message: ChatMessage }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <Info className="h-3.5 w-3.5" />
      <span>{message.content}</span>
    </div>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  switch (message.kind) {
    case "user":
      return <UserBubble content={message.content} />;
    case "tool_call":
      return (
        <div className="flex flex-col gap-1.5 pl-9">
          {message.tools?.map((tool, i) => (
            <ToolCallCard key={`${message.id}-${i}`} tool={tool} />
          ))}
        </div>
      );
    case "safety_warning":
      return <SafetyWarning message={message} />;
    case "system_event":
      return <SystemEvent message={message} />;
    case "assistant":
    default:
      return <AssistantBubble message={message} />;
  }
}

export function TypingBubble() {
  return (
    <div className="flex gap-2.5" aria-label="AutoMind 正在回复">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <MessageSquare className="h-3.5 w-3.5" />
      </div>
      <div
        className={cn(
          "flex items-center gap-1 rounded-2xl rounded-tl-sm border bg-card px-3.5 py-3",
        )}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
