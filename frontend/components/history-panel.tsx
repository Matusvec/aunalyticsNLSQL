"use client";

import { useCallback, useEffect, useState } from "react";

import { Loader2, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchHistory, type HistoryItem } from "@/lib/api";

type HistoryPanelProps = {
  refreshToken?: number;
  onPick?: (question: string) => void;
};

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export function HistoryPanel({ refreshToken, onPick }: HistoryPanelProps) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const history = await fetchHistory();
      setItems(history);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshToken]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">
          {items.length > 0
            ? `${items.length} item${items.length === 1 ? "" : "s"}`
            : "No history yet"}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void load()}
          disabled={loading}
          className="h-7 gap-1.5 px-2 text-xs"
        >
          {loading ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RotateCw className="size-3.5" />
          )}
          Refresh
        </Button>
      </div>

      {error ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {!error && items.length === 0 && !loading ? (
        <p className="text-sm text-muted-foreground">
          Ask a question and your past queries will show up here.
        </p>
      ) : null}

      {items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="rounded-xl border border-border/60 bg-background/60 p-3 transition-colors hover:border-primary/30"
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  onClick={() => onPick?.(item.question)}
                  className="text-left text-sm font-medium hover:text-primary"
                  title="Reuse this question"
                >
                  {item.question}
                </button>
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  {formatTimestamp(item.created_at)}
                </span>
              </div>
              <pre className="mt-1.5 max-h-24 overflow-x-auto overflow-y-auto rounded-md bg-muted/60 px-2 py-1.5 text-[11px]">
                <code className="font-mono">{item.sql}</code>
              </pre>
              <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
                  {item.status}
                </span>
                {typeof item.confidence === "number" ? (
                  <span>
                    {Math.round(
                      (item.confidence > 1 ? item.confidence / 100 : item.confidence) * 100,
                    )}
                    %
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
