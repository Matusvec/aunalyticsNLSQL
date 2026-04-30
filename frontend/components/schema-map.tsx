"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Database,
  KeyRound,
  Loader2,
  Move,
  Network,
  RefreshCw,
  Table as TableIcon,
} from "lucide-react";

import type { AgentEvent } from "@/lib/api";
import type { SchemaGraph } from "@/lib/schema-types";
import { Button } from "@/components/ui/button";
import { ResizeHandle } from "@/components/resizable";
import { cn } from "@/lib/utils";

type SchemaMapProps = {
  graph: SchemaGraph | null;
  loading: boolean;
  error: string | null;
  events: AgentEvent[];
  className?: string;
  /** Canvas height in px. */
  height?: number;
  /** If provided, renders a bottom resize handle that calls this with the new height. */
  onHeightChange?: (next: number) => void;
};

type ActivityKind = "describe" | "sample" | "distinct" | "count" | "related" | "query";

type Activity = { table: string; kind: ActivityKind; at: number };

const ACTIVITY_STYLE: Record<ActivityKind, { ring: string; bg: string; label: string }> = {
  describe: {
    ring: "ring-cyan-400/70 shadow-[0_0_24px_-4px_rgba(34,211,238,0.55)]",
    bg: "bg-cyan-500/10",
    label: "describing",
  },
  sample: {
    ring: "ring-emerald-400/70 shadow-[0_0_24px_-4px_rgba(16,185,129,0.55)]",
    bg: "bg-emerald-500/10",
    label: "sampling",
  },
  distinct: {
    ring: "ring-amber-400/70 shadow-[0_0_24px_-4px_rgba(245,158,11,0.55)]",
    bg: "bg-amber-500/10",
    label: "scanning",
  },
  count: {
    ring: "ring-amber-400/60",
    bg: "bg-amber-500/10",
    label: "counting",
  },
  related: {
    ring: "ring-rose-400/70 shadow-[0_0_24px_-4px_rgba(244,63,94,0.55)]",
    bg: "bg-rose-500/10",
    label: "exploring FKs",
  },
  query: {
    ring: "ring-primary/80 shadow-[0_0_28px_-4px_oklch(0.56_0.22_282_/_0.6)]",
    bg: "bg-primary/15",
    label: "querying",
  },
};

const NODE_W = 168;
const NODE_H = 60;
const DEFAULT_CANVAS_HEIGHT = 460;
const NODE_MARGIN = 12;


/* ------------------------------------------------------------------ */
/*                       Activity extraction                          */
/* ------------------------------------------------------------------ */

function extractTablesFromSql(sql: string): string[] {
  if (!sql) return [];
  const re = /(?:FROM|JOIN|UPDATE|INTO)\s+["'`\[]?([A-Za-z_][A-Za-z0-9_]*)/gi;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(sql)) !== null) out.push(m[1]);
  return out;
}

function activitiesFromEvents(events: AgentEvent[]): Activity[] {
  const out: Activity[] = [];
  let t = 0;
  for (const e of events) {
    t += 1;
    if (e.type !== "tool_call") continue;
    const args = (e.args ?? {}) as Record<string, unknown>;
    const name = e.name;
    if (name === "describe_table" && typeof args.table === "string") out.push({ table: args.table, kind: "describe", at: t });
    else if (name === "sample_rows" && typeof args.table === "string") out.push({ table: args.table, kind: "sample", at: t });
    else if (name === "distinct_values" && typeof args.table === "string") out.push({ table: args.table, kind: "distinct", at: t });
    else if (name === "count_rows" && typeof args.table === "string") out.push({ table: args.table, kind: "count", at: t });
    else if (name === "find_related" && typeof args.table === "string") out.push({ table: args.table, kind: "related", at: t });
    else if (name === "run_query" && typeof args.sql === "string")
      for (const x of extractTablesFromSql(args.sql)) out.push({ table: x, kind: "query", at: t });
    else if (name === "submit_sql" && typeof args.sql === "string")
      for (const x of extractTablesFromSql(args.sql)) out.push({ table: x, kind: "query", at: t });
  }
  return out;
}


/* ------------------------------------------------------------------ */
/*                    Force-directed graph layout                     */
/* ------------------------------------------------------------------ */

type NodeState = { id: string; x: number; y: number; vx: number; vy: number };

function deterministicSeed(id: string, n: number) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  const a = Math.abs(Math.sin(h * 1.7)) % 1;
  return { a, idx: Math.abs(h) % n };
}

