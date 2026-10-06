#!/usr/bin/env node

/**
 * MergenDB CLI Runner for Node.js / npm
 * Zero external dependencies. Uses Node.js native child_process and http.
 */

'use strict';

const { spawn, execSync } = require('child_process');
const http = require('http');

const args = process.argv.slice(2);
const cmd = args[0] || '--help';

function printHelp() {
  console.log(`
MergenDB Node.js CLI Runner (Zero-Dependency)

Usage:
  npx mergendb serve [port]       Start MergenDB HTTP & Studio Server (default: 8765)
  npx mergendb studio [port]      Start server and open Mergen Studio in browser
  npx mergendb test               Run full test suite & device hardware benchmark
  npx mergendb benchmark          Run speed benchmark (rows/sec)
  npx mergendb query "<SQL>"      Execute SQL query against local running server
  npx mergendb --version          Display MergenDB version
  npx mergendb --help             Display this help message
`);
}

function findPythonCommand() {
  const candidates = ['mergen', 'python', 'python3', 'py'];
  for (const c of candidates) {
    try {
      execSync(`${c} --version`, { stdio: 'ignore' });
      return c;
    } catch (e) {
      // Continue searching
    }
  }
  return null;
}

function openBrowser(url) {
  const start = (process.platform === 'darwin' ? 'open' :
                 process.platform === 'win32' ? 'start' : 'xdg-open');
  try {
    execSync(`${start} ${url}`);
  } catch (e) {
    console.log(`Open in browser: ${url}`);
  }
}

async function runQuery(sqlText, port = 8765) {
  const payload = JSON.stringify({ query: sqlText });
  const req = http.request({
    hostname: '127.0.0.1',
    port: port,
    path: '/query',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
      'Authorization': 'Basic ' + Buffer.from('root:').toString('base64')
    }
  }, (res) => {
    let data = '';
    res.on('data', chunk => { data += chunk; });
    res.on('end', () => {
      try {
        const json = JSON.parse(data);
        if (json.success) {
          console.table(json.rows);
          console.log(`\n[+] ${json.row_count} rows in ${json.stats.execution_time_ms} ms (Blocks scanned: ${json.stats.blocks_scanned}, skipped: ${json.stats.blocks_skipped})`);
        } else {
          console.error(`[-] Query Error: ${json.error}`);
          process.exit(1);
        }
      } catch (err) {
        console.log(data);
      }
    });
  });

  req.on('error', (err) => {
    console.error(`[-] Could not connect to MergenDB server on port ${port}. Is it running? (${err.message})`);
    console.error(`    Run 'npx mergendb serve' to start the server.`);
    process.exit(1);
  });

  req.write(payload);
  req.end();
}

function main() {
  if (cmd === '--help' || cmd === '-h' || cmd === 'help') {
    printHelp();
    process.exit(0);
  }

  if (cmd === '--version' || cmd === '-v' || cmd === 'version') {
    const pkg = require('../package.json');
    console.log(`MergenDB v${pkg.version} (Node.js SDK)`);
    process.exit(0);
  }

  if (cmd === 'query') {
    const queryStr = args[1];
    if (!queryStr) {
      console.error("[-] Error: Missing SQL query string. Example: npx mergendb query 'SELECT * FROM users'");
      process.exit(1);
    }
    runQuery(queryStr);
    return;
  }

  const py = findPythonCommand();
  if (!py) {
    console.error("[-] Error: Python runtime or 'mergen' CLI was not found in PATH.");
    console.error("    Please install Python 3.8+ (https://python.org) or install mergendb via pip: 'pip install mergendb'");
    process.exit(1);
  }

  let spawnArgs = [];
  if (py === 'mergen') {
    spawnArgs = args;
  } else {
    // py, python, or python3
    if (cmd === 'serve' || cmd === 'studio') {
      const port = args[1] || '8765';
      spawnArgs = ['-m', 'mergendb.server.server', '--port', port];
      if (cmd === 'studio') {
        setTimeout(() => openBrowser(`http://localhost:${port}/studio`), 1200);
      }
    } else {
      spawnArgs = ['-m', 'mergendb', ...args];
    }
  }

  const child = spawn(py, spawnArgs, { stdio: 'inherit' });
  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

main();
