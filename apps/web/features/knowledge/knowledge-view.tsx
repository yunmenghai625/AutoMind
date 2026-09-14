"use client";

import { BookOpen, ChevronDown, FileText, Send, Sparkles } from "lucide-react";
import * as React from "react";
import { PageHeader } from "@/components/common/page-header";
import { MockBadge } from "@/components/common/mock-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { getKnowledgeSources, queryKnowledge } from "@/lib/api/knowledgeApi";
import type {
  Citation,
  KnowledgeAnswer,
  KnowledgeMessage,
  KnowledgeSource,
} from "@/types/knowledge";

const SUGGESTION = "胎压报警灯亮了还能继续开吗？";

function SourceList() {
  const [sources, setSources] = React.useState<KnowledgeSource[] | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    getKnowledgeSources()
      .then(setSources)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="text-sm text-destructive">
        Failed to load knowledge sources. Please retry.
      </p>
    );
  }
  if (!sources) {
    return (
      <div className="space-y-2" aria-busy="true">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-muted/50" />
        ))}
      </div>
    );
  }
  return (
    <ul className="space-y-2 py-1">
      {sources.map((s) => (
        <li
          key={s.id}
          className="group flex items-start gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-muted/40"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <BookOpen className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1 space-y-0.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">{s.title}</p>
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px]",
                  s.status === "syncing"
                    ? "text-amber-500"
                    : "text-success",
                )}
              >
                {s.status}
              </Badge>
            </div>
            <p className="truncate text-xs text-muted-foreground">
              {s.description}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {s.documents} documents · updated {s.updatedAt}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <div className="flex items-center gap-2 text-xs">
        <FileText className="h-3.5 w-3.5 text-primary" />
        <span className="font-medium text-foreground">{citation.source}</span>
        <span className="text-muted-foreground">
          {citation.chapter ? `· ${citation.chapter}` : ""}
          {citation.page ? ` · p.${citation.page}` : ""}
        </span>
      </div>
      <blockquote className="mt-1.5 border-l-2 border-primary/40 pl-2 text-xs text-muted-foreground">
        {citation.snippet}
      </blockquote>
    </div>
  );
}

function RetrievalDetails({ answer }: { answer: KnowledgeAnswer }) {
  const [open, setOpen] = React.useState(false);
  const r = answer.retrieval;
  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Retrieval Details
        </span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
        />
      </button>
      {open && (
        <div className="space-y-2 border-t p-3 text-xs">
          <div>
            <p className="text-muted-foreground">Original Query</p>
            <p className="text-foreground">{r.originalQuery}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Rewritten Query</p>
            <p className="text-foreground">{r.rewrittenQuery}</p>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <Badge variant="outline">Retrieved Documents · {r.retrievedDocuments}</Badge>
            <Badge variant="outline">
              Reranker · {r.rerankerEnabled ? "Enabled" : "Disabled"}
            </Badge>
            <Badge variant="outline">
              {r.vectorSearchMs + r.rerankMs}ms
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}

export function KnowledgeView() {
  const [query, setQuery] = React.useState("");
  const [messages, setMessages] = React.useState<KnowledgeMessage[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(false);

  const ask = async (raw?: string) => {
    const text = (raw ?? query).trim();
    if (!text || loading) return;
    setLoading(true);
    setError(false);
    const userMsg: KnowledgeMessage = {
      id: `kq-${Date.now()}`,
      role: "user",
      content: text,
      at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    try {
      const answer = await queryKnowledge(text);
      const asst: KnowledgeMessage = {
        id: `ka-${Date.now()}`,
        role: "assistant",
        content: answer.answer,
        at: new Date().toISOString(),
        meta: { citations: answer.citations, retrieval: answer.retrieval },
      };
      setMessages((prev) => [...prev, asst]);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <PageHeader
        title="Knowledge"
        badge={<MockBadge />}
        description="Automotive knowledge RAG grounded in the vehicle manuals and guides. Answers include citations and retrieval details."
      />
      <div className="mt-6 grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Card className="self-start">
          <CardHeader className="py-3">
            <CardTitle className="text-base">Knowledge Sources</CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <SourceList />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 border-b py-3">
            <CardTitle className="text-base">AI RAG Assistant</CardTitle>
            <MockBadge />
          </CardHeader>
          <CardContent className="flex min-h-[520px] flex-col gap-4 p-4">
            <div className="flex items-center gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void ask()}
                placeholder='Ask about your car, e.g. "胎压报警灯亮了还能继续开吗？"'
                aria-label="Ask the knowledge base"
              />
              <Button
                onClick={() => void ask()}
                disabled={loading || !query.trim()}
                aria-label="Send knowledge question"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

            <button
              type="button"
              onClick={() => void ask(SUGGESTION)}
              disabled={loading}
              className="self-start rounded-full border bg-muted/40 px-3 py-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              {SUGGESTION}
            </button>

            <div className="flex-1 space-y-4" aria-live="polite">
              {messages.length === 0 && !loading && (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
                  <Sparkles className="h-8 w-8 text-primary/50" />
                  <p className="text-sm">
                    Ask anything about your vehicle. Grounded in your manuals.
                  </p>
                </div>
              )}

              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "space-y-2",
                    m.role === "user" ? "flex justify-end" : "",
                  )}
                >
                  {m.role === "user" ? (
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground">
                      {m.content}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="rounded-2xl rounded-tl-sm border bg-card px-3.5 py-2.5 text-sm leading-relaxed">
                        {m.content.split("\n\n").map((para, i) => (
                          <p key={i} className={i > 0 ? "mt-2" : ""}>
                            {para}
                          </p>
                        ))}
                      </div>
                      {m.meta?.citations && (
                        <div className="space-y-2 pl-2">
                          {m.meta.citations.map((c, i) => (
                            <CitationCard key={i} citation={c} />
                          ))}
                        </div>
                      )}
                      {m.meta?.retrieval && (
                        <div className="pl-2">
                          <RetrievalDetails
                            answer={{
                              answer: m.content,
                              citations: m.meta.citations ?? [],
                              retrieval: m.meta.retrieval,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                  Retrieving documents & reranking…
                </div>
              )}
            </div>

            {error && (
              <>
                <Separator />
                <p className="text-center text-sm text-destructive">
                  AutoMind API is temporarily unavailable.{" "}
                  <button
                    type="button"
                    className="underline"
                    onClick={() => void ask(messages.filter((m) => m.role === "user").at(-1)?.content)}
                  >
                    Retry
                  </button>
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
