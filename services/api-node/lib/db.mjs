// S4: a thin layer over `pg`, no ORM. Three parity rules make it safe for a
// backend written against SQLite's `?` placeholders to run on PostgreSQL:
//   * `?` is rewritten to `$n` without touching string literals or comments;
//   * BIGINT arrives as a JavaScript number when that is lossless (Python's
//     sqlite3 returns int, so a string here would change the JSON on the wire);
//   * a statement that runs out of budget surfaces as QueryDeadlineExceeded,
//     which the HTTP layer maps to the same 504 body Python sends.
import pg from 'pg';

const { Pool, types } = pg;

// int8 → number when safe. 11.25 also has journaled IDs far below 2^53.
types.setTypeParser(20, (value) => {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : value;
});

export class QueryDeadlineExceeded extends Error {
  constructor() {
    super('The database request exceeded its time budget');
    this.name = 'QueryDeadlineExceeded';
  }
}

export class SchemaMismatchError extends Error {
  constructor(message, missing) {
    super(message);
    this.name = 'SchemaMismatchError';
    this.missing = missing;
  }
}

/**
 * Rewrite `?` placeholders to `$1..$n`, leaving single-quoted strings,
 * double-quoted identifiers, `--` comments and `/* *\/` blocks untouched.
 */
export function toPlaceholders(sql) {
  let out = '';
  let state = 'normal';
  let index = 0;
  for (let i = 0; i < sql.length; i += 1) {
    const char = sql[i];
    const next = sql[i + 1];
    if (state === 'normal') {
      if (char === "'") state = 'single';
      else if (char === '"') state = 'double';
      else if (char === '-' && next === '-') state = 'line';
      else if (char === '/' && next === '*') state = 'block';
      else if (char === '?') {
        index += 1;
        out += `$${index}`;
        continue;
      }
      out += char;
      continue;
    }
    out += char;
    if (state === 'single' && char === "'") {
      if (next === "'") {
        out += next;
        i += 1;
      } else state = 'normal';
    } else if (state === 'double' && char === '"') {
      if (next === '"') {
        out += next;
        i += 1;
      } else state = 'normal';
    } else if (state === 'line' && char === '\n') {
      state = 'normal';
    } else if (state === 'block' && char === '*' && next === '/') {
      out += next;
      i += 1;
      state = 'normal';
    }
  }
  return out;
}

/**
 * The schema contract this service boots against. Python owns migrations, and
 * the schema carries no version counter — so instead of comparing a number,
 * the service asserts the tables and columns the ported queries depend on.
 */
export const REQUIRED_SCHEMA = {
  users: ['id', 'email', 'email_hash', 'password_hash', 'salt', 'created_at'],
  guests: ['id', 'invitation_id', 'name', 'slug', 'token'],
  invitations: ['id', 'slug', 'is_published', 'archived', 'deleted_at', 'owner_id'],
  publications: ['invitation_id', 'document_json', 'version', 'published_at'],
};

export async function assertSchema(db) {
  const result = await db.query(
    "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'",
  );
  const seen = new Map();
  for (const row of result.rows) {
    if (!seen.has(row.table_name)) seen.set(row.table_name, new Set());
    seen.get(row.table_name).add(row.column_name);
  }
  const missing = [];
  for (const [table, columns] of Object.entries(REQUIRED_SCHEMA)) {
    if (!seen.has(table)) {
      missing.push(`${table}.*`);
      continue;
    }
    for (const column of columns) {
      if (!seen.get(table).has(column)) missing.push(`${table}.${column}`);
    }
  }
  if (missing.length) {
    throw new SchemaMismatchError(
      `Schema contract not satisfied; missing ${missing.join(', ')}`,
      missing,
    );
  }
  return true;
}

/**
 * Per-request deadline. The pool also applies statement_timeout, so a runaway
 * query is cancelled server-side; this wrapper bounds the wait even when the
 * connection itself stalls.
 */
export async function withDeadline(budgetMs, operation) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new QueryDeadlineExceeded()), budgetMs);
  });
  try {
    return await Promise.race([operation(), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

export function createDatabase({
  connectionString = process.env.EINVITE_DATABASE_URL,
  max = Number.parseInt(process.env.EINVITE_DB_POOL_MAX ?? '10', 10),
  budgetMs = Number.parseInt(process.env.EINVITE_DB_BUDGET_MS ?? '2000', 10),
} = {}) {
  if (!connectionString) throw new Error('EINVITE_DATABASE_URL is required');
  const pool = new Pool({
    connectionString,
    max,
    statement_timeout: budgetMs,
    query_timeout: budgetMs,
    connectionTimeoutMillis: budgetMs,
    application_name: 'einvite-api-node',
  });

  return {
    pool,
    budgetMs,
    async query(sql, params = []) {
      try {
        return await pool.query(toPlaceholders(sql), params);
      } catch (error) {
        // 57014 is PostgreSQL cancelling the statement at statement_timeout;
        // "Query read timeout" is pg's own query_timeout, which carries no
        // code. Both mean the request ran out of budget and must become a 504.
        if (
          error.code === '57014' ||
          /query read timeout|statement timeout|canceling statement/i.test(error.message ?? '')
        ) {
          throw new QueryDeadlineExceeded();
        }
        throw error;
      }
    },
    async close() {
      await pool.end();
    },
  };
}
