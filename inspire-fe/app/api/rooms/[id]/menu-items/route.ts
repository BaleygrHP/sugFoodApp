import { legacyApiFrozenResponse } from "@/lib/server/http";

export async function POST() {
  return legacyApiFrozenResponse();
}
