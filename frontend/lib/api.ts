/**
 * Typed helpers for the FastAPI backend. Base URL from NEXT_PUBLIC_API_URL.
 */

import type { DatabaseEntry, SchemaPayload } from "@/lib/schema-types";

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
};

export async function askQuestion(
  dbFilename: string,
  question: string,
  limit = 200,
): Promise<AskResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ db_filename: dbFilename, question, limit }),
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