function computeForceLayout(
  tables: string[],
  edges: Array<{ from: string; to: string }>,
  width: number,
  height: number,
): Map<string, { x: number; y: number }> {
  const n = tables.length;
  if (n === 0) return new Map();
  if (n === 1) return new Map([[tables[0], { x: width / 2, y: height / 2 }]]);

  const nodes: NodeState[] = tables.map((id, i) => {
    const angle = (i / n) * Math.PI * 2;
    const r = Math.min(width, height) * 0.35;
    const seed = deterministicSeed(id, n);
    const jitter = (seed.a - 0.5) * 30;
    return {
      id,
      x: width / 2 + Math.cos(angle) * (r + jitter),
      y: height / 2 + Math.sin(angle) * (r + jitter),
      vx: 0,
      vy: 0,
    };
  });

  const ideal = Math.min(width, height) / Math.sqrt(n) * 0.85;
  const k = ideal;
  const iterations = 280;

  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < n; i++) {
      const a = nodes[i];
      a.vx = 0;
      a.vy = 0;
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        const b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distSq = dx * dx + dy * dy;
        const dist = Math.sqrt(distSq) || 0.01;
        const force = (k * k) / dist;
        a.vx += (dx / dist) * force;
        a.vy += (dy / dist) * force;
      }
    }

    for (const e of edges) {
      const a = nodes.find((nn) => nn.id === e.from);
      const b = nodes.find((nn) => nn.id === e.to);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const force = (dist * dist) / k;
      a.vx += (dx / dist) * force;
      a.vy += (dy / dist) * force;
      b.vx -= (dx / dist) * force;
      b.vy -= (dy / dist) * force;
    }

    for (const a of nodes) {
      const dx = width / 2 - a.x;
      const dy = height / 2 - a.y;
      a.vx += dx * 0.012;
      a.vy += dy * 0.012;
    }

    const cool = 1 - iter / iterations;
    const maxStep = k * 0.18 * cool + 0.5;
    for (const a of nodes) {
      const v = Math.sqrt(a.vx * a.vx + a.vy * a.vy) || 0.0001;
      const step = Math.min(v, maxStep);
      a.x += (a.vx / v) * step;
      a.y += (a.vy / v) * step;
      a.x = Math.max(NODE_W / 2 + NODE_MARGIN, Math.min(width - NODE_W / 2 - NODE_MARGIN, a.x));
      a.y = Math.max(NODE_H / 2 + NODE_MARGIN, Math.min(height - NODE_H / 2 - NODE_MARGIN, a.y));
    }
  }

  const map = new Map<string, { x: number; y: number }>();
  for (const node of nodes) map.set(node.id, { x: node.x, y: node.y });
  return map;
}


/* ------------------------------------------------------------------ */
/*                         Visual edge geometry                       */
/* ------------------------------------------------------------------ */

function edgePath(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const cx1 = from.x + dx * 0.45;
  const cy1 = from.y + dy * 0.05;
  const cx2 = to.x - dx * 0.45;
  const cy2 = to.y - dy * 0.05;
  return `M ${from.x},${from.y} C ${cx1},${cy1} ${cx2},${cy2} ${to.x},${to.y}`;
}


/* ------------------------------------------------------------------ */
/*                              Component                             */
/* ------------------------------------------------------------------ */

