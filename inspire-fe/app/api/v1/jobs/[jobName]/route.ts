import { NextResponse } from "next/server";

import { appConfig } from "@/lib/server/config";
import { AppError } from "@/lib/server/errors";
import { handleRouteError } from "@/lib/server/http";
import { runProtectedJob } from "@/lib/server/services";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ jobName: string }> },
) {
  try {
    const secret = request.headers.get("x-job-secret");
    if (secret !== appConfig.jobSecret) {
      throw new AppError("Forbidden", 403, "forbidden");
    }

    const { jobName } = await params;
    const result = await runProtectedJob(jobName);
    return NextResponse.json(result);
  } catch (error) {
    return handleRouteError(error);
  }
}
