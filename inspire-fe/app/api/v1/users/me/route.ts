import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { getMyProfile } from "@/lib/server/services";

export async function GET() {
  try {
    const user = await requireSessionUser();
    const profile = await getMyProfile(user.id);
    return NextResponse.json(profile);
  } catch (error) {
    return handleRouteError(error);
  }
}

