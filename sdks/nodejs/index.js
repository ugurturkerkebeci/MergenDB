/**
 * MergenDB Node.js & TypeScript Client SDK
 * Ultra-compact, columnar database client with Zero external dependencies.
 *
 * (c) 2026 Uğur Türker Kebeci - MIT License
 */

'use strict';

const http = require('http');
const https = require('https');
const url = require('url');
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

class MergenError extends Error {
  constructor(message, status = 500, details = null) {
    super(message);
    this.name = 'MergenError';
    this.status = status;
    this.details = details;
  }
}

class MergenDB {
  /**
   * @param {Object|string} options Connection options or URL string
   */
  constructor(options = {}) {
    if (typeof options === 'string') {
      options = { url: options };
    }
    const defaultUrl = options.url || `http://${options.host || '127.0.0.1'}:${options.port || 8765}`;
    const parsed = new url.URL(defaultUrl);
    
    this.protocol = parsed.protocol || 'http:';
    this.host = parsed.hostname || '127.0.0.1';
    this.port = parseInt(parsed.port || (this.protocol === 'https:' ? '443' : '8765'), 10);
    this.activeTable = options.activeTable || null;
    this.timeout = options.timeout || 30000;
    this.autoStart = Boolean(options.autoStart);
    this._serverProcess = null;
  }

