"use client";

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

function formatConfidence(confidence?: number | null): string | null {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return null;
  const normalized = confidence > 1 ? confidence / 100 : confidence;
  return `${Math.round(normalized * 100)}% confidence`;
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

export function ResultsTable({ result, title = "Query Results", className }: ResultsTableProps) {
  const rawRows = result.rows ?? [];
  const columns =
    result.columns && result.columns.length > 0 ? result.columns : inferColumns(rawRows);
  const rows = normalizeRows(columns, rawRows);
  const hasRows = rows.length > 0;
  const confidenceText = formatConfidence(result.confidence);
  const assumptions = result.assumptions ?? [];
  const rowCount = typeof result.row_count === "number" ? result.row_count : rows.length;

  return (
    <section className={className}>
      <header className="mb-3 space-y-2">
        <h2 className="text-lg font-semibold">{title}</h2>

        {confidenceText && (
          <p className="text-sm font-medium text-muted-foreground">{confidenceText}</p>
        )}

        {assumptions.length > 0 && (
          <div>
            <h3 className="mb-1 text-sm font-medium">Assumptions</h3>
            <ul className="list-disc pl-5 text-sm text-muted-foreground">
              {assumptions.map((assumption, i) => (
                <li key={`${assumption}-${i}`}>{assumption}</li>
              ))}
            </ul>
          </div>
        )}

        {result.sql && (
          <div>
            <h3 className="mb-1 text-sm font-medium">Generated SQL</h3>
            <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
              <code>{result.sql}</code>
            </pre>
          </div>
        )}
      </header>

      {!hasRows && <p className="text-sm text-muted-foreground">No results found.</p>}

      {hasRows && (
        <div className="overflow-x-auto">
          <p className="mb-2 text-xs text-muted-foreground">
            Showing {rows.length} row{rows.length === 1 ? "" : "s"}
            {typeof rowCount === "number" && rowCount !== rows.length
              ? ` (reported: ${rowCount})`
              : ""}
          </p>

          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="border-b border-border px-3 py-2 text-left font-medium whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="hover:bg-muted/40">
                  {columns.map((col) => (
                    <td
                      key={`${i}-${col}`}
                      className="border-b border-border/60 px-3 py-2 align-top"
                    >
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
      )}
    </section>
  );
}
