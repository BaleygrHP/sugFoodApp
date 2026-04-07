import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// POST /api/rooms/[id]/votes - Vote for a menu item
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { menuItemId, participantId } = body;

    if (!menuItemId || !participantId) {
      return NextResponse.json(
        { error: 'Menu Item ID and Participant ID are required' },
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
        { error: 'Room is not open for voting' },
        { status: 400 }
      );
    }

    // Check if menu item is in room
    const menuItemCheck = await query(
      'SELECT menu_item_id FROM room_menu_items WHERE room_id = $1 AND menu_item_id = $2',
      [id, menuItemId]
    );

    if (menuItemCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Menu item is not in this room' },
        { status: 400 }
      );
    }

    // Check if participant is in room
    const participantCheck = await query(
      'SELECT id FROM participants WHERE room_id = $1 AND id = $2',
      [id, participantId]
    );

    if (participantCheck.rows.length === 0) {
      return NextResponse.json(
        { error: 'Participant is not in this room' },
        { status: 400 }
      );
    }

    // Check if vote already exists (toggle vote)
    const existingVote = await query(
      `
      SELECT id FROM votes
      WHERE room_id = $1 AND menu_item_id = $2 AND participant_id = $3
    `,
      [id, menuItemId, participantId]
    );

    if (existingVote.rows.length > 0) {
      // Unvote (remove vote)
      await query(
        `
        DELETE FROM votes
        WHERE room_id = $1 AND menu_item_id = $2 AND participant_id = $3
      `,
        [id, menuItemId, participantId]
      );
    } else {
      // Vote (add vote)
      await query(
        `
        INSERT INTO votes (room_id, menu_item_id, participant_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (room_id, participant_id, menu_item_id) DO NOTHING
      `,
        [id, menuItemId, participantId]
      );
    }

    // Get updated vote counts
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

    return NextResponse.json({ voteCounts }, { status: 200 });
  } catch (error) {
    console.error('Error voting:', error);
    return NextResponse.json(
      { error: 'Failed to vote' },
      { status: 500 }
    );
  }
}

// GET /api/rooms/[id]/votes - Get votes for a room
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const votesResult = await query(
      `
      SELECT menu_item_id, participant_id
      FROM votes
      WHERE room_id = $1
    `,
      [id]
    );

    const voteCounts: { [key: number]: number } = {};
    const participantVotes: { [key: string]: number[] } = {};

    votesResult.rows.forEach((row: any) => {
      const menuItemId = row.menu_item_id;
      voteCounts[menuItemId] = (voteCounts[menuItemId] || 0) + 1;
      
      // Add to participant's votes array
      if (!participantVotes[row.participant_id]) {
        participantVotes[row.participant_id] = [];
      }
      participantVotes[row.participant_id].push(menuItemId);
    });

    return NextResponse.json({ voteCounts, participantVotes }, { status: 200 });
  } catch (error) {
    console.error('Error fetching votes:', error);
    return NextResponse.json(
      { error: 'Failed to fetch votes' },
      { status: 500 }
    );
  }
}

