import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { submitRoomVote } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const body = await request.json();
    const { roomId } = await params;
    const summary = await submitRoomVote(user, roomId, body.candidateId, body.voteValue ?? 1);
    return NextResponse.json(summary);
  } catch (error) {
    return handleRouteError(error);
  }
}

