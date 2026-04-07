import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms/[id]/participants - Add participant to room
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { participantId, name } = body;

    if (!participantId) {
      return NextResponse.json(
        { error: 'Participant ID is required' },
        { status: 400 }
      );
    }

    // Check if room exists
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

    if (roomCheck.rows[0].status !== 'open' && roomCheck.rows[0].status !== 'voting' && roomCheck.rows[0].status !== 'ranking') {
      return NextResponse.json(
        { error: 'Room is not open' },
        { status: 400 }
      );
    }

    // Add participant
    await query(
      `
      INSERT INTO participants (id, room_id, name)
      VALUES ($1, $2, $3)
      ON CONFLICT (id, room_id) DO UPDATE SET
        name = EXCLUDED.name
    `,
      [participantId, id, name || 'Participant']
    );

    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error('Error adding participant:', error);
    return NextResponse.json(
      { error: 'Failed to add participant' },
      { status: 500 }
    );
  }
}

