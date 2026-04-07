import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { getPrefill } from "@/lib/server/services";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ roomId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { roomId } = await params;
    const prefill = await getPrefill(roomId, user.id);
    return NextResponse.json(prefill);
  } catch (error) {
    return handleRouteError(error);
  }
}

