"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Database,
  Gauge,
  History as HistoryIcon,
  Plus,
  Sparkles,
  X,
} from "lucide-react";

import { DatabaseSelector } from "@/components/database-selector";
import { FileUpload } from "@/components/file-upload";
import { HistoryPanel } from "@/components/history-panel";
import { QueryPanel } from "@/components/query-panel";
import { ResizeHandle, useResizable } from "@/components/resizable";
import { SchemaMap } from "@/components/schema-map";
import { SchemaSidebar } from "@/components/schema-sidebar";
import { Button } from "@/components/ui/button";
import { fetchAgentTiers, listDatabases, type AgentEvent, type AgentTier } from "@/lib/api";
import type { DatabaseEntry } from "@/lib/schema-types";
import { useSchema } from "@/hooks/useSchema";
import { useSchemaGraph } from "@/hooks/useSchemaGraph";
import { cn } from "@/lib/utils";


const TIER_FALLBACK: AgentTier[] = [
  { name: "fast", max_iterations: 3, max_submit_retries: 1, description: "1–2 tool calls. Cheapest, least accurate." },
  { name: "medium", max_iterations: 6, max_submit_retries: 2, description: "Up to ~5 tool calls. Balanced." },
  { name: "high", max_iterations: 12, max_submit_retries: 4, description: "Up to ~10 tool calls + run_query verification." },
];


