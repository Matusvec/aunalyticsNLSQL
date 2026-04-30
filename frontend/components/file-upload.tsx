"use client";

import { useCallback, useState } from "react";

import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  ALLOWED_UPLOAD_EXTENSIONS,
  uploadFileWithProgress,
  validateUploadFile,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { CheckCircle2, Upload } from "lucide-react";

export type FileUploadProps = {
  onUploadComplete: (filename: string) => void;
  disabled?: boolean;
};

export function FileUpload({ onUploadComplete, disabled }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [lastFilename, setLastFilename] = useState<string | null>(null);

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
        setLastFilename(filename);
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
    <div className="flex flex-col gap-3">
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
          "group relative flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-6 text-center text-sm transition-all",
          dragActive
            ? "border-primary bg-primary/10 scale-[1.01]"
            : "border-primary/25 bg-primary/[0.03] hover:border-primary/45 hover:bg-primary/[0.06]",
          (disabled || uploading) && "pointer-events-none opacity-60",
        )}
        onClick={() => !uploading && !disabled && document.getElementById("file-input")?.click()}
      >
        <div className="mb-2 grid size-12 place-items-center rounded-full bg-primary/10 text-primary transition-transform group-hover:scale-110">
          <Upload className="size-6" aria-hidden />
        </div>
        <span className="font-medium text-foreground">
          {dragActive ? "Drop to upload" : "Drag & drop, or click to browse"}
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          {ALLOWED_UPLOAD_EXTENSIONS.join(" · ")} · max 20 MB
        </span>
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

      {!uploading && lastFilename ? (
        <p className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-3.5" aria-hidden />
          Uploaded <span className="font-mono font-medium">{lastFilename}</span>
        </p>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
