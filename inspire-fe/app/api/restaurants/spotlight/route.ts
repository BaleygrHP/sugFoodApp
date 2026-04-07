import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { Restaurant, MenuItem } from '@/app/page';

// GET /api/restaurants/spotlight - Get restaurant with highest pick count
export async function GET() {
  try {
    // Get restaurant with highest pick_count
    const restaurantResult = await query(
      `
      SELECT 
        id,
        name,
        cuisine,
        price_range as "priceRange",
        rating,
        distance,
        hours,
        address,
        image,
        pick_count as "pickCount",
        description,
        reviews,
        latitude,
        longitude
      FROM restaurants
      ORDER BY pick_count DESC, rating DESC
      LIMIT 1
    `
    );

    if (restaurantResult.rows.length === 0) {
      return NextResponse.json(
        { error: 'No restaurants found' },
        { status: 404 }
      );
    }

    const restaurant = restaurantResult.rows[0];

    // Get menu items for this restaurant
    const menuItemsResult = await query(
      `
      SELECT name, price
      FROM menu_items
      WHERE restaurant_id = $1
      ORDER BY name
    `,
      [restaurant.id]
    );

    const menuItems: MenuItem[] = menuItemsResult.rows.map((item: any) => ({
      name: item.name,
      price: parseFloat(item.price),
    }));

    const result: Restaurant = {
      id: restaurant.id,
      name: restaurant.name,
      cuisine: restaurant.cuisine,
      priceRange: restaurant.priceRange,
      rating: parseFloat(restaurant.rating),
      distance: restaurant.distance,
      hours: restaurant.hours,
      address: restaurant.address,
      image: restaurant.image || '',
      pickCount: restaurant.pickCount,
      description: restaurant.description || '',
      menuItems: menuItems,
      reviews: restaurant.reviews,
      latitude: restaurant.latitude ? parseFloat(restaurant.latitude) : undefined,
      longitude: restaurant.longitude ? parseFloat(restaurant.longitude) : undefined,
    };

    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    console.error('Error fetching spotlight restaurant:', error);
    return NextResponse.json(
      { error: 'Failed to fetch spotlight restaurant' },
      { status: 500 }
    );
  }
}

