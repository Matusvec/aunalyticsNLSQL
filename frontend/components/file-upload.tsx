"use client";

import { useCallback, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  ALLOWED_UPLOAD_EXTENSIONS,
  uploadFileWithProgress,
  validateUploadFile,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Upload } from "lucide-react";

export type FileUploadProps = {
  onUploadComplete: (filename: string) => void;
  disabled?: boolean;
};

/**
 * Task 7: drag-and-drop zone, client-side validation, upload progress, then notifies parent with saved filename.
 */
export function FileUpload({ onUploadComplete, disabled }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const runUpload = useCallback(
    async (file: File) => {
      setError(null);
      const msg = validateUploadFile(file);
      if (msg) {
        setError(msg);
        return;
      }
      setUploading(true);
      setProgress(0);
      try {
        const { filename } = await uploadFileWithProgress(file, setProgress);
        onUploadComplete(filename);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
    [onUploadComplete],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (disabled || uploading) return;
      const f = e.dataTransfer.files?.[0];
      if (f) void runUpload(f);
    },
    [disabled, uploading, runUpload],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  }, []);

  return (
    <Card className="max-w-md">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Upload database</CardTitle>
        <CardDescription>
          Drop a SQLite file, or CSV / JSON (converted to SQLite on the server). Allowed:{" "}
          {ALLOWED_UPLOAD_EXTENSIONS.join(", ")}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Label className="sr-only" htmlFor="file-input">
          File upload
        </Label>
        <div
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              document.getElementById("file-input")?.click();
            }
          }}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          className={cn(
            "flex min-h-[120px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-6 text-center text-sm transition-colors",
            dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50",
            (disabled || uploading) && "pointer-events-none opacity-60",
          )}
          onClick={() => !uploading && !disabled && document.getElementById("file-input")?.click()}
        >
          <Upload className="mb-2 size-8 text-muted-foreground" aria-hidden />
          <span className="text-muted-foreground">Drag and drop here, or click to browse</span>
          <input
            id="file-input"
            type="file"
            className="hidden"
            accept={ALLOWED_UPLOAD_EXTENSIONS.join(",")}
            disabled={disabled || uploading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void runUpload(f);
              e.target.value = "";
            }}
          />
        </div>
        {uploading ? (
          <div className="space-y-1">
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-muted-foreground">Uploading… {progress}%</p>
          </div>
        ) : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </CardContent>
    </Card>
  );
}
