import { legacyApiFrozenResponse } from "@/lib/server/http";

export async function GET() {
  return legacyApiFrozenResponse();
}
