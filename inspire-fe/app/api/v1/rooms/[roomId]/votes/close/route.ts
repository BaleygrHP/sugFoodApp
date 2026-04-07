import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { closeVoteAndFinalize } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { roomId } = await params;
    const decision = await closeVoteAndFinalize(user, roomId);
    return NextResponse.json(decision);
  } catch (error) {
    return handleRouteError(error);
  }
}

