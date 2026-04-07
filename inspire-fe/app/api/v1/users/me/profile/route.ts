import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { updateMyProfile } from "@/lib/server/services";

export async function PUT(request: Request) {
  try {
    const user = await requireSessionUser();
    const body = await request.json();
    const profile = await updateMyProfile(user.id, body);
    return NextResponse.json(profile);
  } catch (error) {
    return handleRouteError(error);
  }
}

