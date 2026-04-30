"use client";

import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type Orientation = "horizontal" | "vertical";
type Edge = "start" | "end";


/**
 * Persisted resize state. SSR-safe (returns the default until first effect run).
 */
export function useResizable(
  storageKey: string,
  defaultSize: number,
  min: number,
  max: number,
) {
  const [size, setSizeState] = useState<number>(defaultSize);

  // On mount, read from localStorage. Done in an effect so SSR + hydration agree.
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) {
        const parsed = parseInt(raw, 10);
        if (Number.isFinite(parsed)) {
          setSizeState(Math.max(min, Math.min(max, parsed)));
        }
      }
    } catch {
      /* ignore */
    }
  }, [storageKey, min, max]);

  const setSize = useCallback(
    (next: number) => {
      const clamped = Math.max(min, Math.min(max, Math.round(next)));
      setSizeState(clamped);
      try {
        window.localStorage.setItem(storageKey, String(clamped));
      } catch {
        /* ignore */
      }
    },
    [storageKey, min, max],
  );

  return [size, setSize] as const;
}


type ResizeHandleProps = {
  orientation: Orientation;
  /** Which edge of the resizable element this handle sits on. */
  edge: Edge;
  /** Current size of the element. Captured at pointerdown to compute the delta. */
  size: number;
  /** Called with the new absolute size during drag. */
  onResize: (next: number) => void;
  className?: string;
  ariaLabel?: string;
};


export function ResizeHandle({
  orientation,
  edge,
  size,
  onResize,
  className,
  ariaLabel,
}: ResizeHandleProps) {
  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      const startSize = size;
      const startCoord = orientation === "horizontal" ? e.clientX : e.clientY;
      const direction = edge === "end" ? 1 : -1;

      const onMove = (ev: PointerEvent) => {
        const coord = orientation === "horizontal" ? ev.clientX : ev.clientY;
        const delta = (coord - startCoord) * direction;
        onResize(startSize + delta);
      };

      const onUp = () => {
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      document.body.style.cursor =
        orientation === "horizontal" ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
    },
    [orientation, edge, size, onResize],
  );

  return (
    <div
      role="separator"
      aria-label={ariaLabel}
      aria-orientation={orientation}
      onPointerDown={handlePointerDown}
      className={cn(
        "group/handle relative shrink-0 transition-colors",
        orientation === "horizontal"
          ? "w-1 cursor-col-resize hover:w-1.5"
          : "h-1 cursor-row-resize hover:h-1.5",
        "bg-border/40 hover:bg-primary/50",
        className,
      )}
    >
      {/* Wider invisible hit area so the user can grab it without aiming */}
      <div
        aria-hidden
        className={cn(
          "absolute",
          orientation === "horizontal" ? "-inset-y-0 -left-1.5 -right-1.5" : "-inset-x-0 -top-1.5 -bottom-1.5",
        )}
      />
      {/* Grip dot indicator on hover */}
      <div
        aria-hidden
        className={cn(
          "absolute opacity-0 transition-opacity group-hover/handle:opacity-100",
          orientation === "horizontal"
            ? "left-1/2 top-1/2 h-8 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary"
            : "left-1/2 top-1/2 h-1 w-8 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary",
        )}
      />
    </div>
  );
}
