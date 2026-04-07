import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms/[id]/restaurants - Add restaurant to room
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { restaurantId } = body;

    if (!restaurantId) {
      return NextResponse.json(
        { error: 'Restaurant ID is required' },
        { status: 400 }
      );
    }

    // Check if room exists and is open
    const roomCheck = await query(
      'SELECT id, status FROM rooms WHERE id = $1',
      [id]
    );

    if (roomCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Room not found' },
        { status: 404 }
      );
    }

    if (roomCheck.rows[0].status !== 'open' && roomCheck.rows[0].status !== 'voting') {
      return NextResponse.json(
        { error: 'Room is not open' },
        { status: 400 }
      );
    }

    // Check if restaurant exists
    const restaurantCheck = await query(
      'SELECT id FROM restaurants WHERE id = $1',
      [restaurantId]
    );

    if (restaurantCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Restaurant not found' },
        { status: 404 }
      );
    }

    // Get menu item "Anything" for this restaurant
    const menuItemResult = await query(
      `
      SELECT id FROM menu_items
      WHERE restaurant_id = $1 AND name = 'Anything'
      LIMIT 1
    `,
      [restaurantId]
    );

    if (menuItemResult.rows.length === 0) {
      return NextResponse.json(
        { error: 'Menu item "Anything" not found for this restaurant' },
        { status: 404 }
      );
    }

    const menuItemId = menuItemResult.rows[0].id;
    
    // Add menu item "Anything" to room
    await query(
      `
      INSERT INTO room_menu_items (room_id, menu_item_id)
      VALUES ($1, $2)
      ON CONFLICT (room_id, menu_item_id) DO NOTHING
    `,
      [id, menuItemId]
    );

    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error('Error adding restaurant to room:', error);
    return NextResponse.json(
      { error: 'Failed to add restaurant to room' },
      { status: 500 }
    );
  }
}

