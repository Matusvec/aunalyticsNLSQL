"use client";

import { Code2, Lightbulb } from "lucide-react";

type RowValue = string | number | boolean | null;
type ObjectRow = Record<string, RowValue>;
type ArrayRow = RowValue[];

export type AskResponse = {
  columns?: string[];
  rows?: Array<ObjectRow | ArrayRow>;
  sql?: string | null;
  confidence?: number | null;
  assumptions?: string[];
  row_count?: number;
  question?: string;
  db_filename?: string;
  limit_applied?: number | null;
};

type ResultsTableProps = {
  result: AskResponse;
  title?: string;
  className?: string;
};

function confidenceTone(c: number): { label: string; tone: string } {
  if (c >= 0.8) return { label: "high", tone: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400" };
  if (c >= 0.5) return { label: "medium", tone: "bg-amber-500/15 text-amber-700 dark:text-amber-400" };
  return { label: "low", tone: "bg-rose-500/15 text-rose-700 dark:text-rose-400" };
}

function formatConfidence(confidence?: number | null) {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return null;
  const normalized = confidence > 1 ? confidence / 100 : confidence;
  const pct = Math.round(normalized * 100);
  const tone = confidenceTone(normalized);
  return { pct, ...tone };
}

function normalizeRows(columns: string[], rows: Array<ObjectRow | ArrayRow>): ObjectRow[] {
  if (rows.length === 0) return [];
  const firstRow = rows[0];
  if (Array.isArray(firstRow)) {
    return rows.map((row) => {
      const arrayRow = row as ArrayRow;
      const out: ObjectRow = {};
      columns.forEach((col, i) => {
        out[col] = arrayRow[i] ?? null;
      });
      return out;
    });
  }
  return rows as ObjectRow[];
}

function inferColumns(rows: Array<ObjectRow | ArrayRow>): string[] {
  if (rows.length === 0) return [];
  const firstRow = rows[0];
  if (Array.isArray(firstRow)) return firstRow.map((_, i) => `column_${i + 1}`);
  return Object.keys(firstRow);
}

export function ResultsTable({ result, title = "Results", className }: ResultsTableProps) {
  const rawRows = result.rows ?? [];
  const columns =
    result.columns && result.columns.length > 0 ? result.columns : inferColumns(rawRows);
  const rows = normalizeRows(columns, rawRows);
  const hasRows = rows.length > 0;
  const conf = formatConfidence(result.confidence);
  const assumptions = result.assumptions ?? [];
  const rowCount = typeof result.row_count === "number" ? result.row_count : rows.length;

  return (
    <section className={className}>
      <header className="mb-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-base font-semibold">{title}</h2>
          {conf ? (
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ${conf.tone}`}
            >
              {conf.pct}% · {conf.label}
            </span>
          ) : null}
        </div>

        {assumptions.length > 0 ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
            <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300">
              <Lightbulb className="size-3.5" aria-hidden />
              Assumptions
            </div>
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
              {assumptions.map((assumption, i) => (
                <li key={`${assumption}-${i}`}>{assumption}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {result.sql ? (
          <div>
            <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <Code2 className="size-3.5" aria-hidden />
              Generated SQL
            </div>
            <pre className="overflow-x-auto rounded-lg border border-border/60 bg-muted/60 p-3 text-xs">
              <code className="font-mono">{result.sql}</code>
            </pre>
          </div>
        ) : null}
      </header>

      {!hasRows ? <p className="text-sm text-muted-foreground">No results found.</p> : null}

      {hasRows ? (
        <div className="overflow-hidden rounded-xl border border-border/60">
          <p className="border-b border-border/60 bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
            Showing {rows.length} row{rows.length === 1 ? "" : "s"}
            {typeof rowCount === "number" && rowCount !== rows.length
              ? ` (reported: ${rowCount})`
              : ""}
          </p>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-muted/20">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="border-b border-border/60 px-4 py-2 text-left font-medium whitespace-nowrap text-foreground"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr
                    key={i}
                    className="transition-colors hover:bg-primary/[0.04] [&:not(:last-child)]:border-b [&:not(:last-child)]:border-border/40"
                  >
                    {columns.map((col) => (
                      <td key={`${i}-${col}`} className="px-4 py-2 align-top">
                        {row[col] === null || row[col] === undefined ? (
                          <span className="text-muted-foreground italic">null</span>
                        ) : (
                          String(row[col])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
