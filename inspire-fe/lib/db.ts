import { Pool, PoolClient, QueryResult } from "pg";

let pool: Pool | null = null;

function createPool() {
  return new Pool({
    host: process.env.DB_HOST || "localhost",
    port: Number.parseInt(process.env.DB_PORT || "5432", 10),
    database: process.env.DB_NAME || "inspire",
    user: process.env.DB_USER || "postgres",
    password: process.env.DB_PASSWORD || "postgres",
    max: Number.parseInt(process.env.DB_MAX_CONNECTIONS || "10", 10),
    idleTimeoutMillis: 30_000,
  });
}

export function getPool(): Pool {
  if (!pool) {
    pool = createPool();
  }

  return pool;
}

export async function query<T = unknown>(
  text: string,
  params?: unknown[],
  client?: PoolClient,
): Promise<QueryResult<T>> {
  const executor = client ?? getPool();
  return executor.query<T>(text, params);
}

export async function withTransaction<T>(
  callback: (client: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await getPool().connect();

  try {
    await client.query("BEGIN");
    const result = await callback(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function closePool() {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

