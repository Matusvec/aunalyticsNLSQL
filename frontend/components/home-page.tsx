"use client";

import { useCallback, useEffect, useState } from "react";

import { DatabaseSelector } from "@/components/database-selector";
import { FileUpload } from "@/components/file-upload";
import { HistoryPanel } from "@/components/history-panel";
import { QueryPanel } from "@/components/query-panel";
import { SchemaSidebar } from "@/components/schema-sidebar";
import { listDatabases } from "@/lib/api";
import type { DatabaseEntry } from "@/lib/schema-types";
import { useSchema } from "@/hooks/useSchema";

export function HomePage() {
  const [databases, setDatabases] = useState<DatabaseEntry[]>([]);
  const [selectedDb, setSelectedDb] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0);

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
    // Intentional mount-only load of /api/databases
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  const { data, loading, error } = useSchema(selectedDb);

  const onUploadComplete = useCallback(
    (filename: string) => {
      void refreshDatabases(filename);
    },
    [refreshDatabases],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col md:flex-row">
      <SchemaSidebar
        dbFilename={selectedDb}
        schema={data}
        loading={loading}
        error={error}
        className="md:max-w-sm md:min-h-0 md:shrink-0"
      />
      <main className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">NL to SQL</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Choose a database, inspect the schema in the sidebar, and upload new SQLite / CSV / JSON files.
          </p>
        </div>

        {listError ? <p className="text-sm text-destructive">{listError}</p> : null}

        <DatabaseSelector
          databases={databases}
          value={selectedDb}
          onValueChange={(name) => setSelectedDb(name)}
        />

        <FileUpload onUploadComplete={onUploadComplete} />

        <QueryPanel
          dbFilename={selectedDb}
          question={question}
          onQuestionChange={setQuestion}
          onAsked={() => setHistoryRefreshToken((n) => n + 1)}
        />

        <HistoryPanel refreshToken={historyRefreshToken} onPick={setQuestion} />
      </main>
    </div>
  );
}
