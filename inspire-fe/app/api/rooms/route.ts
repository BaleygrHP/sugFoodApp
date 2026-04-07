import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms - Create a new room
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { title, participantId } = body;

    // Create room with 30 minutes expiration
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 30);

    const roomResult = await query(
      `
      INSERT INTO rooms (title, name, expires_at, status)
      VALUES ($1, $1, $2, 'open')
      RETURNING id, title, status, expires_at, created_at
    `,
      [title || null, expiresAt]
    );

    const room = roomResult.rows[0];

    // Add creator as first participant (host)
    if (participantId) {
      await query(
        `
        INSERT INTO participants (id, room_id, name)
        VALUES ($1, $2, 'Host')
        ON CONFLICT (id, room_id) DO NOTHING
      `,
        [participantId, room.id]
      );
    }

    return NextResponse.json({
      id: room.id,
      title: room.title,
      status: room.status,
      expiresAt: room.expires_at,
      createdAt: room.created_at,
    }, { status: 201 });
  } catch (error) {
    console.error('Error creating room:', error);
    return NextResponse.json(
      { error: 'Failed to create room' },
      { status: 500 }
    );
  }
}