  /**
   * Internal HTTP requester (zero external dependencies)
   */
  _rawRequest(method, path, body = null, headers = {}) {
    return new Promise((resolve, reject) => {
      const client = this.protocol === 'https:' ? https : http;
      const payload = body ? (typeof body === 'string' ? body : JSON.stringify(body)) : null;

      const reqHeaders = {
        'Accept': 'application/json',
        ...headers
      };

      if (payload && !reqHeaders['Content-Type']) {
        reqHeaders['Content-Type'] = 'application/json';
        reqHeaders['Content-Length'] = Buffer.byteLength(payload);
      }

      const req = client.request({
        protocol: this.protocol,
        hostname: this.host,
        port: this.port,
        method: method.toUpperCase(),
        path: path,
        headers: reqHeaders,
        timeout: this.timeout
      }, (res) => {
        let rawData = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => { rawData += chunk; });
        res.on('end', () => {
          let parsed;
          const contentType = res.headers['content-type'] || '';
          if (contentType.includes('application/json')) {
            try {
              parsed = JSON.parse(rawData);
            } catch (err) {
              parsed = rawData;
            }
          } else {
            parsed = rawData;
          }

          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            const errMsg = (parsed && parsed.error) ? parsed.error : `HTTP ${res.statusCode}: ${rawData}`;
            reject(new MergenError(errMsg, res.statusCode, parsed));
          }
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new MergenError(`Request timed out after ${this.timeout}ms`, 408));
      });

      req.on('error', (err) => {
        reject(new MergenError(`Connection to MergenDB failed: ${err.message}`, 503, err));
      });

      if (payload) {
        req.write(payload);
      }
      req.end();
    });
  }

  async _request(method, path, body = null, headers = {}) {
    try {
      return await this._rawRequest(method, path, body, headers);
    } catch (err) {
      if (this.autoStart && err.status === 503 && (this.host === '127.0.0.1' || this.host === 'localhost')) {
        await this.ensureServer();
        return await this._rawRequest(method, path, body, headers);
      }
      throw err;
    }
  }

  /**
   * Ensures the MergenDB server is running. Spawns it if not already online.
   * @param {number} maxWaitMs Maximum wait time in milliseconds
   * @returns {Promise<boolean>}
   */
  async ensureServer(maxWaitMs = 5000) {
    if (await this.ping()) {
      return true;
    }
    this._serverProcess = startServer({ port: this.port, host: this.host });
    const start = Date.now();
    while (Date.now() - start < maxWaitMs) {
      await new Promise(r => setTimeout(r, 150));
      if (await this.ping()) {
        return true;
      }
    }
    throw new MergenError(`Could not auto-start or connect to MergenDB server on port ${this.port}`, 503);
  }

  /**
   * Healthcheck / Ping server
   * @returns {Promise<boolean>}
   */
  async ping() {
    try {
      const res = await this._request('GET', '/status');
      return !!(res && (res.status === 'healthy' || res.status === 'ok' || res.engine_version || res.server === 'MergenDB'));
    } catch (e) {
      return false;
    }
  }

  /**
   * Get server hardware specifications & engine diagnostics
   * @returns {Promise<Object>}
   */
  async status() {
    return await this._request('GET', '/status');
  }

  /**
   * List all available tables (.mgdb files) in the working directory
   * @returns {Promise<Array<Object>>}
   */
  async listTables() {
    const res = await this._request('GET', '/tables');
    return (res && res.tables) ? res.tables : [];
  }

  /**
   * Execute an analytical SQL / MergenQL query
   * @param {string} sqlQuery SQL query string
   * @param {Object} [options] Query options (e.g. activeTable)
   * @returns {Promise<Object>} Query result with rows, columns, and execution stats
   */
  async query(sqlQuery, options = {}) {
    if (!sqlQuery || typeof sqlQuery !== 'string') {
      throw new MergenError('Query must be a non-empty SQL string');
    }
    const payload = {
      query: sqlQuery,
      active_table: options.activeTable || this.activeTable || ''
    };
    const res = await this._request('POST', '/query', payload);
    if (res && res.rows && res.row_count === undefined) {
      res.row_count = res.rows.length;
    }
    return res;
  }

  /**
   * Tagged template literal for SQL queries with parameter escaping
   * Usage: await db.sql`SELECT * FROM users WHERE age > ${minAge}`
   */
  async sql(strings, ...values) {
    let queryStr = '';
    for (let i = 0; i < strings.length; i++) {
      queryStr += strings[i];
      if (i < values.length) {
        const val = values[i];
        if (val === null || val === undefined) {
          queryStr += 'NULL';
        } else if (typeof val === 'number' || typeof val === 'boolean') {
          queryStr += val;
        } else {
          // Escape single quotes for SQL safety
          const escaped = String(val).replace(/'/g, "''");
          queryStr += `'${escaped}'`;
        }
      }
    }
    return this.query(queryStr);
  }

  /**
   * Get a high-level table handle
   * @param {string} tableName Name of the .mgdb table
   * @returns {TableHandle}
   */
  table(tableName) {
    return new TableHandle(this, tableName);
  }

  /**
   * Perform administrative table operations (create, truncate, drop, rename)
   */
  async operation(op, params = {}) {
    return await this._request('POST', '/operation', { op, ...params });
  }

  /**
   * Create a new table
   */
  async createTable(name, columns, blockSize = 1024) {
    return await this.operation('create_table', {
      table: name,
      columns: columns,
      block_size: blockSize
    });
  }

  /**
   * Truncate an existing table (clear data, preserve schema)
   */
  async truncateTable(name) {
    return await this.operation('truncate', { table: name });
  }

  /**
   * Permanently drop a table
   */
  async dropTable(name) {
    return await this.operation('drop', { table: name });
  }

  /**
   * Rename an existing table
   */
  async renameTable(oldName, newName) {
    return await this.operation('rename', { table: oldName, new_name: newName });
  }

  /**
   * Run live hardware diagnostics and benchmark throughput
   */
  async benchmark() {
    return await this._request('GET', '/status?benchmark=1');
  }

  /**
   * Access a database container
   * @param {string} [name='default']
   * @returns {DatabaseHandle}
   */
  database(name = 'default') {
    return new DatabaseHandle(this, name);
  }

  /**
   * List all database containers on server
   */
  async listDatabases() {
    const res = await this._request('GET', '/databases');
    return res.databases || [];
  }

  /**
   * Create a new database container
   */
  async createDatabase(name) {
    return await this._request('POST', '/database', { action: 'create', name: name });
  }

  /**
   * Drop a database container and its tables
   */
  async dropDatabase(name) {
    return await this._request('POST', '/database', { action: 'drop', name: name });
  }
}

/**
 * Handle for a logical database container (phpMyAdmin style)
 */
class DatabaseHandle {
  constructor(client, name = 'default') {
    this.client = client;
    this.name = name;
  }

  /**
   * Get table handle scoped to this database
   */
  table(tableName) {
    const clean = tableName.replace(/\.mgdb$/, '');
    const scoped = (this.name === 'default') ? clean : `${this.name}.${clean}`;
    return new TableHandle(this.client, scoped);
  }

  /**
   * List all tables and sub-tables within this database
   */
  async tables() {
    const res = await this.client._request('GET', `/tables?database=${encodeURIComponent(this.name)}`);
    return res.tables || [];
  }

