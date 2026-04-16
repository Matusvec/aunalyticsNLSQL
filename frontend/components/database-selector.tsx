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
      <div className="flex flex-col gap-2">
        <Label>Database</Label>
        <p className="text-sm text-muted-foreground">No databases found. Upload a file below.</p>
      </div>
    );
  }

  const v = value ?? databases[0]?.filename ?? "";

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="db-select">Active database</Label>
      <Select
        value={v}
        onValueChange={(next) => onValueChange(next ?? null)}
        disabled={disabled}
      >
        <SelectTrigger id="db-select" className="w-full max-w-md" size="default">
          <SelectValue placeholder="Choose a database" />
        </SelectTrigger>
        <SelectContent>
          {databases.map((d) => (
            <SelectItem key={d.filename} value={d.filename}>
              {d.filename} ({formatBytes(d.size_bytes)})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