export function HomePage() {
  const [databases, setDatabases] = useState<DatabaseEntry[]>([]);
  const [selectedDb, setSelectedDb] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0);

  const [tiers, setTiers] = useState<AgentTier[]>(TIER_FALLBACK);
  const [tier, setTier] = useState<string>("medium");

  const [showUpload, setShowUpload] = useState(false);

  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const [agentRunning, setAgentRunning] = useState(false);

  // Resizable layout state — persisted to localStorage.
  const [sidebarWidth, setSidebarWidth] = useResizable("nl2sql.sidebar", 288, 220, 480);
  const [rightRailWidth, setRightRailWidth] = useResizable("nl2sql.rightRail", 352, 240, 560);
  const [mapHeight, setMapHeight] = useResizable("nl2sql.schemaMap", 460, 280, 900);

  const refreshDatabases = useCallback(async (preferFilename?: string) => {
    try {
      const { databases: list } = await listDatabases();
      setListError(null);
      setDatabases(list);
      setSelectedDb(() => {
        if (preferFilename && list.some((d) => d.filename === preferFilename)) {
          return preferFilename;
        }
        return list[0]?.filename ?? null;
      });
    } catch (e: unknown) {
      setListError(e instanceof Error ? e.message : "Failed to load database list");
    }
  }, []);

  useEffect(() => {
    void refreshDatabases();
    fetchAgentTiers()
      .then((data) => {
        setTiers(data.tiers);
        setTier(data.default || "medium");
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: schemaData, loading: schemaLoading, error: schemaError } = useSchema(selectedDb);
  const { data: graphData, loading: graphLoading, error: graphError } = useSchemaGraph(selectedDb);

  const onUploadComplete = useCallback(
    (filename: string) => {
      void refreshDatabases(filename);
      setShowUpload(false);
    },
    [refreshDatabases],
  );

  return (
    <div className="flex h-screen flex-col">
      {/* Top app bar */}
      <header className="z-30 border-b border-border/60 bg-background/85 backdrop-blur">
        <div className="flex flex-wrap items-center gap-3 px-6 py-3">
          <div className="flex items-center gap-2 pr-3">
            <div className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-sm shadow-primary/30">
              <Sparkles className="size-4" aria-hidden />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">NL2SQL</div>
              <div className="text-[10px] text-muted-foreground">agent workspace</div>
            </div>
          </div>

          <div className="h-7 w-px bg-border/60" aria-hidden />

          <div className="flex min-w-[16rem] items-center gap-2">
            <Database className="size-4 shrink-0 text-primary" aria-hidden />
            <div className="min-w-0 flex-1">
              <DatabaseSelector
                databases={databases}
                value={selectedDb}
                onValueChange={(name) => setSelectedDb(name)}
              />
            </div>
          </div>

          <Button
            variant={showUpload ? "secondary" : "outline"}
            size="sm"
            onClick={() => setShowUpload((s) => !s)}
            className="gap-1.5"
          >
            {showUpload ? <X className="size-4" /> : <Plus className="size-4" />}
            {showUpload ? "Close" : "Upload"}
          </Button>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
              <Gauge className="size-3.5" aria-hidden />
              Thinking
            </span>
            <div role="radiogroup" aria-label="Thinking depth" className="flex gap-1">
              {tiers.map((t) => {
                const active = tier === t.name;
                return (
                  <button
                    key={t.name}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setTier(t.name)}
                    title={t.description}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs font-semibold capitalize transition-all",
                      active
                        ? "border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/30"
                        : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground",
                    )}
                  >
                    {t.name}
                    <span className={cn("ml-1.5 text-[10px]", active ? "opacity-90" : "opacity-60")}>
                      ≤{t.max_iterations}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {showUpload ? (
          <div className="border-t border-border/60 px-6 py-3">
            <FileUpload onUploadComplete={onUploadComplete} />
          </div>
        ) : null}

        {listError ? (
          <p className="border-t border-destructive/30 bg-destructive/10 px-6 py-2 text-sm text-destructive">
            {listError}
          </p>
        ) : null}
      </header>

      {/* Body — flex layout with draggable handles */}
      <div className="flex min-h-0 flex-1">
        {/* Left: schema sidebar */}
        <aside
          className="hidden lg:flex lg:flex-col lg:shrink-0"
          style={{ width: sidebarWidth }}
        >
          <SchemaSidebar
            dbFilename={selectedDb}
            schema={schemaData}
            loading={schemaLoading}
            error={schemaError}
            className="h-full"
          />
        </aside>

        <ResizeHandle
          orientation="horizontal"
          edge="end"
          size={sidebarWidth}
          onResize={setSidebarWidth}
          ariaLabel="Resize schema sidebar"
          className="hidden lg:block"
        />

        {/* Center: main */}
        <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          <div className="flex-1 space-y-5 px-6 py-5">
            <SchemaMap
              graph={graphData}
              loading={graphLoading}
              error={graphError}
              events={agentEvents}
              height={mapHeight}
              onHeightChange={setMapHeight}
            />

            <div className="space-y-5">
              <QueryPanel
                dbFilename={selectedDb}
                question={question}
                onQuestionChange={setQuestion}
                tier={tier}
                tiers={tiers}
                events={agentEvents}
                running={agentRunning}
                onEventsChange={setAgentEvents}
                onRunningChange={setAgentRunning}
                onAsked={() => setHistoryRefreshToken((n) => n + 1)}
              />

              <section className="xl:hidden">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <HistoryIcon className="size-4 text-primary" aria-hidden />
                  Recent questions
                </div>
                <HistoryPanel refreshToken={historyRefreshToken} onPick={setQuestion} />
              </section>
            </div>
          </div>
        </main>

        <ResizeHandle
          orientation="horizontal"
          edge="start"
          size={rightRailWidth}
          onResize={setRightRailWidth}
          ariaLabel="Resize history rail"
          className="hidden xl:block"
        />

        {/* Right: history rail */}
        <aside
          className="hidden bg-sidebar/50 xl:flex xl:flex-col xl:shrink-0 xl:overflow-y-auto"
          style={{ width: rightRailWidth }}
        >
          <div className="flex items-center gap-2 border-b border-border/60 px-5 py-3 text-sm font-semibold">
            <HistoryIcon className="size-4 text-primary" aria-hidden />
            Recent questions
          </div>
          <div className="flex-1 px-3 py-3">
            <HistoryPanel refreshToken={historyRefreshToken} onPick={setQuestion} />
          </div>
        </aside>
      </div>
    </div>
  );
}
