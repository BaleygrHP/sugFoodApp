import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms/[id]/close - Close room and finalize order (host only)
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { participantId } = body;

    if (!participantId) {
      return NextResponse.json(
        { error: 'Participant ID is required' },
        { status: 400 }
      );
    }

    // Get room
    const roomResult = await query(
      'SELECT id, status FROM rooms WHERE id = $1',
      [id]
    );

    if (roomResult.rows.length === 0) {
      return NextResponse.json(
        { error: 'Room not found' },
        { status: 404 }
      );
    }

    const room = roomResult.rows[0];

    // Check if participant is host (first participant)
    const hostCheck = await query(
      `
      SELECT id FROM participants
      WHERE room_id = $1
      ORDER BY joined_at ASC
      LIMIT 1
    `,
      [id]
    );

    if (hostCheck.rows.length === 0 || hostCheck.rows[0].id !== participantId) {
      return NextResponse.json(
        { error: 'Only the host can close the room' },
        { status: 403 }
      );
    }

    if (room.status !== 'open' && room.status !== 'voting') {
      return NextResponse.json(
        { error: 'Room is already closed' },
        { status: 400 }
      );
    }

    // Close the room
    await query(
      `
      UPDATE rooms
      SET status = 'CLOSED', closed_at = CURRENT_TIMESTAMP
      WHERE id = $1
    `,
      [id]
    );

    // Get winner menu item (most votes)
    const winnerResult = await query(
      `
      SELECT menu_item_id, COUNT(*) as vote_count
      FROM votes
      WHERE room_id = $1
      GROUP BY menu_item_id
      ORDER BY vote_count DESC
      LIMIT 1
    `,
      [id]
    );

    const winner = winnerResult.rows.length > 0
      ? winnerResult.rows[0].menu_item_id
      : null;

    return NextResponse.json({
      success: true,
      winner,
    }, { status: 200 });
  } catch (error) {
    console.error('Error closing room:', error);
    return NextResponse.json(
      { error: 'Failed to close room' },
      { status: 500 }
    );
  }
}

