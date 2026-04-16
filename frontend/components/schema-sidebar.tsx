"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { SchemaPayload } from "@/lib/schema-types";
import { cn } from "@/lib/utils";

export type SchemaSidebarProps = {
  dbFilename: string | null;
  schema: SchemaPayload | null;
  loading: boolean;
  error: string | null;
  className?: string;
};

/**
 * Task 4: collapsible sidebar listing tables and columns (types + PK) from GET /api/schema.
 */
export function SchemaSidebar({ dbFilename, schema, loading, error, className }: SchemaSidebarProps) {
  if (!dbFilename) {
    return (
      <aside
        className={cn(
          "flex w-full max-w-sm flex-col border-r border-border bg-sidebar p-4 text-sidebar-foreground",
          className,
        )}
      >
        <h2 className="mb-2 text-sm font-semibold tracking-tight">Schema</h2>
        <p className="text-sm text-muted-foreground">Select a database to view tables and columns.</p>
      </aside>
    );
  }

  if (loading) {
    return (
      <aside
        className={cn(
          "flex w-full max-w-sm flex-col border-r border-border bg-sidebar p-4 text-sidebar-foreground",
          className,
        )}
      >
        <h2 className="mb-2 text-sm font-semibold tracking-tight">Schema</h2>
        <p className="text-sm text-muted-foreground">Loading schema for {dbFilename}…</p>
      </aside>
    );
  }

  if (error) {
    return (
      <aside
        className={cn(
          "flex w-full max-w-sm flex-col border-r border-border bg-sidebar p-4 text-sidebar-foreground",
          className,
        )}
      >
        <h2 className="mb-2 text-sm font-semibold tracking-tight">Schema</h2>
        <p className="text-sm text-destructive">{error}</p>
      </aside>
    );
  }

  const tables = schema?.tables ?? [];

  if (tables.length === 0) {
    return (
      <aside
        className={cn(
          "flex w-full max-w-sm flex-col border-r border-border bg-sidebar p-4 text-sidebar-foreground",
          className,
        )}
      >
        <h2 className="mb-2 text-sm font-semibold tracking-tight">Schema</h2>
        <p className="text-sm text-muted-foreground">No tables found in this database.</p>
      </aside>
    );
  }

  const defaultOpen = tables.map((t) => t.table);

  return (
    <aside
      className={cn(
        "flex h-full w-full max-w-sm flex-col overflow-hidden border-r border-border bg-sidebar text-sidebar-foreground",
        className,
      )}
    >
      <div className="border-b border-sidebar-border px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight">Schema</h2>
        <p className="truncate text-xs text-muted-foreground" title={schema?.database}>
          {schema?.database ?? dbFilename}
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2">
        <Accordion multiple defaultValue={defaultOpen} className="w-full">
          {tables.map((t) => (
            <AccordionItem key={t.table} value={t.table}>
              <AccordionTrigger className="px-2 text-sm">
                <span className="font-medium">{t.table}</span>
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {t.columns.length} column{t.columns.length === 1 ? "" : "s"}
                </span>
              </AccordionTrigger>
              <AccordionContent className="px-2 pb-2">
                <ul className="space-y-1.5 text-xs">
                  {t.columns.map((col) => (
                    <li
                      key={`${t.table}-${col.name}`}
                      className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 rounded-md bg-muted/40 px-2 py-1"
                    >
                      <span className="font-mono font-medium text-foreground">{col.name}</span>
                      <span className="text-muted-foreground">{col.type || "ANY"}</span>
                      {col.primary_key ? (
                        <span className="rounded bg-primary/15 px-1.5 py-0 text-[10px] font-medium uppercase text-primary">
                          PK
                        </span>
                      ) : null}
                      {col.notnull && !col.primary_key ? (
                        <span className="text-[10px] text-muted-foreground">NOT NULL</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </aside>
  );
}
