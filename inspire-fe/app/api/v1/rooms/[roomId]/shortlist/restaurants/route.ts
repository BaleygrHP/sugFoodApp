import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { addRestaurantToShortlist } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const body = await request.json();
    const { roomId } = await params;
    const room = await addRestaurantToShortlist(user, roomId, body.restaurantId);
    return NextResponse.json(room);
  } catch (error) {
    return handleRouteError(error);
  }
}
