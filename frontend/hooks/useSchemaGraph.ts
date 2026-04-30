"use client";

import { useEffect, useState } from "react";

import { fetchSchemaGraph } from "@/lib/api";
import type { SchemaGraph } from "@/lib/schema-types";

export function useSchemaGraph(dbFilename: string | null) {
  const [data, setData] = useState<SchemaGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dbFilename) {
      setData(null);
      return;
    }

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);

    fetchSchemaGraph(dbFilename)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(e instanceof Error ? e.message : "Failed to load schema graph");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [dbFilename]);

  return {
    data: dbFilename ? data : null,
    loading: Boolean(dbFilename) && loading,
    error: dbFilename ? error : null,
  };
}
