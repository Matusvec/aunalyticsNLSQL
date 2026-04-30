/**
 * Typed helpers for the FastAPI backend. Base URL from NEXT_PUBLIC_API_URL.
 */

import type { DatabaseEntry, SchemaGraph, SchemaPayload } from "@/lib/schema-types";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
}

export async function fetchSchema(dbFilename: string): Promise<SchemaPayload> {
  const url = `${getApiBaseUrl()}/api/schema/${encodeURIComponent(dbFilename)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Schema request failed: ${res.status}`);
  }
  return res.json() as Promise<SchemaPayload>;
}

export async function fetchSchemaGraph(dbFilename: string): Promise<SchemaGraph> {
  const url = `${getApiBaseUrl()}/api/schema-graph/${encodeURIComponent(dbFilename)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Schema graph request failed: ${res.status}`);
  }
  return res.json() as Promise<SchemaGraph>;
}

export async function listDatabases(): Promise<{ databases: DatabaseEntry[] }> {
  const res = await fetch(`${getApiBaseUrl()}/api/databases`);
  if (!res.ok) {
    throw new Error(`Failed to list databases: ${res.status}`);
  }
  return res.json() as Promise<{ databases: DatabaseEntry[] }>;
}

/**
 * Upload with XMLHttpRequest so we can report upload progress (Task 7 bonus).
 * POST /api/upload — multipart field "file".
 */
export function uploadFileWithProgress(
  file: File,
  onProgress: (percent: number) => void,
): Promise<{ success: boolean; filename: string }> {
  const mock = process.env.NEXT_PUBLIC_MOCK_UPLOAD === "true";
  if (mock) {
    return new Promise((resolve) => {
      let p = 0;
      const id = setInterval(() => {
        p += 25;
        onProgress(Math.min(p, 100));
        if (p >= 100) {
          clearInterval(id);
          resolve({ success: true, filename: file.name });
        }
      }, 40);
    });
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getApiBaseUrl()}/api/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((100 * e.loaded) / e.total));
      }
    };
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText) as { success?: boolean; filename?: string; detail?: string };
        if (xhr.status >= 200 && xhr.status < 300 && body.filename) {
          onProgress(100);
          resolve({ success: Boolean(body.success), filename: body.filename });
        } else {
          reject(new Error(body.detail ?? xhr.responseText ?? `Upload failed (${xhr.status})`));
        }
      } catch {
        reject(new Error(xhr.responseText || "Invalid upload response"));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export type AskResponse = {
  db_filename: string;
  question: string;
  sql: string;
  columns: string[];
  rows: Array<Record<string, string | number | boolean | null>>;
  row_count: number;
  limit_applied: number | null;
  confidence?: number | null;
  assumptions?: string[];
  tier?: string | null;
};

export type AgentTier = {
  name: string;
  max_iterations: number;
  max_submit_retries: number;
  description: string;
};

export type AgentEvent =
  | { type: "request_id"; request_id: string }
  | { type: "start"; tier: string; max_iterations: number; max_submit_retries: number; model: string }
  | { type: "brief"; brief: string }
  | { type: "iteration"; iteration: number }
  | { type: "model_text"; text: string }
  | { type: "tool_call"; iteration: number; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; iteration: number; name: string; summary: Record<string, unknown> }
  | { type: "submit_failed"; attempt: number; max_attempts: number; error: string; sql?: string }
  | { type: "submit_ok"; sql: string; confidence: number | null; assumptions: string[] }
  | { type: "nudge"; reason: string }
  | ({ type: "final" } & AskResponse)
  | { type: "error"; status: number; detail: string };

export async function fetchAgentTiers(): Promise<{ default: string; tiers: AgentTier[] }> {
  const res = await fetch(`${getApiBaseUrl()}/api/agent/tiers`);
  if (!res.ok) throw new Error(`Failed to load tiers: ${res.status}`);
  return res.json() as Promise<{ default: string; tiers: AgentTier[] }>;
}

export async function askQuestion(
  dbFilename: string,
  question: string,
  limit = 200,
  tier?: string,
): Promise<AskResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ db_filename: dbFilename, question, limit, tier }),
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail ?? "";
    } catch {
      detail = await res.text();
    }
    throw new Error(detail || `Ask failed (${res.status})`);
  }
  return res.json() as Promise<AskResponse>;
}

/**
 * Stream agent events from POST /api/ask/stream.
 * `onEvent` is called for every parsed Server-Sent Event.
 * Resolves when the stream ends; rejects on transport failure or abort.
 */
export async function askQuestionStream(
  dbFilename: string,
  question: string,
  limit: number,
  tier: string | undefined,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ db_filename: dbFilename, question, limit, tier }),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail ?? "";
    } catch {
      try {
        detail = await res.text();
      } catch {
        /* ignore */
      }
    }
    throw new Error(detail || `Ask stream failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    while (true) {
      const idx = buffer.indexOf("\n\n");
      if (idx === -1) break;
      const message = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      const dataLines = message
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6));

      if (dataLines.length === 0) continue;
      const payload = dataLines.join("\n");
      try {
        const event = JSON.parse(payload) as AgentEvent;
        onEvent(event);
      } catch (err) {
        console.error("agent stream parse error", err, payload.slice(0, 200));
      }
    }
  }
}

export type HistoryItem = {
  id: number;
  question: string;
  sql: string;
  confidence: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
};

export async function fetchHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/history`);
  if (!res.ok) {
    throw new Error(`Failed to load history: ${res.status}`);
  }
  const body = (await res.json()) as { items: HistoryItem[] };
  return body.items;
}

export const ALLOWED_UPLOAD_EXTENSIONS = [".sqlite", ".db", ".csv", ".json"] as const;

export function validateUploadFile(file: File): string | null {
  const lower = file.name.toLowerCase();
  const ok = ALLOWED_UPLOAD_EXTENSIONS.some((ext) => lower.endsWith(ext));
  if (!ok) {
    return `Invalid file type. Allowed: ${ALLOWED_UPLOAD_EXTENSIONS.join(", ")}`;
  }
  const maxBytes = 20 * 1024 * 1024;
  if (file.size > maxBytes) {
    return "File too large (max 20 MB).";
  }
  return null;
}
