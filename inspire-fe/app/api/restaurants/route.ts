import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { Restaurant, MenuItem } from '@/app/page';
import { randomUUID } from 'crypto';

// GET /api/restaurants - Get all restaurants
// Frontend will handle filtering and sorting
export async function GET() {
  try {
    // Get all restaurants (no filtering - done on frontend)
    const sql = `
      SELECT 
        r.id,
        r.name,
        r.cuisine,
        r.price_range as "priceRange",
        r.rating,
        r.distance,
        r.hours,
        r.address,
        r.image,
        r.pick_count as "pickCount",
        r.description,
        r.reviews,
        r.latitude,
        r.longitude
      FROM restaurants r
      ORDER BY r.rating DESC, r.name ASC
    `;

    const restaurantsResult = await query(sql);

    // Get menu items for all restaurants
    const restaurantIds = restaurantsResult.rows.map((r: any) => r.id);
    let menuItemsResult: any = { rows: [] };

    if (restaurantIds.length > 0) {
      const menuSql = `
        SELECT restaurant_id, name, price
        FROM menu_items
        WHERE restaurant_id = ANY($1)
        ORDER BY restaurant_id, name
      `;
      menuItemsResult = await query(menuSql, [restaurantIds]);
    }

    // Group menu items by restaurant_id
    const menuItemsByRestaurant: { [key: string]: MenuItem[] } = {};
    menuItemsResult.rows.forEach((item: any) => {
      if (!menuItemsByRestaurant[item.restaurant_id]) {
        menuItemsByRestaurant[item.restaurant_id] = [];
      }
      menuItemsByRestaurant[item.restaurant_id].push({
        name: item.name,
        price: parseFloat(item.price),
      });
    });

    // Combine restaurants with their menu items
    const restaurants: Restaurant[] = restaurantsResult.rows.map((r: any) => ({
      id: r.id,
      name: r.name,
      cuisine: r.cuisine,
      priceRange: r.priceRange,
      rating: parseFloat(r.rating),
      distance: r.distance,
      hours: r.hours,
      address: r.address,
      image: r.image || '',
      pickCount: r.pickCount,
      description: r.description || '',
      menuItems: menuItemsByRestaurant[r.id] || [],
      reviews: r.reviews,
      latitude: r.latitude ? parseFloat(r.latitude) : undefined,
      longitude: r.longitude ? parseFloat(r.longitude) : undefined,
    }));

    return NextResponse.json(restaurants, { status: 200 });
  } catch (error) {
    console.error('Error fetching restaurants:', error);
    return NextResponse.json(
      { error: 'Failed to fetch restaurants' },
      { status: 500 }
    );
  }
}

// POST /api/restaurants - Create a new restaurant
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      name,
      address,
      latitude,
      longitude,
      cuisine = 'Other',
      menuItems = [],
      image,
    } = body;

    // Validate required fields
    if (!name || !address) {
      return NextResponse.json(
        { error: 'Name and address are required' },
        { status: 400 }
      );
    }

    if (!latitude || !longitude) {
      return NextResponse.json(
        { error: 'Latitude and longitude are required' },
        { status: 400 }
      );
    }

    // Generate restaurant ID
    const restaurantId = `restaurant-${randomUUID()}`;

    // Calculate distance (simplified - you might want to calculate from user location)
    const distance = '0.5 km'; // Default distance

    // Determine price range from menu items
    let priceRange = '$';
    if (menuItems.length > 0) {
      const prices = menuItems.map((item: { price: number }) => item.price).filter((p: number) => p > 0);
      if (prices.length > 0) {
        const avgPrice = prices.reduce((a: number, b: number) => a + b, 0) / prices.length;
        if (avgPrice >= 100) {
          priceRange = '$$$';
        } else if (avgPrice >= 50) {
          priceRange = '$$';
        }
      }
    }

    // Insert restaurant
    const restaurantResult = await query(
      `
      INSERT INTO restaurants (
        id, name, cuisine, price_range, rating, distance, hours, address,
        latitude, longitude, description, reviews, pick_count, image
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
      RETURNING id, name, cuisine, price_range as "priceRange", rating, distance,
                hours, address, latitude, longitude, description, reviews, pick_count as "pickCount", image
    `,
      [
        restaurantId,
        name,
        cuisine,
        priceRange,
        4.0, // Default rating
        distance,
        '9:00 AM - 10:00 PM', // Default hours
        address,
        latitude,
        longitude,
        `A great place to eat at ${address}`,
        0, // reviews
        0, // pick_count
        image || null, // Image (base64 data URL or URL)
      ]
    );

    const restaurant = restaurantResult.rows[0];

    // Insert menu items
    if (menuItems.length > 0) {
      // Always add "Anything" as default menu item
      await query(
        `
        INSERT INTO menu_items (restaurant_id, name, price)
        VALUES ($1, $2, $3)
      `,
        [restaurantId, 'Anything', 0]
      );

      // Insert other menu items
      for (const item of menuItems) {
        if (item.name && item.name.trim() !== '') {
          await query(
            `
            INSERT INTO menu_items (restaurant_id, name, price)
            VALUES ($1, $2, $3)
          `,
            [restaurantId, item.name.trim(), item.price || 0]
          );
        }
      }
    } else {
      // If no menu items, add default "Anything"
      await query(
        `
        INSERT INTO menu_items (restaurant_id, name, price)
        VALUES ($1, $2, $3)
      `,
        [restaurantId, 'Anything', 0]
      );
    }

    return NextResponse.json(
      {
        id: restaurant.id,
        name: restaurant.name,
        cuisine: restaurant.cuisine,
        priceRange: restaurant.priceRange,
        rating: parseFloat(restaurant.rating),
        distance: restaurant.distance,
        hours: restaurant.hours,
        address: restaurant.address,
        latitude: parseFloat(restaurant.latitude),
        longitude: parseFloat(restaurant.longitude),
        description: restaurant.description,
        reviews: restaurant.reviews,
        pickCount: restaurant.pickCount,
        image: restaurant.image || '',
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error creating restaurant:', error);
    return NextResponse.json(
      { error: 'Failed to create restaurant' },
      { status: 500 }
    );
  }
}
