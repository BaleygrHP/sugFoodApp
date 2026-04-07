import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { joinRoom } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const body = await request.json().catch(() => ({}));
    const { roomId } = await params;
    const room = await joinRoom(user, roomId, body.inviteToken);
    return NextResponse.json(room);
  } catch (error) {
    return handleRouteError(error);
  }
}

