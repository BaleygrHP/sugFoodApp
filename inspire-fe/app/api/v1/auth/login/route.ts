import { NextResponse } from "next/server";

import { getSessionUser, setSessionCookie } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { loginWithEmail } from "@/lib/server/services";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const currentUser = await getSessionUser();
    const user = await loginWithEmail(currentUser, {
      email: body.email,
      displayName: body.displayName,
    });
    await setSessionCookie(user);
    return NextResponse.json({ user });
  } catch (error) {
    return handleRouteError(error);
  }
}

