import { NextResponse } from "next/server";

import { requireSessionUser } from "@/lib/server/auth";
import { handleRouteError } from "@/lib/server/http";
import { blockRestaurantForUser } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ restaurantId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { restaurantId } = await params;
    const profile = await blockRestaurantForUser(user.id, restaurantId, true);
    return NextResponse.json(profile);
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ restaurantId: string }> },
) {
  try {
    const user = await requireSessionUser();
    const { restaurantId } = await params;
    const profile = await blockRestaurantForUser(user.id, restaurantId, false);
    return NextResponse.json(profile);
  } catch (error) {
    return handleRouteError(error);
  }
}