  async listTables() {
    return await this.tables();
  }

  /**
   * Create a new table inside this database
   */
  async createTable(name, columns, blockSize = 1024) {
    const clean = name.replace(/\.mgdb$/, '');
    const scoped = (this.name === 'default') ? clean : `${this.name}.${clean}`;
    return await this.client.operation('create_table', {
      table: scoped,
      database: this.name,
      columns: columns,
      block_size: blockSize
    });
  }

  /**
   * Drop a table from this database
   */
  async dropTable(name) {
    const clean = name.replace(/\.mgdb$/, '');
    const scoped = (this.name === 'default') ? clean : `${this.name}.${clean}`;
    return await this.client.operation('drop', { table: scoped, database: this.name });
  }

  /**
   * Execute an analytical SQL query scoped to this database
   */
  async query(sql) {
    return await this.client.query(sql, { database: this.name });
  }

  /**
   * Permanently drop this database container
   */
  async drop() {
    return await this.client.dropDatabase(this.name);
  }
}

/**
 * Fluent table handle for document-like querying & schema manipulation
 */
class TableHandle {
  constructor(client, name) {
    this.client = client;
    this.name = name.endsWith('.mgdb') ? name : `${name}.mgdb`;
    this.pureName = this.name.replace(/\.mgdb$/, '');
  }

  /**
   * Fetch table schema definition and column metadata
   */
  async schema() {
    return await this.client._request('GET', `/table_schema?table=${encodeURIComponent(this.name)}`);
  }

  /**
   * Fetch paginated rows from table
   */
  async data(page = 1, limit = 50) {
    return await this.client._request('GET', `/table_data?table=${encodeURIComponent(this.name)}&page=${page}&limit=${limit}`);
  }

  /**
   * Find rows matching simple equality filters
   * @param {Object} [filters] E.g. { status: 'ACTIVE', age: 25 }
   * @param {Object} [options] E.g. { limit: 100, columns: ['id', 'name'] }
   */
  async find(filters = {}, options = {}) {
    const cols = (options.columns && options.columns.length) ? options.columns.join(', ') : '*';
    let query = `SELECT ${cols} FROM ${this.pureName}`;
    
    const conditions = [];
    for (const [key, val] of Object.entries(filters)) {
      if (val === null || val === undefined) {
        conditions.push(`${key} IS NULL`);
      } else if (typeof val === 'number' || typeof val === 'boolean') {
        conditions.push(`${key} = ${val}`);
      } else {
        const escaped = String(val).replace(/'/g, "''");
        conditions.push(`${key} = '${escaped}'`);
      }
    }

    if (conditions.length > 0) {
      query += ` WHERE ${conditions.join(' AND ')}`;
    }

    if (options.limit && Number.isInteger(options.limit)) {
      query += ` LIMIT ${options.limit}`;
    }

    const res = await this.client.query(query, { activeTable: this.name });
    if (!res || !res.columns || !res.rows) return [];

    // Map rows to objects
    const colNames = res.columns;
    return res.rows.map(row => {
      const obj = {};
      colNames.forEach((col, idx) => {
        obj[col] = row[idx];
      });
      return obj;
    });
  }

  /**
   * Find first row matching filter
   */
  async findOne(filters = {}) {
    const results = await this.find(filters, { limit: 1 });
    return results.length > 0 ? results[0] : null;
  }

  /**
   * Count rows matching filter
   */
  async count(filters = {}) {
    let query = `SELECT COUNT(*) FROM ${this.pureName}`;
    const conditions = [];
    for (const [key, val] of Object.entries(filters)) {
      if (val === null || val === undefined) {
        conditions.push(`${key} IS NULL`);
      } else if (typeof val === 'number' || typeof val === 'boolean') {
        conditions.push(`${key} = ${val}`);
      } else {
        const escaped = String(val).replace(/'/g, "''");
        conditions.push(`${key} = '${escaped}'`);
      }
    }
    if (conditions.length > 0) {
      query += ` WHERE ${conditions.join(' AND ')}`;
    }
    const res = await this.client.query(query, { activeTable: this.name });
    if (res && res.rows && res.rows.length > 0) {
      return res.rows[0][0];
    }
    return 0;
  }

  /**
   * Export table in given format ('csv', 'json', 'jsonl', 'sql')
   */
  async export(format = 'json') {
    return await this.client._request('GET', `/export?table=${encodeURIComponent(this.name)}&format=${format}`);
  }

  /**
   * Stream table export directly to a file with zero RAM memory buffering.
   * @param {string} destPath Local destination file
   * @param {string} [format='csv'] 'csv', 'json', 'jsonl', 'sql'
   */
  async exportToFile(destPath, format = 'csv') {
    return new Promise((resolve, reject) => {
      const client = this.client.protocol === 'https:' ? https : http;
      const req = client.request({
        protocol: this.client.protocol,
        hostname: this.client.host,
        port: this.client.port,
        method: 'GET',
        path: `/export?table=${encodeURIComponent(this.name)}&format=${encodeURIComponent(format)}`,
        timeout: this.client.timeout
      }, (res) => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          return reject(new MergenError(`Export failed with HTTP ${res.statusCode}`, res.statusCode));
        }
        const fileStream = fs.createWriteStream(destPath);
        res.pipe(fileStream);
        fileStream.on('finish', () => {
          fileStream.close();
          resolve(destPath);
        });
        fileStream.on('error', (err) => {
          fs.unlink(destPath, () => {});
          reject(err);
        });
      });
      req.on('error', reject);
      req.end();
    });
  }

