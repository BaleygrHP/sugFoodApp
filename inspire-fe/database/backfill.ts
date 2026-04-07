import { readFileSync } from "fs";
import path from "path";

import dotenv from "dotenv";
import { Pool } from "pg";

dotenv.config({ path: path.resolve(process.cwd(), ".env.local") });

const pool = new Pool({
  host: process.env.DB_HOST || "localhost",
  port: Number.parseInt(process.env.DB_PORT || "5432", 10),
  database: process.env.DB_NAME || "inspire",
  user: process.env.DB_USER || "postgres",
  password: process.env.DB_PASSWORD || "postgres",
});

function normalizeText(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

async function ensureSchema() {
  const schemaPath = path.resolve(process.cwd(), "database", "schema.sql");
  const sql = readFileSync(schemaPath, "utf8");
  await pool.query(sql);
}

export async function backfillDomainData() {
  await ensureSchema();

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    const cuisineResult = await client.query<{
      cuisine: string;
    }>(`
      SELECT DISTINCT cuisine
      FROM restaurants
      WHERE cuisine IS NOT NULL
    `);

    for (const row of cuisineResult.rows) {
      const cuisineCode = normalizeText(row.cuisine).replace(/\s+/g, "_");
      await client.query(
        `
          INSERT INTO cuisines (code, name)
          VALUES ($1, $2)
          ON CONFLICT (code) DO NOTHING
        `,
        [cuisineCode, row.cuisine],
      );
    }

    const menuResult = await client.query<{
      restaurant_id: string;
      name: string;
      price: string;
      cuisine: string;
    }>(`
      SELECT mi.restaurant_id, mi.name, mi.price, r.cuisine
      FROM menu_items mi
      JOIN restaurants r ON r.id = mi.restaurant_id
    `);

    for (const row of menuResult.rows) {
      const cuisineCode = normalizeText(row.cuisine).replace(/\s+/g, "_");
      const cuisineLookup = await client.query<{ id: string }>(
        `
          SELECT id
          FROM cuisines
          WHERE code = $1
          LIMIT 1
        `,
        [cuisineCode],
      );

      const dishResult = await client.query<{ id: string }>(
        `
          INSERT INTO dishes (name, normalized_name, cuisine_id, tags_json)
          VALUES ($1, $2, $3, $4::jsonb)
          ON CONFLICT DO NOTHING
          RETURNING id
        `,
        [
          row.name,
          normalizeText(row.name),
          cuisineLookup.rows[0]?.id || null,
          JSON.stringify([]),
        ],
      );

      let dishId = dishResult.rows[0]?.id;
      if (!dishId) {
        const existingDish = await client.query<{ id: string }>(
          `
            SELECT id
            FROM dishes
            WHERE normalized_name = $1
            LIMIT 1
          `,
          [normalizeText(row.name)],
        );
        dishId = existingDish.rows[0]?.id;
      }

      if (!dishId) continue;

      await client.query(
        `
          INSERT INTO restaurant_dishes (restaurant_id, dish_id, current_price, metadata_json)
          VALUES ($1, $2, $3, $4::jsonb)
          ON CONFLICT (restaurant_id, dish_id) DO UPDATE SET
            current_price = EXCLUDED.current_price,
            metadata_json = EXCLUDED.metadata_json
        `,
        [row.restaurant_id, dishId, row.price, JSON.stringify({ source: "legacy_menu_items" })],
      );
    }

    const restaurantResult = await client.query<{
      id: string;
      name: string;
      rating: string;
      supports_invoice: boolean;
    }>(`
      SELECT id, name, rating, supports_invoice
      FROM restaurants
    `);

    for (const row of restaurantResult.rows) {
      await client.query(
        `
          UPDATE restaurants
          SET normalized_name = $2
          WHERE id = $1
        `,
        [row.id, normalizeText(row.name)],
      );

      await client.query(
        `
          INSERT INTO vendors (
            restaurant_id,
            source_system,
            approval_status,
            invoice_supported,
            reliability_score,
            imported_payload_json
          )
          VALUES ($1, 'manual_seed', 'approved', $2, $3, $4::jsonb)
          ON CONFLICT (restaurant_id) DO UPDATE SET
            reliability_score = EXCLUDED.reliability_score,
            invoice_supported = EXCLUDED.invoice_supported,
            imported_payload_json = EXCLUDED.imported_payload_json,
            updated_at = CURRENT_TIMESTAMP
        `,
        [
          row.id,
          row.supports_invoice,
          Math.min(Math.max(Number(row.rating) / 5, 0.4), 0.99),
          JSON.stringify({ importedAt: new Date().toISOString() }),
        ],
      );
    }

    await client.query(`
      UPDATE restaurants r
      SET
        avg_price_min = price_stats.min_price,
        avg_price_max = price_stats.max_price,
        updated_at = CURRENT_TIMESTAMP
      FROM (
        SELECT
          restaurant_id,
          MIN(price) AS min_price,
          MAX(price) AS max_price
        FROM menu_items
        WHERE price > 0
        GROUP BY restaurant_id
      ) AS price_stats
      WHERE r.id = price_stats.restaurant_id
    `);

    const participantResult = await client.query<{
      id: string;
      name: string | null;
      room_id: string;
      joined_at: Date | string;
    }>(`
      SELECT id, name, room_id, joined_at
      FROM participants
    `);

    for (const row of participantResult.rows) {
      await client.query(
        `
          INSERT INTO users (id, display_name, account_status, role)
          VALUES ($1, $2, 'guest', 'guest')
          ON CONFLICT (id) DO NOTHING
        `,
        [row.id, row.name || `Guest-${row.id.slice(0, 8)}`],
      );

      await client.query(
        `
          INSERT INTO user_profiles (user_id)
          VALUES ($1)
          ON CONFLICT (user_id) DO NOTHING
        `,
        [row.id],
      );

      await client.query(
        `
          INSERT INTO room_members (room_id, user_id, role, participation_status, joined_at)
          VALUES ($1, $2, 'member', 'joined', $3)
          ON CONFLICT (room_id, user_id) DO NOTHING
        `,
        [row.room_id, row.id, row.joined_at],
      );
    }

    const roomHosts = await client.query<{
      room_id: string;
      host_user_id: string;
    }>(`
      SELECT DISTINCT ON (p.room_id)
        p.room_id,
        p.id AS host_user_id
      FROM participants p
      ORDER BY p.room_id, p.joined_at ASC
    `);

    for (const row of roomHosts.rows) {
      await client.query(
        `
          UPDATE rooms
          SET
            host_user_id = $2,
            name = COALESCE(name, title, 'Team Lunch'),
            title = COALESCE(title, name, 'Team Lunch'),
            updated_at = CURRENT_TIMESTAMP
          WHERE id = $1
        `,
        [row.room_id, row.host_user_id],
      );

      await client.query(
        `
          UPDATE room_members
          SET role = 'host'
          WHERE room_id = $1 AND user_id = $2
        `,
        [row.room_id, row.host_user_id],
      );
    }

    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

backfillDomainData()
  .then(async () => {
    console.log("Backfill completed");
    await pool.end();
  })
  .catch(async (error) => {
    console.error("Backfill failed", error);
    await pool.end();
    process.exit(1);
  });
