/**
 * TypeScript Declarations for MergenDB Node.js SDK
 * (c) 2026 Uğur Türker Kebeci - MIT License
 */

export interface MergenOptions {
  url?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  token?: string;
  activeTable?: string;
  timeout?: number;
  autoStart?: boolean;
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

export class DatabaseHandle {
  readonly client: MergenDB;
  readonly name: string;

  table(tableName: string): TableHandle;
  tables(): Promise<TableInfo[]>;
  listTables(): Promise<TableInfo[]>;
  createTable(name: string, columns: ColumnDefinition[], blockSize?: number): Promise<{ status: string; message: string }>;
  dropTable(name: string): Promise<{ status: string; message: string }>;
  query<T = any>(sqlQuery: string): Promise<QueryResult<T>>;
  drop(): Promise<{ success: boolean; message: string }>;
}

export type Database = DatabaseHandle;

export class TableHandle {
  readonly client: MergenDB;
  readonly name: string;
  readonly pureName: string;
  readonly database: string;

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
  exportToFile(destPath: string, format?: 'csv' | 'json' | 'jsonl' | 'sql'): Promise<string>;
  import(content: string, format?: 'csv' | 'json' | 'sql'): Promise<{ status: string; rows_imported: number }>;
  importFile(filePath: string, format?: 'csv' | 'json' | 'sql'): Promise<{ success: boolean; rows_imported: number; execution_time_ms: number }>;
  createSubtable(name: string, columns: ColumnDefinition[], blockSize?: number): Promise<{ status: string; message: string }>;
  subtable(name: string): TableHandle;
  listSubtables(): Promise<TableInfo[]>;
  truncate(): Promise<{ status: string; message: string }>;
  drop(): Promise<{ status: string; message: string }>;
}

export type Table = TableHandle;

export class MergenDB {
  protocol: string;
  host: string;
  port: number;
  username: string;
  password: string;
  token?: string;
  activeTable?: string;
  timeout: number;
  autoStart: boolean;

  constructor(options?: MergenOptions | string);
  login(username?: string, password?: string): Promise<{ success: boolean; token: string; user: string }>;
  changePassword(newPassword: string, username?: string): Promise<{ success: boolean; message: string }>;
  verifyAuth(): Promise<{ authenticated: boolean; user: string }>;
  ping(): Promise<boolean>;
  status(): Promise<ServerStatus>;
  benchmark(): Promise<any>;
  ensureServer(maxWaitMs?: number): Promise<boolean>;
  database(name?: string): DatabaseHandle;
  listDatabases(): Promise<Array<{ name: string; tables_count: number; total_bytes: number }>>;
  createDatabase(name: string): Promise<{ success: boolean; message: string }>;
  dropDatabase(name: string): Promise<{ success: boolean; message: string }>;
  listTables(): Promise<TableInfo[]>;
  query<T = any>(sqlQuery: string, options?: { activeTable?: string; database?: string }): Promise<QueryResult<T>>;
  sql<T = any>(strings: TemplateStringsArray, ...values: any[]): Promise<QueryResult<T>>;
  table(tableName: string): TableHandle;
  createTable(name: string, columns: ColumnDefinition[], blockSize?: number): Promise<{ status: string; message: string }>;
  truncateTable(name: string): Promise<{ status: string; message: string }>;
  dropTable(name: string): Promise<{ status: string; message: string }>;
  renameTable(oldName: string, newName: string): Promise<{ status: string; message: string }>;
}

export function connect(options?: MergenOptions | string): MergenDB;
export const open: typeof connect;
export default connect;