  /**
   * Import data string (CSV, SQL, or JSON) into this table
   */
  async import(content, format = 'csv') {
    return await this.client._request('POST', '/import', {
      table: this.pureName,
      format: format,
      content: content
    });
  }

  /**
   * Stream a local file (CSV, SQL, JSON) directly into table with strictly bounded RAM.
   * @param {string} filePath Local file path to stream
   * @param {string} [format='csv'] 'csv', 'sql', 'json', 'jsonl'
   */
  async importFile(filePath, format = 'csv') {
    if (!fs.existsSync(filePath)) {
      throw new MergenError(`File not found for import: ${filePath}`, 404);
    }
    const stat = fs.statSync(filePath);
    return new Promise((resolve, reject) => {
      const client = this.client.protocol === 'https:' ? https : http;
      const req = client.request({
        protocol: this.client.protocol,
        hostname: this.client.host,
        port: this.client.port,
        method: 'POST',
        path: `/import_stream?table=${encodeURIComponent(this.name)}&format=${encodeURIComponent(format)}`,
        headers: {
          'Content-Type': 'application/octet-stream',
          'Content-Length': stat.size
        },
        timeout: this.client.timeout
      }, (res) => {
        let rawData = '';
        res.setEncoding('utf8');
        res.on('data', chunk => { rawData += chunk; });
        res.on('end', () => {
          try {
            const parsed = JSON.parse(rawData);
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(parsed);
            } else {
              reject(new MergenError(parsed.error || `HTTP ${res.statusCode}`, res.statusCode, parsed));
            }
          } catch(e) {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve({ success: true, message: rawData });
            } else {
              reject(new MergenError(rawData || `HTTP ${res.statusCode}`, res.statusCode));
            }
          }
        });
      });
      req.on('error', reject);

      const fileStream = fs.createReadStream(filePath, { highWaterMark: 64 * 1024 });
      fileStream.pipe(req);
    });
  }

  /**
   * Create a nested sub-table under this table (e.g. table.subtable)
   */
  async createSubtable(subtableName, columns, blockSize = 1024) {
    const cleanSub = subtableName.replace(/\.mgdb$/, '');
    const fullSub = `${this.pureName}.${cleanSub}`;
    return await this.client.operation('create_subtable', {
      table: fullSub,
      parent_table: this.pureName,
      columns: columns,
      block_size: blockSize
    });
  }

  /**
   * Get handle to a nested sub-table
   */
  subtable(subtableName) {
    const cleanSub = subtableName.replace(/\.mgdb$/, '');
    const fullSub = `${this.pureName}.${cleanSub}`;
    return new TableHandle(this.client, fullSub);
  }

  /**
   * List all nested sub-tables of this table
   */
  async listSubtables() {
    const all = await this.client.tables();
    return all.filter(t => t.parent === this.pureName || (t.type === 'subtable' && t.full_name && t.full_name.startsWith(this.pureName + '.')));
  }

  /**
   * Insert one or multiple row objects into table
   * @param {Object|Array<Object>} records Single object or array of row objects
   */
  async insert(records) {
    return await this.client.operation('insert', {
      table: this.name,
      row: records
    });
  }

  /**
   * Search for a substring across all text columns (full-text search)
   * @param {string} term Substring to search
   */
  async search(term) {
    const schema = await this.schema();
    const strCols = (schema.columns || []).filter(c => c.type === 'STRING').map(c => c.name);
    if (strCols.length === 0) return [];
    
    const conditions = strCols.map(c => `${c} LIKE '%${String(term).replace(/'/g, "''")}%'`);
    const sql = `SELECT * FROM ${this.pureName} WHERE ${conditions.join(' OR ')}`;
    const res = await this.client.query(sql, { activeTable: this.name });
    if (!res || !res.columns || !res.rows) return [];
    const colNames = res.columns;
    return res.rows.map(row => {
      const obj = {};
      colNames.forEach((col, idx) => { obj[col] = row[idx]; });
      return obj;
    });
  }

  /**
   * Update matching records
   * @param {Object} updates Column-value pairs to set
   * @param {string} where WHERE condition clause
   */
  async update(updates, where) {
    if (!where) throw new MergenError("A WHERE clause is required for update()");
    const setClauses = [];
    for (const [key, val] of Object.entries(updates)) {
      if (val === null || val === undefined) {
        setClauses.push(`${key} = NULL`);
      } else if (typeof val === 'number' || typeof val === 'boolean') {
        setClauses.push(`${key} = ${val}`);
      } else {
        setClauses.push(`${key} = '${String(val).replace(/'/g, "''")}'`);
      }
    }
    const sql = `UPDATE ${this.pureName} SET ${setClauses.join(', ')} WHERE ${where}`;
    return await this.client.query(sql, { activeTable: this.name });
  }

  /**
   * Delete matching records
   * @param {string} where WHERE condition clause
   */
  async delete(where) {
    if (!where) throw new MergenError("A WHERE clause is required for delete()");
    return await this.client.operation('delete', {
      table: this.name,
      where: where
    });
  }

  /**
   * Add a new column to the table schema
   */
  async addColumn(name, type = 'STRING', defaultVal = null) {
    return await this.client.operation('add_column', {
      table: this.name,
      name: name,
      type: type,
      default: defaultVal
    });
  }

  /**
   * Drop a column from the table
   */
  async dropColumn(name) {
    return await this.client.operation('drop_column', {
      table: this.name,
      name: name
    });
  }

  /**
   * Rename an existing column
   */
  async renameColumn(oldName, newName) {
    return await this.client.operation('rename_column', {
      table: this.name,
      old_name: oldName,
      new_name: newName
    });
  }

  /**
   * Clear all records from this table while preserving schema
   */
  async truncate() {
    return await this.client.truncateTable(this.name);
  }

  /**
   * Permanently delete this table file
   */
  async drop() {
    return await this.client.dropTable(this.name);
  }
}

