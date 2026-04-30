"use client";

import { Database, KeyRound, Loader2, Table as TableIcon } from "lucide-react";

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

function Shell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <aside
      className={cn(
        "flex h-full w-full flex-col overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:max-w-xs",
        className,
      )}
    >
      {children}
    </aside>
  );
}

function Header({
  title,
  subtitle,
  tableCount,
}: {
  title: string;
  subtitle?: string | null;
  tableCount?: number;
}) {
  return (
    <div className="flex items-center gap-3 border-b border-sidebar-border bg-gradient-to-br from-primary/10 via-transparent to-accent/30 px-4 py-4">
      <div className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Database className="size-4" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {subtitle ? (
          <p className="truncate text-xs text-muted-foreground" title={subtitle}>
            {subtitle}
            {typeof tableCount === "number" ? (
              <span className="ml-1.5">· {tableCount} table{tableCount === 1 ? "" : "s"}</span>
            ) : null}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function SchemaSidebar({ dbFilename, schema, loading, error, className }: SchemaSidebarProps) {
  if (!dbFilename) {
    return (
      <Shell className={className}>
        <Header title="Schema" subtitle="No database selected" />
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 py-10 text-center text-sm text-muted-foreground">
          <Database className="size-8 opacity-30" aria-hidden />
          <p>Select a database to view tables and columns.</p>
        </div>
      </Shell>
    );
  }

  if (loading) {
    return (
      <Shell className={className}>
        <Header title="Schema" subtitle={dbFilename} />
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading schema…
        </div>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell className={className}>
        <Header title="Schema" subtitle={dbFilename} />
        <p className="m-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      </Shell>
    );
  }

  const tables = schema?.tables ?? [];

  if (tables.length === 0) {
    return (
      <Shell className={className}>
        <Header title="Schema" subtitle={schema?.database ?? dbFilename} tableCount={0} />
        <p className="m-4 text-sm text-muted-foreground">No tables found.</p>
      </Shell>
    );
  }

  const defaultOpen = tables.map((t) => t.table);

  return (
    <Shell className={className}>
      <Header title="Schema" subtitle={schema?.database ?? dbFilename} tableCount={tables.length} />
      <div className="flex-1 overflow-y-auto px-2 py-2">
        <Accordion multiple defaultValue={defaultOpen} className="w-full">
          {tables.map((t) => (
            <AccordionItem key={t.table} value={t.table} className="border-none">
              <AccordionTrigger className="rounded-lg px-2 py-2 text-sm hover:bg-sidebar-accent">
                <span className="flex flex-1 items-center gap-2">
                  <TableIcon className="size-3.5 text-primary" aria-hidden />
                  <span className="truncate font-medium">{t.table}</span>
                </span>
                <span className="ml-2 text-[10px] font-normal text-muted-foreground">
                  {t.columns.length}
                </span>
              </AccordionTrigger>
              <AccordionContent className="px-1 pb-2">
                <ul className="space-y-1 text-xs">
                  {t.columns.map((col) => (
                    <li
                      key={`${t.table}-${col.name}`}
                      className="group flex flex-wrap items-baseline gap-x-2 gap-y-0.5 rounded-md px-2 py-1 hover:bg-sidebar-accent"
                    >
                      <span className="font-mono font-medium text-foreground">{col.name}</span>
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {col.type || "any"}
                      </span>
                      {col.primary_key ? (
                        <span className="inline-flex items-center gap-0.5 rounded bg-primary/15 px-1.5 py-0 text-[10px] font-medium text-primary">
                          <KeyRound className="size-2.5" aria-hidden />
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
    </Shell>
  );
}
