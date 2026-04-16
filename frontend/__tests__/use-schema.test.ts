import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useSchema } from "@/hooks/useSchema";

describe("useSchema", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches schema when db filename is set", async () => {
    const payload = {
      database: "x.db",
      tables: [{ table: "t", columns: [] }],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => payload,
      }),
    );

    const { result } = renderHook(() => useSchema("x.db"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/schema/x.db"),
    );
  });

  it("clears data when filename is null", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ database: "a", tables: [] }),
      }),
    );

    const { result, rerender } = renderHook(
      ({ name }: { name: string | null }) => useSchema(name),
      { initialProps: { name: "a.db" as string | null } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      rerender({ name: null });
    });

    expect(result.current.data).toBeNull();
  });
});
