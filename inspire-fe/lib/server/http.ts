import { NextResponse } from "next/server";

import { AppError } from "@/lib/server/errors";

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
