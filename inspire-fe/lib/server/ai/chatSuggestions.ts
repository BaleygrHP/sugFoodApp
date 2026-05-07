import { query } from "@/lib/db";
import { appConfig } from "@/lib/server/config";
import { normalizeText } from "@/lib/server/utils";

export type ChatSuggestionSource = "ai" | "fallback";

export interface ChatSuggestionRequestPayload {
  message: string;
  keywords?: string[];
}

export interface ChatSuggestionResponsePayload {
  reply: string;
  matchedRestaurantIds: string[];
  source: ChatSuggestionSource;
}

type RestaurantRow = {
  id: string;
  name: string;
  cuisine: string;
  priceRange: string;
  rating: string | number;
  distance: string;
  description: string | null;
  menuItemName: string | null;
};

type ChatSuggestionRestaurant = {
  id: string;
  name: string;
  cuisine: string;
  priceRange: string;
  rating: number;
  distance: string;
  description: string;
  menuItems: string[];
};

type FallbackRule = {
  keywords: string[];
  dishTerms: string[];
  intro: string;
};

const fallbackRules: FallbackRule[] = [
  {
    keywords: ["sad", "down", "upset", "stress", "stressed", "busy", "tired", "rain", "raining", "cold"],
    dishTerms: ["pho", "bun bo", "hu tieu", "chao", "lau"],
    intro: "Here are some warm Vietnamese comfort-food picks that should hit the spot:",
  },
  {
    keywords: ["budget", "cheap", "save", "affordable", "quick", "fast", "hurry"],
    dishTerms: ["com tam", "banh mi", "bun", "com", "hu tieu"],
    intro: "Here are some affordable Vietnamese lunch picks that stay quick and satisfying:",
  },
  {
    keywords: ["date", "romantic", "special", "paid", "celebrate", "party", "group", "friends", "team"],
    dishTerms: ["lau", "nuong", "set mon", "com phan"],
    intro: "Here are some Vietnamese group-friendly picks for sharing and celebrating:",
  },
  {
    keywords: ["healthy", "health", "light", "diet", "fresh"],
    dishTerms: ["goi", "cuon", "pho ga", "chay"],
    intro: "Here are some lighter Vietnamese options that still feel satisfying:",
  },
];

const allDishTerms = Array.from(new Set(fallbackRules.flatMap((rule) => rule.dishTerms)));

