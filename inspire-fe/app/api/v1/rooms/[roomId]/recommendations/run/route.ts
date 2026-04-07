import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { runRecommendationsManually } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { roomId } = await params;
    const summary = await runRecommendationsManually(user, roomId);
    return NextResponse.json(summary);
  } catch (error) {
    return handleRouteError(error);
  }
}

