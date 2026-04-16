import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SchemaSidebar } from "@/components/schema-sidebar";
import type { SchemaPayload } from "@/lib/schema-types";

const sampleSchema: SchemaPayload = {
  database: "demo.db",
  tables: [
    {
      table: "users",
      columns: [
        {
          cid: 0,
          name: "id",
          type: "INTEGER",
          notnull: false,
          default_value: null,
          primary_key: true,
        },
        {
          cid: 1,
          name: "name",
          type: "TEXT",
          notnull: true,
          default_value: null,
          primary_key: false,
        },
      ],
    },
  ],
};

describe("SchemaSidebar", () => {
  it("shows empty state when no database selected", () => {
    render(
      <SchemaSidebar dbFilename={null} schema={null} loading={false} error={null} />,
    );
    expect(screen.getByText(/Select a database/i)).toBeInTheDocument();
  });

  it("renders table and column rows from schema payload", () => {
    render(
      <SchemaSidebar
        dbFilename="demo.db"
        schema={sampleSchema}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("users")).toBeInTheDocument();
    expect(screen.getByText("id")).toBeInTheDocument();
    expect(screen.getByText("PK")).toBeInTheDocument();
    expect(screen.getByText("name")).toBeInTheDocument();
    expect(screen.getByText("NOT NULL")).toBeInTheDocument();
  });
});
