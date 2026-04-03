import { useState, type FormEvent } from "react";

import { ResultsTable, type AskResponse } from "./ResultsTable";

type AskRequest = {
  db_filename: string;
  question: string;
  limit?: number;
};

export function ResultsTableExample() {
  const [request, setRequest] = useState<AskRequest>({
    db_filename: "chinook.db",
    question: "Show me the top 10 customers by revenue",
    limit: 10,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        let detail = "";
        try {
          const payload = (await response.json()) as { detail?: string };
          detail = payload.detail ? ` - ${payload.detail}` : "";
        } catch {
          detail = "";
        }
        throw new Error(`Request failed: ${response.status}${detail}`);
      }

      const data = (await response.json()) as AskResponse;
      setResult(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch results.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={submit} style={{ marginBottom: 20 }}>
        <label htmlFor="db_filename">Database</label>
        <input
          id="db_filename"
          value={request.db_filename}
          onChange={(event) =>
            setRequest((prev) => ({ ...prev, db_filename: event.target.value }))
          }
          style={{ display: "block", marginBottom: 10 }}
        />

        <label htmlFor="question">Question</label>
        <input
          id="question"
          value={request.question}
          onChange={(event) =>
            setRequest((prev) => ({ ...prev, question: event.target.value }))
          }
          style={{ display: "block", width: "100%", marginBottom: 10 }}
        />

        <button type="submit" disabled={loading}>
          {loading ? "Running..." : "Run Query"}
        </button>
      </form>

      {error && <p>{error}</p>}
      {result && <ResultsTable result={result} />}
    </div>
  );
}
