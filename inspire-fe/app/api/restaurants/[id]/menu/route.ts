import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { MenuItem } from '@/app/page';

// GET /api/restaurants/[id]/menu - Get menu items for a restaurant
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Verify restaurant exists
    const restaurantCheck = await query(
      'SELECT id FROM restaurants WHERE id = $1',
      [id]
    );

    if (restaurantCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Restaurant not found' },
        { status: 404 }
      );
    }

    // Get menu items
    const menuItemsResult = await query(
      `
      SELECT id, name, price
      FROM menu_items
      WHERE restaurant_id = $1
      ORDER BY name
    `,
      [id]
    );

    const menuItems: (MenuItem & { id: number })[] = menuItemsResult.rows.map((item: any) => ({
      id: item.id,
      name: item.name,
      price: parseFloat(item.price),
    }));

    return NextResponse.json(menuItems, { status: 200 });
  } catch (error) {
    console.error('Error fetching menu items:', error);
    return NextResponse.json(
      { error: 'Failed to fetch menu items' },
      { status: 500 }
    );
  }
}

