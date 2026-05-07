import { NextResponse } from "next/server";

import { AppError } from "@/lib/server/errors";

export function legacyApiFrozenResponse(upgradePath = "/api/v1/rooms") {
  return NextResponse.json(
    {
      code: "legacy_api_frozen",
      error: "This legacy room API has been frozen. Please migrate to the /api/v1 room flow.",
      upgradePath,
    },
    { status: 410 },
  );
}

export function handleRouteError(error: unknown) {
  if (error instanceof AppError) {
    return NextResponse.json(
      {
        error: error.message,
        code: error.code,
        details: error.details ?? null,
      },
      { status: error.status },
    );
  }

  console.error(error);
  return NextResponse.json(
    {
      error: "Internal server error",
      code: "internal_error",
    },
    { status: 500 },
  );
}
