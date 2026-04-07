import { NextResponse } from "next/server";

import { buildGuestSessionResponse, getSessionUser, setSessionCookie } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { createGuestSession } from "@/lib/server/services";

export async function POST(request: Request) {
  try {
    const existingUser = await getSessionUser();
    if (existingUser) {
      return NextResponse.json(buildGuestSessionResponse(existingUser));
    }

    const body = await request.json().catch(() => ({}));
    const user = await createGuestSession(body.displayName);
    await setSessionCookie(user);
    return NextResponse.json(buildGuestSessionResponse(user), { status: 201 });
  } catch (error) {
    return handleRouteError(error);
  }
}

