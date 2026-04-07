import { NextResponse } from "next/server";

import { requireRole } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { getAdminLunchSummary } from "@/lib/server/services";

export async function GET() {
  try {
    await requireRole(["admin", "ops_admin"]);
    const summary = await getAdminLunchSummary();
    return NextResponse.json(summary);
  } catch (error) {
    return handleRouteError(error);
  }
}

