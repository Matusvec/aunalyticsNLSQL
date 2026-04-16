"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2">
        <CardTitle>Recent questions</CardTitle>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </CardHeader>
      <CardContent>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {!error && items.length === 0 && !loading ? (
          <p className="text-sm text-muted-foreground">
            No history yet — ask a question to see it here.
          </p>
        ) : null}

        {items.length > 0 ? (
          <ul className="space-y-3">
            {items.map((item) => (
              <li
                key={item.id}
                className="rounded-md border border-border/60 bg-muted/20 p-3 text-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => onPick?.(item.question)}
                    className="text-left font-medium hover:underline"
                    title="Reuse this question"
                  >
                    {item.question}
                  </button>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatTimestamp(item.created_at)}
                  </span>
                </div>
                <pre className="mt-2 overflow-x-auto rounded bg-muted px-2 py-1 text-xs">
                  <code>{item.sql}</code>
                </pre>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{item.status}</span>
                  {typeof item.confidence === "number" ? (
                    <span>
                      {Math.round(
                        (item.confidence > 1 ? item.confidence / 100 : item.confidence) * 100,
                      )}
                      % confidence
                    </span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
