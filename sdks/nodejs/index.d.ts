/**
 * TypeScript Declarations for MergenDB Node.js SDK
 * (c) 2026 Uğur Türker Kebeci - MIT License
 */

export interface MergenOptions {
  url?: string;
  host?: string;
  port?: number;
  activeTable?: string;
  timeout?: number;
}

export interface QueryStats {
  execution_time_ms: number;
  blocks_scanned: number;
  blocks_pruned: number;
  bytes_read: number;
}

export interface QueryResult<T = any> {
  columns: string[];
  rows: any[][];
  row_count: number;
  stats: QueryStats;
  message?: string;
}

export interface TableInfo {
  name: string;
  path: string;
  rows: number;
  blocks: number;
  columns: number;
  size_bytes: number;
}

export interface ColumnDefinition {
  name: string;
  type: string;
  nullable?: boolean;
}

export interface SchemaInfo {
  table: string;
  columns: ColumnDefinition[];
  block_count: number;
  file_size: number;
}

export interface PageResult {
  columns: string[];
  rows: any[][];
  page: number;
  limit: number;
  total_rows: number;
  total_pages: number;
}

export interface ServerStatus {
  status: string;
  server: string;
  version: string;
  database: string;
  cpu_model: string;
  cpu_threads: number;
  total_ram_gb: number;
  os: string;
  python_version: string;
  timestamp: number;
}

export class MergenError extends Error {
  status: number;
  details?: any;
  constructor(message: string, status?: number, details?: any);
}

export class TableHandle {
  readonly client: MergenDB;
  readonly name: string;
  readonly pureName: string;

  schema(): Promise<SchemaInfo>;
  data(page?: number, limit?: number): Promise<PageResult>;
  find<T = Record<string, any>>(filters?: Record<string, any>, options?: { limit?: number; columns?: string[] }): Promise<T[]>;
  findOne<T = Record<string, any>>(filters?: Record<string, any>): Promise<T | null>;
  search<T = Record<string, any>>(term: string): Promise<T[]>;
  count(filters?: Record<string, any>): Promise<number>;
  insert(records: Record<string, any> | Record<string, any>[]): Promise<{ status: string; message: string }>;
  update(updates: Record<string, any>, where: string): Promise<QueryResult>;
  delete(where: string): Promise<{ status: string; message: string }>;
  addColumn(name: string, type?: string, defaultVal?: any): Promise<{ status: string; message: string }>;
  dropColumn(name: string): Promise<{ status: string; message: string }>;
  renameColumn(oldName: string, newName: string): Promise<{ status: string; message: string }>;
  export(format?: 'csv' | 'json' | 'jsonl' | 'sql'): Promise<string>;
  import(content: string, format?: 'csv' | 'json' | 'sql'): Promise<{ status: string; rows_imported: number }>;
  truncate(): Promise<{ status: string; message: string }>;
  drop(): Promise<{ status: string; message: string }>;
}

export class MergenDB {
  protocol: string;
  host: string;
  port: number;
  activeTable?: string;
  timeout: number;

  constructor(options?: MergenOptions | string);
  ping(): Promise<boolean>;
  status(): Promise<ServerStatus>;
  benchmark(): Promise<any>;
  listTables(): Promise<TableInfo[]>;
  query<T = any>(sqlQuery: string, options?: { activeTable?: string }): Promise<QueryResult<T>>;
  sql<T = any>(strings: TemplateStringsArray, ...values: any[]): Promise<QueryResult<T>>;
  table(tableName: string): TableHandle;
  createTable(name: string, columns: ColumnDefinition[], blockSize?: number): Promise<{ status: string; message: string }>;
  truncateTable(name: string): Promise<{ status: string; message: string }>;
  dropTable(name: string): Promise<{ status: string; message: string }>;
  renameTable(oldName: string, newName: string): Promise<{ status: string; message: string }>;
}

export function connect(options?: MergenOptions | string): MergenDB;
export default connect;
