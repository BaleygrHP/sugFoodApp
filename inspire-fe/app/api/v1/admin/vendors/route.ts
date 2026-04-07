import { NextResponse } from "next/server";

import { requireRole } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { listAdminVendors, saveVendor } from "@/lib/server/services";

export async function GET() {
  try {
    await requireRole(["admin", "ops_admin"]);
    const vendors = await listAdminVendors();
    return NextResponse.json(vendors);
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function POST(request: Request) {
  try {
    await requireRole(["admin", "ops_admin"]);
    const body = await request.json();
    const vendor = await saveVendor(body);
    return NextResponse.json(vendor, { status: 201 });
  } catch (error) {
    return handleRouteError(error);
  }
}

