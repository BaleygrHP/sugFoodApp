import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { getRoomForViewer } from "@/lib/server/services";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { roomId } = await params;
    const { searchParams } = new URL(request.url);
    const room = await getRoomForViewer(user, roomId, searchParams.get("token"));
    return NextResponse.json(room);
  } catch (error) {
    return handleRouteError(error);
  }
}

