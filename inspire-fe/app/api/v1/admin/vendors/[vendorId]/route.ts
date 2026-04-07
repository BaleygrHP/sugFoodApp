import { NextResponse } from "next/server";

import { requireRole } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { saveVendor } from "@/lib/server/services";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ vendorId: string }> },
) {
  try {
    await requireRole(["admin", "ops_admin"]);
    const body = await request.json();
    const { vendorId } = await params;
    const vendor = await saveVendor({
      ...body,
      id: vendorId,
      restaurantId: body.restaurantId,
    });
    return NextResponse.json(vendor);
  } catch (error) {
    return handleRouteError(error);
  }
}

