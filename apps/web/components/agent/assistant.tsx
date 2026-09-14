"use client";

import { Sparkles, Send } from "lucide-react";
import * as React from "react";
import { MessageBubble, TypingBubble } from "@/components/agent/message-bubble";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { sendChat } from "@/lib/api/cockpitApi";
import { IS_MOCK } from "@/lib/config";
import { uid } from "@/lib/mock/chat";
import type { ChatMessage } from "@/types/chat";

const SUGGESTIONS = [
  "我有点冷",
  "我妈有点冷",
  "120公里时速帮我打开车门",
  "我的电量还够吗",
];

/** Demo greeting appended locally so every first visit looks alive. */
function greeting(): ChatMessage {
  return {
    id: uid("sys"),
    role: "assistant",
    kind: "system_event",
    content: `AutoMind 助手已就绪 · ${IS_MOCK ? "模拟模式" : "在线 API"}。可以试试“我有点冷”，或询问车辆电量。`,
    at: new Date().toISOString(),
  };
}

/**
 * AutoMind Assistant conversation panel.
 * SSE-ready: mock provider returns a finished message and the UI replays it
 * token-by-token to simulate streaming. Swapping to /api/v1/chat/stream
 * only requires replacing the send() internals.
 */
export function AssistantPanel() {
  const [messages, setMessages] = React.useState<ChatMessage[]>([greeting()]);
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const streamRef = React.useRef<number | null>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  const stopStream = () => {
    if (streamRef.current) {
      window.clearInterval(streamRef.current);
      streamRef.current = null;
    }
  };

  React.useEffect(() => stopStream, []);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  const streamText = (targetId: string, fullText: string) => {
    let idx = 0;
    return new Promise<void>((resolve) => {
      streamRef.current = window.setInterval(() => {
        idx += 2;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === targetId ? { ...m, content: fullText.slice(0, idx) } : m,
          ),
        );
        if (idx >= fullText.length) {
          stopStream();
          setMessages((prev) =>
            prev.map((m) =>
              m.id === targetId ? { ...m, content: fullText } : m,
            ),
          );
          resolve();
        }
      }, 14);
    });
  };

  const handleSend = async (raw?: string) => {
    const text = (raw ?? input).trim();
    if (!text || busy) return;
    setInput("");
    const userMsg: ChatMessage = {
      id: uid("user"),
      role: "user",
      kind: "user",
      content: text,
      at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setBusy(true);

    try {
      // Step 1: optimistic placeholder for the answered assistant bubble
      const answerId = uid("asst");
      setMessages((prev) => [
        ...prev,
        { id: answerId, role: "assistant", kind: "assistant", content: "", at: new Date().toISOString() },
      ]);

      // Step 2: query the API layer (+ tool calls / safety warnings)
      const res = await sendChat({ message: text });
      const nonAnswer = res.messages.filter(
        (m) => m.kind !== "assistant",
      );
      const answer = res.messages.find((m) => m.kind === "assistant")?.content ?? "";

      // Step 3: append tool cards / safety / system messages
      if (nonAnswer.length > 0) {
        setMessages((prev) => {
          const withoutPlaceholder = prev.filter((m) => m.id !== answerId);
          return [...withoutPlaceholder, ...nonAnswer.map((m) => ({ ...m }))];
        });
      }

      // Step 4: replay assistant answer token-by-token (streaming simulation)
      const answerMsg = res.messages.find((m) => m.kind === "assistant");
      if (answerMsg) {
        await streamText(answerId, answer);
        setMessages((prev) => {
          const withoutPlaceholder = prev.filter((m) => m.id !== answerId);
          return [...withoutPlaceholder, answerMsg];
        });
      }
    } catch {
      setMessages((prev) => [
        ...prev.filter((m) => !(m.kind === "assistant" && m.content === "")),
        {
          id: uid("err"),
          role: "assistant",
          kind: "system_event",
          content: "AutoMind API 暂时不可用，请稍后重试。",
          at: new Date().toISOString(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="border-b py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="text-base leading-tight">
              AutoMind 智能助手
            </CardTitle>
            <p className="text-[11px] text-muted-foreground">
              自然语言车辆控制 · {IS_MOCK ? "模拟模式" : "在线 API"}
            </p>
          </div>
        </div>
      </CardHeader>

      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto p-4"
        aria-live="polite"
        style={{ maxHeight: "calc(100vh - 260px)" }}
      >
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {busy && <TypingBubble />}
      </div>

      <CardContent className="space-y-3 border-t p-3">
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              disabled={busy}
              onClick={() => handleSend(s)}
              className="rounded-full border bg-muted/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>

        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSend();
          }}
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder='试试“我有点冷”…'
            rows={1}
            className="min-h-[42px] resize-none"
            aria-label="向 AutoMind 智能助手发送消息"
          />
          <Button
            type="submit"
            size="icon"
            disabled={busy || !input.trim()}
            aria-label="发送消息"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
