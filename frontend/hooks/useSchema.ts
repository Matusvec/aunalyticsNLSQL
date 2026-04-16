"use client";

import { useEffect, useState } from "react";

import { fetchSchema } from "@/lib/api";
import type { SchemaPayload } from "@/lib/schema-types";

export function useSchema(dbFilename: string | null) {
  const [data, setData] = useState<SchemaPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dbFilename) {
      return;
    }

    let cancelled = false;
    // Loading state for async fetch (React Compiler set-state-in-effect rule is overly strict here)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync before network
    setLoading(true);
    setError(null);

    fetchSchema(dbFilename)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(e instanceof Error ? e.message : "Failed to load schema");
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