export function SchemaMap({
  graph,
  loading,
  error,
  events,
  className,
  height = DEFAULT_CANVAS_HEIGHT,
  onHeightChange,
}: SchemaMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(960);

  useLayoutEffect(() => {
    if (!containerRef.current) return;
    setWidth(containerRef.current.clientWidth);
  }, [graph]);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver(() => {
      setWidth(el.clientWidth);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Manual position overrides — populated as the user drags nodes.
  const [manualPositions, setManualPositions] = useState<Map<string, { x: number; y: number }>>(
    () => new Map(),
  );
  const [draggingTable, setDraggingTable] = useState<string | null>(null);

  // Reset manual positions when the user switches databases (graph identity changes).
  const graphKey = graph?.database ?? null;
  const lastGraphKey = useRef<string | null>(null);
  useEffect(() => {
    if (graphKey !== lastGraphKey.current) {
      setManualPositions(new Map());
      lastGraphKey.current = graphKey;
    }
  }, [graphKey]);

  const computedPositions = useMemo(() => {
    if (!graph) return new Map<string, { x: number; y: number }>();
    return computeForceLayout(
      graph.tables.map((t) => t.name),
      graph.foreign_keys.map((fk) => ({ from: fk.from_table, to: fk.to_table })),
      Math.max(320, width),
      height,
    );
  }, [graph, width, height]);

  const positions = useMemo(() => {
    if (manualPositions.size === 0) return computedPositions;
    const merged = new Map(computedPositions);
    for (const [name, pos] of manualPositions) {
      merged.set(name, pos);
    }
    return merged;
  }, [computedPositions, manualPositions]);

  const [hoveredTable, setHoveredTable] = useState<string | null>(null);

  // Tick to animate activity fading (only while events keep arriving)
  const [, setNow] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setNow((n) => n + 1), 250);
    return () => clearInterval(id);
  }, []);

  const activeMap = useMemo(() => {
    const list = activitiesFromEvents(events);
    if (list.length === 0) return new Map<string, ActivityKind>();
    const latest = new Map<string, { kind: ActivityKind; at: number }>();
    for (const a of list) {
      const prior = latest.get(a.table);
      if (!prior || a.at >= prior.at) latest.set(a.table, { kind: a.kind, at: a.at });
    }
    const maxAt = list[list.length - 1].at;
    const fresh = new Map<string, ActivityKind>();
    for (const [name, info] of latest) {
      if (maxAt - info.at <= 4) fresh.set(name, info.kind);
    }
    return fresh;
  }, [events]);

  const startNodeDrag = useCallback(
    (e: React.PointerEvent, tableName: string) => {
      e.preventDefault();
      e.stopPropagation();
      const current = positions.get(tableName);
      if (!current) return;

      const startClientX = e.clientX;
      const startClientY = e.clientY;
      const startX = current.x;
      const startY = current.y;
      const localWidth = Math.max(320, width);
      const localHeight = height;

      let didMove = false;
      setDraggingTable(tableName);

      const onMove = (ev: PointerEvent) => {
        const dx = ev.clientX - startClientX;
        const dy = ev.clientY - startClientY;
        if (!didMove && Math.abs(dx) + Math.abs(dy) < 3) return; // suppress tiny accidental moves
        didMove = true;
        const x = Math.max(NODE_W / 2 + NODE_MARGIN, Math.min(localWidth - NODE_W / 2 - NODE_MARGIN, startX + dx));
        const y = Math.max(NODE_H / 2 + NODE_MARGIN, Math.min(localHeight - NODE_H / 2 - NODE_MARGIN, startY + dy));
        setManualPositions((prev) => {
          const next = new Map(prev);
          next.set(tableName, { x, y });
          return next;
        });
      };

      const onUp = () => {
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        setDraggingTable(null);
      };

      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      document.body.style.cursor = "grabbing";
      document.body.style.userSelect = "none";
    },
    [positions, width, height],
  );

  const resetLayout = useCallback(() => {
    setManualPositions(new Map());
  }, []);

  if (error) {
    return (
      <section
        className={cn("rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive", className)}
      >
        Schema map: {error}
      </section>
    );
  }

  if (loading || !graph) {
    return (
      <section
        className={cn(
          "flex min-h-[8rem] items-center justify-center gap-2 rounded-2xl border border-border/60 surface-card text-sm text-muted-foreground",
          className,
        )}
      >
        {loading ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Building map…
          </>
        ) : (
          <>
            <Database className="size-4" aria-hidden />
            Pick a database to see the map.
          </>
        )}
      </section>
    );
  }

  return (
    <section className={cn("overflow-hidden rounded-2xl border border-border/60 surface-card", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-5 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Network className="size-4 text-primary" aria-hidden />
          Schema map
        </div>
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          <span>{graph.tables.length} tables</span>
          <span>· {graph.foreign_keys.length} FKs</span>
          {hoveredTable ? (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-primary">{hoveredTable}</span>
          ) : null}
          {manualPositions.size > 0 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={resetLayout}
              className="h-6 gap-1 px-2 text-[10px]"
              title="Reset layout to auto"
            >
              <RefreshCw className="size-3" aria-hidden />
              Reset
            </Button>
          ) : null}
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative bg-[radial-gradient(ellipse_at_center,_oklch(0.97_0.012_282_/_0.6),transparent_75%)]"
        style={{ height }}
      >
        {/* SVG uses pixel coords matching container — no viewBox stretching */}
        <svg
          aria-hidden
          className="pointer-events-none absolute inset-0"
          width={Math.max(320, width)}
          height={height}
        >
          <defs>
            <marker
              id="schema-arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
            </marker>
          </defs>

          {graph.foreign_keys.map((fk, i) => {
            const from = positions.get(fk.from_table);
            const to = positions.get(fk.to_table);
            if (!from || !to) return null;

            const fromActive = activeMap.has(fk.from_table);
            const toActive = activeMap.has(fk.to_table);
            const bothActive = fromActive && toActive;

            const hovered =
              hoveredTable !== null &&
              (fk.from_table === hoveredTable || fk.to_table === hoveredTable);
            const dim = hoveredTable !== null && !hovered;

            const stroke = bothActive
              ? "oklch(0.56 0.22 282)"
              : fromActive || toActive
                ? "oklch(0.65 0.18 282)"
                : hovered
                  ? "oklch(0.56 0.22 282)"
                  : "oklch(0.78 0.03 280)";
            const strokeWidth = bothActive ? 2.4 : hovered ? 2 : 1.2;
            const opacity = dim ? 0.18 : bothActive ? 1 : hovered ? 0.95 : 0.55;

            return (
              <path
                key={`${fk.from_table}.${fk.from_column}->${fk.to_table}.${fk.to_column}-${i}`}
                d={edgePath(from, to)}
                fill="none"
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeOpacity={opacity}
                markerEnd="url(#schema-arrow)"
                className={cn(
                  "transition-[stroke-width,stroke-opacity] duration-200",
                  draggingTable && "transition-none",
                )}
                style={{
                  color: stroke,
                  filter: bothActive ? "drop-shadow(0 0 6px oklch(0.56 0.22 282 / 0.5))" : undefined,
                }}
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {graph.tables.map((table) => {
          const pos = positions.get(table.name);
          if (!pos) return null;
          const kind = activeMap.get(table.name);
          const style = kind ? ACTIVITY_STYLE[kind] : null;
          const pkCount = table.columns.filter((c) => c.primary_key).length;
          const isHovered = hoveredTable === table.name;
          const isDragging = draggingTable === table.name;
          const dim = hoveredTable !== null && !isHovered && !isDragging;
          return (
            <div
              key={table.name}
              onPointerDown={(e) => startNodeDrag(e, table.name)}
              onMouseEnter={() => !draggingTable && setHoveredTable(table.name)}
              onMouseLeave={() => !draggingTable && setHoveredTable(null)}
              className={cn(
                "absolute select-none rounded-xl border bg-background/90 p-2.5",
                "ring-2 ring-transparent",
                style ? `${style.ring} ${style.bg}` : "border-border/60",
                isHovered && "border-primary/60 shadow-md",
                dim && "opacity-40",
                isDragging
                  ? "cursor-grabbing shadow-lg shadow-primary/20 ring-primary/40"
                  : "cursor-grab",
                draggingTable ? "transition-none" : "transition-all duration-300",
              )}
              style={{
                width: NODE_W,
                left: pos.x - NODE_W / 2,
                top: pos.y - NODE_H / 2,
                touchAction: "none",
              }}
              title="Drag to reposition"
            >
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-md transition-colors",
                    style ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary",
                  )}
                >
                  <TableIcon className="size-3.5" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-mono text-xs font-semibold">{table.name}</div>
                  <div className="text-[10px] text-muted-foreground">
                    {table.row_count != null ? `${table.row_count.toLocaleString()} rows` : "? rows"}
                    <span className="mx-1">·</span>
                    {table.columns.length} col{table.columns.length === 1 ? "" : "s"}
                    {pkCount > 0 ? (
                      <span className="ml-1 inline-flex items-center gap-0.5 text-primary">
                        <KeyRound className="size-2.5" aria-hidden />
                        {pkCount}
                      </span>
                    ) : null}
                  </div>
                </div>
                <Move
                  className="size-3 shrink-0 text-muted-foreground/50"
                  aria-hidden
                />
              </div>

              {style ? (
                <div className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-background/90 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground">
                  <span className="size-1.5 animate-pulse rounded-full bg-primary" aria-hidden />
                  {style.label}
                </div>
              ) : null}
            </div>
          );
        })}

        {graph.tables.length === 0 ? (
          <div className="absolute inset-0 grid place-items-center text-sm text-muted-foreground">
            No tables in this database.
          </div>
        ) : null}
      </div>

      {/* Bottom resize handle (drag down to expand) */}
      {onHeightChange ? (
        <ResizeHandle
          orientation="vertical"
          edge="end"
          size={height}
          onResize={onHeightChange}
          ariaLabel="Resize schema map height"
          className="border-t border-border/60"
        />
      ) : null}
    </section>
  );
}
