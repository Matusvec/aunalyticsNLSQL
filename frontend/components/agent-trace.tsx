"use client";

import { useEffect, useRef } from "react";

import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronRight,
  Database,
  Eye,
  GitBranch,
  Hash,
  Loader2,
  RotateCw,
  Search,
  Shuffle,
  Table as TableIcon,
} from "lucide-react";

import type { AgentEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

type AgentTraceProps = {
  events: AgentEvent[];
  active: boolean;
  className?: string;
};

const TOOL_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  list_tables: Database,
  describe_table: TableIcon,
  sample_rows: Eye,
  distinct_values: Hash,
  count_rows: Activity,
  find_related: GitBranch,
  search_value: Search,
  run_query: Brain,
  submit_sql: CheckCircle2,
};

function shortJson(value: unknown, max = 90): string {
  try {
    const s = JSON.stringify(value);
    if (!s) return "";
    return s.length > max ? `${s.slice(0, max - 1)}…` : s;
  } catch {
    return String(value);
  }
}

type Row = {
  key: string;
  iteration?: number;
  Icon: React.ComponentType<{ className?: string }>;
  iconClass: string;
  title: string;
  detail?: string;
  status: "running" | "ok" | "warn" | "error" | "info";
  result?: string;
};

function buildRows(events: AgentEvent[]): Row[] {
  // Pair tool_call with the matching tool_result (by name + iteration order),
  // and surface non-paired events (start, iteration, submit_*, nudge) inline.
  const rows: Row[] = [];
  const pendingToolCalls = new Map<string, number>(); // key = `${iter}:${name}` → row index

  events.forEach((event, idx) => {
    switch (event.type) {
      case "start":
        rows.push({
          key: `start-${idx}`,
          Icon: Activity,
          iconClass: "text-primary",
          title: `Tier: ${event.tier}`,
          detail: `up to ${event.max_iterations} iterations · ${event.max_submit_retries} submit retries · ${event.model}`,
          status: "info",
        });
        break;

      case "iteration":
        rows.push({
          key: `iter-${event.iteration}-${idx}`,
          Icon: ChevronRight,
          iconClass: "text-muted-foreground",
          title: `Iteration ${event.iteration}`,
          status: "info",
        });
        break;

      case "tool_call": {
        const Icon = TOOL_ICON[event.name] ?? Brain;
        const argDetail = Object.keys(event.args ?? {}).length
          ? shortJson(event.args)
          : undefined;
        const idxRow = rows.length;
        rows.push({
          key: `call-${event.iteration}-${event.name}-${idx}`,
          iteration: event.iteration,
          Icon,
          iconClass: "text-primary",
          title: event.name,
          detail: argDetail,
          status: event.name === "submit_sql" ? "info" : "running",
        });
        pendingToolCalls.set(`${event.iteration}:${event.name}`, idxRow);
        break;
      }

      case "tool_result": {
        const key = `${event.iteration}:${event.name}`;
        const rowIdx = pendingToolCalls.get(key);
        const summary = event.summary ?? {};
        const text = shortJson(summary, 140);
        if (rowIdx !== undefined) {
          const row = rows[rowIdx];
          rows[rowIdx] = {
            ...row,
            status: "ok",
            result: text,
          };
          pendingToolCalls.delete(key);
        } else {
          rows.push({
            key: `result-${event.iteration}-${event.name}-${idx}`,
            iteration: event.iteration,
            Icon: TOOL_ICON[event.name] ?? Brain,
            iconClass: "text-primary",
            title: event.name,
            status: "ok",
            result: text,
          });
        }
        break;
      }

      case "submit_failed":
        rows.push({
          key: `submit-fail-${event.attempt}-${idx}`,
          Icon: RotateCw,
          iconClass: "text-amber-500",
          title: `submit_sql failed (attempt ${event.attempt}/${event.max_attempts})`,
          detail: event.error,
          status: "warn",
          result: event.sql,
        });
        break;

      case "submit_ok":
        rows.push({
          key: `submit-ok-${idx}`,
          Icon: CheckCircle2,
          iconClass: "text-emerald-500",
          title: "submit_sql passed validation",
          detail:
            event.confidence != null
              ? `${Math.round((event.confidence > 1 ? event.confidence / 100 : event.confidence) * 100)}% confidence`
              : undefined,
          status: "ok",
        });
        break;

      case "nudge":
        rows.push({
          key: `nudge-${idx}`,
          Icon: Shuffle,
          iconClass: "text-muted-foreground",
          title: `Nudge: ${event.reason}`,
          status: "info",
        });
        break;

      case "error":
        rows.push({
          key: `error-${idx}`,
          Icon: AlertTriangle,
          iconClass: "text-destructive",
          title: `Error · ${event.status}`,
          detail: event.detail,
          status: "error",
        });
        break;

      // start/brief/model_text/request_id/final intentionally don't add visible rows here.
      default:
        break;
    }
  });

  return rows;
}

const STATUS_CLASSES: Record<Row["status"], string> = {
  running: "bg-primary/5 border-primary/20",
  ok: "bg-emerald-500/5 border-emerald-500/20",
  warn: "bg-amber-500/5 border-amber-500/30",
  error: "bg-destructive/10 border-destructive/30",
  info: "bg-muted/40 border-border/60",
};

export function AgentTrace({ events, active, className }: AgentTraceProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rows = buildRows(events);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [rows.length]);

  if (rows.length === 0 && !active) return null;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl border border-border/60 surface-card",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-5 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Brain className="size-4 text-primary" aria-hidden />
          Agent trace
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {active ? (
            <>
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
              thinking…
            </>
          ) : (
            <span>{rows.length} step{rows.length === 1 ? "" : "s"}</span>
          )}
        </div>
      </div>

      <div ref={containerRef} className="max-h-80 space-y-1.5 overflow-y-auto p-3">
        {rows.map((row) => (
          <div
            key={row.key}
            className={cn(
              "flex items-start gap-3 rounded-lg border px-3 py-2 text-sm transition-colors",
              STATUS_CLASSES[row.status],
            )}
          >
            <div className="mt-0.5 shrink-0">
              {row.status === "running" ? (
                <Loader2 className={cn("size-4 animate-spin", row.iconClass)} aria-hidden />
              ) : (
                <row.Icon className={cn("size-4", row.iconClass)} aria-hidden />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{row.title}</span>
                {row.iteration ? (
                  <span className="text-[10px] uppercase text-muted-foreground">
                    iter {row.iteration}
                  </span>
                ) : null}
              </div>
              {row.detail ? (
                <div className="font-mono text-xs text-muted-foreground break-words">
                  {row.detail}
                </div>
              ) : null}
              {row.result ? (
                <div className="mt-1 truncate font-mono text-[11px] text-foreground/80">
                  → {row.result}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
