import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms/[id]/menu-items - Add a specific menu item to room
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { menuItemId } = body;

    if (!menuItemId) {
      return NextResponse.json(
        { error: 'Menu Item ID is required' },
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

    // Check if menu item exists
    const menuItemCheck = await query(
      'SELECT id FROM menu_items WHERE id = $1',
      [menuItemId]
    );

    if (menuItemCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Menu item not found' },
        { status: 404 }
      );
    }
    
    // Add menu item to room_menu_items
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
    console.error('Error adding menu item to room:', error);
    return NextResponse.json(
      { error: 'Failed to add menu item to room' },
      { status: 500 }
    );
  }
}

