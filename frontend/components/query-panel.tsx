"use client";

import { useCallback, useRef, useState } from "react";

import { Loader2, Send, Sparkles } from "lucide-react";

import { AgentTrace } from "@/components/agent-trace";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ResultsTable } from "@/components/results-table";
import {
  askQuestionStream,
  type AgentEvent,
  type AgentTier,
  type AskResponse,
} from "@/lib/api";

type QueryPanelProps = {
  dbFilename: string | null;
  question: string;
  onQuestionChange: (value: string) => void;
  tier: string;
  tiers: AgentTier[];
  events: AgentEvent[];
  running: boolean;
  onEventsChange: (events: AgentEvent[] | ((prev: AgentEvent[]) => AgentEvent[])) => void;
  onRunningChange: (running: boolean) => void;
  onAsked?: () => void;
};

const SAMPLE_PROMPTS = [
  "Show the top 5 customers by total spending",
  "Which artist has the most albums?",
  "Average invoice total per country",
];


export function QueryPanel({
  dbFilename,
  question,
  onQuestionChange,
  tier,
  tiers,
  events,
  running,
  onEventsChange,
  onRunningChange,
  onAsked,
}: QueryPanelProps) {
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loading = running;

  const abortRef = useRef<AbortController | null>(null);

  const canSubmit = Boolean(dbFilename) && question.trim().length > 0 && !loading;

  const tierMeta = tiers.find((t) => t.name === tier);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!dbFilename || !question.trim()) return;

    onRunningChange(true);
    setError(null);
    setResult(null);
    onEventsChange([]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await askQuestionStream(
        dbFilename,
        question.trim(),
        200,
        tier,
        (e) => {
          onEventsChange((prev) => [...prev, e]);
          if (e.type === "final") {
            setResult({
              db_filename: e.db_filename,
              question: e.question,
              sql: e.sql,
              columns: e.columns,
              rows: e.rows,
              row_count: e.row_count,
              limit_applied: e.limit_applied,
              confidence: e.confidence,
              assumptions: e.assumptions,
              tier: e.tier,
            });
            onAsked?.();
          } else if (e.type === "error") {
            setError(e.detail || `Error ${e.status}`);
          }
        },
        controller.signal,
      );
    } catch (e) {
      if ((e as Error)?.name === "AbortError") {
        setError("Cancelled.");
      } else {
        setError(e instanceof Error ? e.message : "Ask failed");
      }
    } finally {
      onRunningChange(false);
      abortRef.current = null;
    }
  }

  const showSplit = events.length > 0 || loading;

  return (
    <div className="space-y-6">
      {/* Question card */}
      <section className="overflow-hidden rounded-2xl border border-border/60 surface-card">
        <div className="border-b border-border/60 bg-gradient-to-r from-primary/8 via-transparent to-accent/40 px-6 py-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="size-4 text-primary" aria-hidden />
              Ask a question
            </div>
            <span className="rounded-full border border-primary/20 bg-primary/5 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
              {tier}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {dbFilename ? (
              <>
                Querying <span className="font-mono font-medium">{dbFilename}</span>
                {tierMeta?.description ? <> · {tierMeta.description}</> : null}
              </>
            ) : (
              "Pick a database first"
            )}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div className="space-y-2">
            <Label htmlFor="question" className="sr-only">
              Question
            </Label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => onQuestionChange(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && canSubmit) {
                  e.preventDefault();
                  void handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              placeholder={
                dbFilename
                  ? "e.g. Show the top 5 customers by total spending"
                  : "Select a database to start"
              }
              disabled={!dbFilename || loading}
              rows={3}
              className="w-full resize-y rounded-lg border border-input bg-background/50 px-4 py-3 text-base outline-none transition-colors focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <p className="text-[11px] text-muted-foreground">
              Tip: press{" "}
              <kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono text-[10px]">
                ⌘/Ctrl + Enter
              </kbd>{" "}
              to send
            </p>
          </div>

          {!question.trim() && dbFilename ? (
            <div className="flex flex-wrap gap-2">
              {SAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onQuestionChange(prompt)}
                  className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!canSubmit} className="gap-2">
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  Generating
                </>
              ) : (
                <>
                  <Send className="size-4" aria-hidden />
                  Ask
                </>
              )}
            </Button>
            {loading ? (
              <Button type="button" variant="ghost" size="sm" onClick={handleStop}>
                Stop
              </Button>
            ) : null}
            {error ? <span className="text-sm text-destructive">{error}</span> : null}
          </div>
        </form>
      </section>

      {/* Trace + Results — side by side on lg+ */}
      {showSplit ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[20rem_minmax(0,1fr)] xl:grid-cols-[22rem_minmax(0,1fr)]">
          <div className="lg:sticky lg:top-32 lg:self-start">
            <AgentTrace events={events} active={loading} />
          </div>

          <div className="min-w-0">
            {result ? (
              <div className="rounded-2xl border border-border/60 surface-card p-6">
                <ResultsTable result={result} />
              </div>
            ) : (
              <div className="flex h-full min-h-[16rem] items-center justify-center rounded-2xl border border-dashed border-border/60 bg-muted/20 px-6 text-center text-sm text-muted-foreground">
                {loading ? "Working — results will appear here when the agent submits." : "No results yet."}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
