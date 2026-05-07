import { NextResponse } from "next/server";

import { createChatSuggestions } from "@/lib/server/ai/chatSuggestions";
import { handleRouteError } from "@/lib/server/http";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      message?: string;
      keywords?: string[];
    };

    const message = body.message?.trim();
    if (!message) {
      return NextResponse.json(
        {
          error: "Message is required",
        },
        { status: 400 },
      );
    }

    const response = await createChatSuggestions({
      message,
      keywords: Array.isArray(body.keywords) ? body.keywords : [],
    });

    return NextResponse.json(response);
  } catch (error) {
    return handleRouteError(error);
  }
}
