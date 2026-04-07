import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { getLatestRecommendations } from "@/lib/server/services";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { roomId } = await params;
    const summary = await getLatestRecommendations(user, roomId);
    return NextResponse.json(summary);
  } catch (error) {
    return handleRouteError(error);
  }
}

