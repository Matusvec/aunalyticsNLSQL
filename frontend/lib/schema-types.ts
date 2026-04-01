/**
 * Mirrors FastAPI GET /api/schema/{db_filename} (see backend sqlite_service.describe_table_impl).
 */

export type SchemaColumn = {
  cid: number;
  name: string;
  type: string;
  notnull: boolean;
  default_value: unknown;
  primary_key: boolean;
};

export type SchemaTable = {
  table: string;
  columns: SchemaColumn[];
};

export type SchemaPayload = {
  database: string;
  tables: SchemaTable[];
};

export type DatabaseEntry = {
  filename: string;
  size_bytes: number;
};
