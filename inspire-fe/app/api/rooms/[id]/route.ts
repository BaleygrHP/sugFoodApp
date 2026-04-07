import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// GET /api/rooms/[id] - Get room details
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Get room info
    const roomResult = await query(
      `
      SELECT id, title, status, expires_at, closed_at, created_at
      FROM rooms
      WHERE id = $1
    `,
      [id]
    );

    if (roomResult.rows.length === 0) {
      return NextResponse.json(
        { error: 'Room not found' },
        { status: 404 }
      );
    }

    const room = roomResult.rows[0];

    // Get participants count
    const participantsResult = await query(
      'SELECT COUNT(*) as count FROM participants WHERE room_id = $1',
      [id]
    );
    const participantCount = parseInt(participantsResult.rows[0].count);

    // Get first participant (host) - the one who joined first
    const hostResult = await query(
      'SELECT id FROM participants WHERE room_id = $1 ORDER BY joined_at ASC LIMIT 1',
      [id]
    );
    const hostId = hostResult.rows.length > 0 ? hostResult.rows[0].id : null;

    // Get menu items in room with restaurant info
    const menuItemsResult = await query(
      `
      SELECT 
        mi.id as menu_item_id,
        mi.name as menu_item_name,
        mi.price,
        r.id as restaurant_id,
        r.name as restaurant_name,
        r.cuisine,
        r.price_range,
        r.image,
        r.distance,
        r.rating
      FROM room_menu_items rmi
      JOIN menu_items mi ON rmi.menu_item_id = mi.id
      JOIN restaurants r ON mi.restaurant_id = r.id
      WHERE rmi.room_id = $1
      ORDER BY rmi.added_at ASC
    `,
      [id]
    );

    // Get vote counts for each menu item
    const votesResult = await query(
      `
      SELECT menu_item_id, COUNT(*) as vote_count
      FROM votes
      WHERE room_id = $1
      GROUP BY menu_item_id
    `,
      [id]
    );

    const voteCounts: { [key: number]: number } = {};
    votesResult.rows.forEach((row: any) => {
      voteCounts[row.menu_item_id] = parseInt(row.vote_count);
    });

    const menuItems = menuItemsResult.rows.map((row: any) => ({
      menuItemId: row.menu_item_id,
      menuItemName: row.menu_item_name,
      price: parseFloat(row.price),
      restaurant: {
        id: row.restaurant_id,
        name: row.restaurant_name,
        cuisine: row.cuisine,
        priceRange: row.price_range,
        image: row.image || '',
        distance: row.distance,
        rating: parseFloat(row.rating),
      },
      votes: voteCounts[row.menu_item_id] || 0,
    }));

    // Calculate time remaining
    const expiresAt = new Date(room.expires_at);
    const now = new Date();
    const timeRemaining = Math.max(0, Math.floor((expiresAt.getTime() - now.getTime()) / 1000));

    return NextResponse.json({
      id: room.id,
      title: room.title,
      status: room.status,
      expiresAt: room.expires_at,
      timeRemaining,
      participantCount,
      hostId,
      menuItems,
    }, { status: 200 });
  } catch (error) {
    console.error('Error fetching room:', error);
    return NextResponse.json(
      { error: 'Failed to fetch room' },
      { status: 500 }
    );
  }
}

