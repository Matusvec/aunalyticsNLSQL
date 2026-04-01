import React from "react";

type RowValue = string | number | boolean | null;
type ObjectRow = Record<string, RowValue>;
type ArrayRow = RowValue[];

type AskResponse = {
  columns?: string[];
  rows?: Array<ObjectRow | ArrayRow>;
  sql?: string | null;
  confidence?: number | null;
  assumptions?: string[];
  row_count?: number;
};

type ResultsTableProps = {
  result: AskResponse;
  title?: string;
  className?: string;
};

function formatConfidence(confidence?: number | null): string | null {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) {
    return null;
  }

  const normalized = confidence > 1 ? confidence / 100 : confidence;
  return `${Math.round(normalized * 100)}% confidence`;
}

function normalizeRows(
  columns: string[],
  rows: Array<ObjectRow | ArrayRow>
): ObjectRow[] {
  if (rows.length === 0) {
    return [];
  }

  const firstRow = rows[0];

  if (Array.isArray(firstRow)) {
    return rows.map((row) => {
      const arrayRow = row as ArrayRow;
      const objectRow: ObjectRow = {};

      columns.forEach((column, index) => {
        objectRow[column] = arrayRow[index] ?? null;
      });

      return objectRow;
    });
  }

  return rows as ObjectRow[];
}

function inferColumns(rows: Array<ObjectRow | ArrayRow>): string[] {
  if (rows.length === 0) {
    return [];
  }

  const firstRow = rows[0];
  if (Array.isArray(firstRow)) {
    return firstRow.map((_, index) => `column_${index + 1}`);
  }

  return Object.keys(firstRow);
}

export function ResultsTable({ result, title = "Query Results", className }: ResultsTableProps) {
  const rawRows = result.rows ?? [];
  const columns = (result.columns && result.columns.length > 0)
    ? result.columns
    : inferColumns(rawRows);

  const rows = normalizeRows(columns, rawRows);
  const hasRows = rows.length > 0;
  const confidenceText = formatConfidence(result.confidence);
  const assumptions = result.assumptions ?? [];
  const rowCount = typeof result.row_count === "number" ? result.row_count : rows.length;

  return (
    <section className={className}>
      <header style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>{title}</h2>

        {confidenceText && (
          <p style={{ margin: "8px 0 0", fontWeight: 600 }}>{confidenceText}</p>
        )}

        {assumptions.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>Assumptions</h3>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {assumptions.map((assumption, index) => (
                <li key={`${assumption}-${index}`}>{assumption}</li>
              ))}
            </ul>
          </div>
        )}

        {result.sql && (
          <div style={{ marginTop: 12 }}>
            <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>Generated SQL</h3>
            <pre
              style={{
                margin: 0,
                padding: 12,
                borderRadius: 8,
                background: "#f6f8fa",
                overflowX: "auto",
              }}
            >
              <code>{result.sql}</code>
            </pre>
          </div>
        )}
      </header>

      {!hasRows && <p>No results found.</p>}

      {hasRows && (
        <div style={{ overflowX: "auto" }}>
          <p style={{ marginTop: 0 }}>
            Showing {rows.length} row{rows.length === 1 ? "" : "s"}
            {typeof rowCount === "number" ? ` (reported: ${rowCount})` : ""}
          </p>

          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    style={{
                      borderBottom: "1px solid #d0d7de",
                      textAlign: "left",
                      padding: "8px 10px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {columns.map((column) => (
                    <td
                      key={`${rowIndex}-${column}`}
                      style={{ borderBottom: "1px solid #eef2f6", padding: "8px 10px" }}
                    >
                      {String(row[column] ?? "")}
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

export type { AskResponse, ResultsTableProps };
