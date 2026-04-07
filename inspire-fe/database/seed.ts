import { Pool } from 'pg';
import { mockRestaurants } from '../data/restaurants';
import dotenv from 'dotenv';
import path from 'path';
import { readFileSync } from 'fs';

// Load environment variables
dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

// Database connection configuration
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'inspire',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
});

async function seedDatabase() {
  const client = await pool.connect();
  
  try {
    console.log('🌱 Starting database seed...');
    
    const schemaPath = path.resolve(process.cwd(), 'database', 'schema.sql');
    const schemaSql = readFileSync(schemaPath, 'utf8');
    await client.query(schemaSql);

    // Begin transaction
    await client.query('BEGIN');

    // Clear existing data
    console.log('🗑️  Clearing existing data...');
    await client.query('DELETE FROM menu_items');
    await client.query('DELETE FROM restaurants');

    // Insert restaurants
    console.log(`📝 Inserting ${mockRestaurants.length} restaurants...`);
    
    for (const restaurant of mockRestaurants) {
      const restaurantQuery = `
        INSERT INTO restaurants (
          id, name, cuisine, price_range, rating, distance, hours, 
          address, image, pick_count, description, reviews, latitude, longitude
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (id) DO UPDATE SET
          name = EXCLUDED.name,
          cuisine = EXCLUDED.cuisine,
          price_range = EXCLUDED.price_range,
          rating = EXCLUDED.rating,
          distance = EXCLUDED.distance,
          hours = EXCLUDED.hours,
          address = EXCLUDED.address,
          image = EXCLUDED.image,
          pick_count = EXCLUDED.pick_count,
          description = EXCLUDED.description,
          reviews = EXCLUDED.reviews,
          latitude = EXCLUDED.latitude,
          longitude = EXCLUDED.longitude,
          updated_at = CURRENT_TIMESTAMP
      `;

      await client.query(restaurantQuery, [
        restaurant.id,
        restaurant.name,
        restaurant.cuisine,
        restaurant.priceRange,
        restaurant.rating,
        restaurant.distance,
        restaurant.hours,
        restaurant.address,
        restaurant.image,
        restaurant.pickCount,
        restaurant.description,
        restaurant.reviews,
        restaurant.latitude || null,
        restaurant.longitude || null,
      ]);

      // Insert default "Anything" menu item for every restaurant
      const defaultMenuItemQuery = `
        INSERT INTO menu_items (restaurant_id, name, price)
        VALUES ($1, $2, $3)
        ON CONFLICT (restaurant_id, name) DO UPDATE SET
          price = EXCLUDED.price,
          updated_at = CURRENT_TIMESTAMP
      `;
      
      await client.query(defaultMenuItemQuery, [
        restaurant.id,
        'Anything',
        0,
      ]);

      // Insert menu items for this restaurant (if any)
      if (restaurant.menuItems && restaurant.menuItems.length > 0) {
        for (const menuItem of restaurant.menuItems) {
          const menuItemQuery = `
            INSERT INTO menu_items (restaurant_id, name, price)
            VALUES ($1, $2, $3)
            ON CONFLICT (restaurant_id, name) DO UPDATE SET
              price = EXCLUDED.price,
              updated_at = CURRENT_TIMESTAMP
          `;
          
          await client.query(menuItemQuery, [
            restaurant.id,
            menuItem.name,
            menuItem.price,
          ]);
        }
      }
    }

    // Commit transaction
    await client.query('COMMIT');
    
    console.log('✅ Database seeded successfully!');
    console.log(`   - ${mockRestaurants.length} restaurants inserted`);
    
    const menuItemCount = mockRestaurants.length + mockRestaurants.reduce(
      (sum, r) => sum + (r.menuItems?.length || 0),
      0
    );
    console.log(`   - ${menuItemCount} menu items inserted (${mockRestaurants.length} default "Anything" + ${mockRestaurants.reduce((sum, r) => sum + (r.menuItems?.length || 0), 0)} from data)`);
    
  } catch (error) {
    // Rollback on error
    await client.query('ROLLBACK');
    console.error('❌ Error seeding database:', error);
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

// Run seed
seedDatabase()
  .then(() => {
    console.log('🎉 Seed completed!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('💥 Seed failed:', error);
    process.exit(1);
  });

export { seedDatabase };

