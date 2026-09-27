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
  }

  /**
   * Internal HTTP requester (zero external dependencies)
   */
  _request(method, path, body = null, headers = {}) {
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

module.exports = {
  MergenDB,
  TableHandle,
  MergenError,
  connect,
  default: connect
};
