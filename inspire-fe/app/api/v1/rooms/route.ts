import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { createRoom } from "@/lib/server/services";

export async function POST(request: Request) {
  try {
    const user = await requireSessionUser();
    const body = await request.json();
    const room = await createRoom(user, body);
    return NextResponse.json(room, { status: 201 });
  } catch (error) {
    return handleRouteError(error);
  }
}