/**
 * Factory helper function to connect to MergenDB
 * @param {string|Object} options URL string or configuration object
 * @returns {MergenDB}
 */
function connect(options) {
  return new MergenDB(options);
}

/**
 * Programmatically starts the local MergenDB server using native child_process.
 * @param {Object} options Server options (port, host, detached)
 * @returns {import('child_process').ChildProcess}
 */
function startServer(options = {}) {
  const port = options.port || 8765;
  const candidates = ['mergen', 'python', 'python3', 'py'];
  let found = null;
  for (const c of candidates) {
    try {
      execSync(`${c} --version`, { stdio: 'ignore' });
      found = c;
      break;
    } catch (e) {}
  }
  if (!found) {
    throw new MergenError("Python 3.8+ or 'mergen' CLI was not found in PATH to start server automatically.", 500);
  }
  const args = (found === 'mergen') ? ['serve', String(port)] : ['-m', 'mergendb.server.server', '--port', String(port)];
  const proc = spawn(found, args, { stdio: 'ignore', detached: Boolean(options.detached) });
  if (!options.detached) {
    process.on('exit', () => {
      try { proc.kill(); } catch (e) {}
    });
  }
  return proc;
}

module.exports = {
  MergenDB,
  Database: DatabaseHandle,
  DatabaseHandle,
  Table: TableHandle,
  TableHandle,
  MergenError,
  connect,
  open: connect,
  startServer,
  default: connect
};

