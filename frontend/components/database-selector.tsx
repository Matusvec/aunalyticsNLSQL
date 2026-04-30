"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DatabaseEntry } from "@/lib/schema-types";

export type DatabaseSelectorProps = {
  databases: DatabaseEntry[];
  value: string | null;
  onValueChange: (filename: string | null) => void;
  disabled?: boolean;
};

/**
 * Picker for SQLite files under backend/db (GET /api/databases). Drives which DB the schema sidebar loads.
 */
export function DatabaseSelector({
  databases,
  value,
  onValueChange,
  disabled,
}: DatabaseSelectorProps) {
  if (databases.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No databases yet — upload a SQLite, CSV, or JSON file to get started.
      </p>
    );
  }

  const v = value ?? databases[0]?.filename ?? "";

  return (
    <>
      <Label htmlFor="db-select" className="sr-only">
        Active database
      </Label>
      <Select
        value={v}
        onValueChange={(next) => onValueChange(next ?? null)}
        disabled={disabled}
      >
        <SelectTrigger id="db-select" className="w-full" size="default">
          <SelectValue placeholder="Choose a database" />
        </SelectTrigger>
        <SelectContent>
          {databases.map((d) => (
            <SelectItem key={d.filename} value={d.filename}>
              <span className="font-mono">{d.filename}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                {formatBytes(d.size_bytes)}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </>
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