function tokenize(value: string) {
  return normalizeText(value)
    .split(/[^a-z0-9]+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

function parseDistanceKm(distance: string) {
  const match = distance.match(/(\d+\.?\d*)/);
  return match ? Number.parseFloat(match[1]) : 99;
}

function buildSearchText(restaurant: ChatSuggestionRestaurant) {
  return normalizeText(
    [
      restaurant.name,
      restaurant.cuisine,
      restaurant.description,
      restaurant.menuItems.join(" "),
    ].join(" "),
  );
}

function sanitizeMatchedRestaurantIds(
  candidateIds: string[],
  restaurants: ChatSuggestionRestaurant[],
  reply: string,
) {
  const availableIds = new Set(restaurants.map((restaurant) => restaurant.id));
  const validIds = candidateIds.filter((id) => availableIds.has(id));
  if (validIds.length > 0) {
    return Array.from(new Set(validIds)).slice(0, 5);
  }

  const normalizedReply = normalizeText(reply);
  return restaurants
    .filter((restaurant) => normalizedReply.includes(normalizeText(restaurant.name)))
    .map((restaurant) => restaurant.id)
    .slice(0, 5);
}

function resolveFallbackRule(message: string, keywords: string[]) {
  const normalizedMessage = normalizeText(message);
  const tokenSet = new Set([...tokenize(message), ...keywords.map((keyword) => normalizeText(keyword))]);
  const explicitRule = fallbackRules.find((rule) =>
    rule.keywords.some(
      (keyword) => tokenSet.has(keyword) || normalizedMessage.includes(keyword),
    ),
  );

  if (explicitRule) {
    return explicitRule;
  }

  const directDishTerms = allDishTerms.filter((dish) => normalizedMessage.includes(dish));
  if (directDishTerms.length > 0) {
    return {
      keywords: [],
      dishTerms: directDishTerms,
      intro: "Here are some Vietnamese-style matches for what you're craving:",
    };
  }

  return {
    keywords: [],
    dishTerms: ["pho", "com tam", "bun bo", "goi cuon", "lau"],
    intro: "Here are a few Vietnamese-first suggestions to get the room started:",
  };
}

function scoreRestaurantForRule(restaurant: ChatSuggestionRestaurant, rule: FallbackRule) {
  const normalizedCuisine = normalizeText(restaurant.cuisine);
  const searchText = buildSearchText(restaurant);
  const normalizedMenuItems = restaurant.menuItems.map((item) => normalizeText(item));
  let score = restaurant.rating / 5;

  if (normalizedCuisine.includes("vietnam")) {
    score += 0.75;
  }

  for (const dish of rule.dishTerms) {
    if (normalizedMenuItems.some((item) => item.includes(dish))) {
      score += 3;
      continue;
    }

    if (searchText.includes(dish)) {
      score += 1.75;
    }
  }

  if (rule.keywords.some((keyword) => ["budget", "cheap", "save", "affordable"].includes(keyword))) {
    if (restaurant.priceRange === "$") score += 1.5;
    if (restaurant.priceRange === "$$") score += 0.5;
  }

  if (rule.keywords.some((keyword) => ["quick", "fast", "hurry", "busy", "tired"].includes(keyword))) {
    score += Math.max(0, 1.5 - parseDistanceKm(restaurant.distance));
  }

  if (rule.keywords.some((keyword) => ["healthy", "health", "light", "diet", "fresh"].includes(keyword))) {
    if (searchText.includes("chay") || searchText.includes("goi") || searchText.includes("cuon")) {
      score += 1.25;
    }
  }

  if (rule.keywords.some((keyword) => ["date", "romantic", "special", "paid", "celebrate", "party", "group", "friends", "team"].includes(keyword))) {
    if (searchText.includes("lau") || searchText.includes("nuong") || searchText.includes("set")) {
      score += 1.25;
    }
  }

  return score;
}

function buildRestaurantReason(restaurant: ChatSuggestionRestaurant, rule: FallbackRule) {
  const matchingDish =
    rule.dishTerms.find((dish) =>
      restaurant.menuItems.some((item) => normalizeText(item).includes(dish)),
    ) || rule.dishTerms[0];

  return `${restaurant.cuisine} | ${restaurant.priceRange} | ${restaurant.distance}. Try ${matchingDish}.`;
}

function buildFallbackResponse(
  message: string,
  keywords: string[],
  restaurants: ChatSuggestionRestaurant[],
): ChatSuggestionResponsePayload {
  const rule = resolveFallbackRule(message, keywords);
  const matches = [...restaurants]
    .sort((a, b) => scoreRestaurantForRule(b, rule) - scoreRestaurantForRule(a, rule))
    .slice(0, 5);

  const reply = [
    rule.intro,
    "",
    ...matches.map(
      (restaurant) => `* **${restaurant.name}**: ${buildRestaurantReason(restaurant, rule)}`,
    ),
  ].join("\n");

  return {
    reply,
    matchedRestaurantIds: matches.map((restaurant) => restaurant.id),
    source: "fallback",
  };
}

async function listRestaurantsForChat(): Promise<ChatSuggestionRestaurant[]> {
  const result = await query<RestaurantRow>(
    `
      SELECT
        r.id,
        r.name,
        r.cuisine,
        r.price_range AS "priceRange",
        r.rating,
        r.distance,
        r.description,
        mi.name AS "menuItemName"
      FROM restaurants r
      LEFT JOIN menu_items mi ON mi.restaurant_id = r.id
      ORDER BY r.rating DESC, r.name ASC, mi.name ASC
    `,
  );

  const restaurants = new Map<string, ChatSuggestionRestaurant>();

  for (const row of result.rows) {
    const existing = restaurants.get(row.id);
    if (existing) {
      if (row.menuItemName) {
        existing.menuItems.push(row.menuItemName);
      }
      continue;
    }

    restaurants.set(row.id, {
      id: row.id,
      name: row.name,
      cuisine: row.cuisine,
      priceRange: row.priceRange,
      rating: typeof row.rating === "number" ? row.rating : Number.parseFloat(row.rating),
      distance: row.distance,
      description: row.description || "",
      menuItems: row.menuItemName ? [row.menuItemName] : [],
    });
  }

  return Array.from(restaurants.values());
}

async function requestAiServiceSuggestions(
  message: string,
  keywords: string[],
  restaurants: ChatSuggestionRestaurant[],
): Promise<ChatSuggestionResponsePayload | null> {
  const baseUrl = appConfig.aiServiceBaseUrl.replace(/\/+$/, "");

  try {
    const response = await fetch(`${baseUrl}/api/v1/food/chat-suggestions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        keywords,
        restaurants: restaurants.slice(0, 30),
      }),
      signal: AbortSignal.timeout(8_000),
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      reply?: string;
      matched_restaurant_ids?: string[];
      matchedRestaurantIds?: string[];
    };

    const reply = typeof data.reply === "string" ? data.reply.trim() : "";
    if (!reply) {
      return null;
    }

    const matchedRestaurantIds = sanitizeMatchedRestaurantIds(
      data.matched_restaurant_ids || data.matchedRestaurantIds || [],
      restaurants,
      reply,
    );

    return {
      reply,
      matchedRestaurantIds,
      source: "ai",
    };
  } catch {
    return null;
  }
}

export async function createChatSuggestions(
  payload: ChatSuggestionRequestPayload,
): Promise<ChatSuggestionResponsePayload> {
  const restaurants = await listRestaurantsForChat();
  const keywords = payload.keywords || [];
  const aiResponse = await requestAiServiceSuggestions(payload.message, keywords, restaurants);

  if (aiResponse) {
    return aiResponse;
  }

  return buildFallbackResponse(payload.message, keywords, restaurants);
}
