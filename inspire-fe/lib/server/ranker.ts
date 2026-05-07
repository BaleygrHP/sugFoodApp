import { appConfig } from "@/lib/server/config";
import type {
  PrefillSuggestion,
  RankerContext,
  RecommendationCandidate,
  RoomPreferenceSubmission,
  UserProfile,
} from "@/lib/server/types";
import { clamp, normalizeText, splitPreferenceText } from "@/lib/server/utils";

export interface RankerCatalogItem {
  restaurantId: string;
  restaurantName: string;
  cuisine: string;
  serviceMode: string;
  avgPriceMin: number | null;
  avgPriceMax: number | null;
  deliveryRadiusKm: number | null;
  restaurantReliabilityScore: number;
  supportsInvoice: boolean;
  latitude: number | null;
  longitude: number | null;
  dishId: string;
  dishName: string;
  normalizedDishName: string;
  tags: string[];
  currentPrice: number;
  vendorId: string | null;
  approvalStatus: string;
  invoiceSupported: boolean;
  supportsDelivery: boolean;
  supportsDineIn: boolean;
  vendorReliabilityScore: number;
  deliverySlaMins: number | null;
}

export interface RankerHistorySnapshot {
  userRestaurantCounts: Record<string, Record<string, number>>;
  userDishCounts: Record<string, Record<string, number>>;
  roomRestaurantCounts: Record<string, number>;
}

const synonymMap: Record<string, string> = {
  pho: "pho",
  "pho bo": "pho",
  "bun bo": "bun bo",
  "com tam": "com tam",
  "lau": "lau",
  "bun dau": "bun dau",
  "hu tieu": "hu tieu",
};

function normalizeTokens(input: string) {
  return splitPreferenceText(input).map((token) => synonymMap[normalizeText(token)] || normalizeText(token));
}

function derivePriceBand(price: number | null) {
  if (!price) return "unknown";
  if (price < 50) return "low";
  if (price < 90) return "mid";
  return "high";
}

function distanceKm(lat1: number, lng1: number, lat2: number, lng2: number) {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const earthRadiusKm = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return earthRadiusKm * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

function budgetFit(price: number | null, minBudget: number | null, maxBudget: number | null) {
  if (!price) {
    return 0.5;
  }
  if (maxBudget !== null && price > maxBudget) {
    return 0;
  }
  if (minBudget !== null && price < minBudget) {
    return clamp(1 - (minBudget - price) / Math.max(minBudget, 1), 0, 1);
  }
  return 1;
}

function normalizePreference(preference: RoomPreferenceSubmission | null, profile: UserProfile) {
  const freeTextTokens = normalizeTokens(preference?.freeTextInput || "");
  const selectedTokens = (preference?.selectedSuggestions || []).map((item) => normalizeText(item));
  const rankedTokens = (preference?.rankedChoices || []).map((item) => normalizeText(item));
  const cuisineTokens = profile.cuisinePreferences.map((item) => normalizeText(item));
  const dishTokens = profile.dishStylePreferences.map((item) => normalizeText(item));
  const favoriteRestaurantIds = new Set(profile.favoriteRestaurantIds);
  const favoriteDishIds = new Set(profile.favoriteDishIds);

  return {
    explicitTokens: new Set([...freeTextTokens, ...selectedTokens, ...rankedTokens, ...cuisineTokens, ...dishTokens]),
    favoriteRestaurantIds,
    favoriteDishIds,
    vegetarianOnly: Boolean(preference?.hardConstraints?.vegetarian),
    budgetCap: preference?.hardConstraints?.budgetCap ?? profile.preferredBudgetMax,
    blockedRestaurantIds: new Set([
      ...profile.blockedRestaurantIds,
      ...(preference?.hardConstraints?.blockedRestaurantIds || []),
    ]),
    requireInvoice: Boolean(preference?.hardConstraints?.requireInvoice),
  };
}

export function buildNormalizedPayload(preference: RoomPreferenceSubmission, catalog: RankerCatalogItem[]) {
  const tokens = normalizeTokens(preference.freeTextInput);
  const restaurantMatches = catalog
    .filter((item) => tokens.some((token) => normalizeText(item.restaurantName).includes(token)))
    .slice(0, 5)
    .map((item) => item.restaurantId);
  const dishMatches = catalog
    .filter((item) => tokens.some((token) => item.normalizedDishName.includes(token)))
    .slice(0, 5)
    .map((item) => item.dishId);
  const cuisineMatches = catalog
    .filter((item) => tokens.some((token) => normalizeText(item.cuisine).includes(token)))
    .slice(0, 5)
    .map((item) => item.cuisine);

  return {
    tokens,
    restaurantMatches,
    dishMatches,
    cuisineMatches,
  };
}

export function buildPrefillSuggestions(profile: UserProfile, catalog: RankerCatalogItem[], userHistory?: Record<string, number>) {
  const cuisinePreferenceSet = new Set(profile.cuisinePreferences.map((item) => normalizeText(item)));
  const suggestions = new Map<string, PrefillSuggestion>();

  for (const item of catalog) {
    if (suggestions.size >= 3) {
      break;
    }

    const normalizedCuisine = normalizeText(item.cuisine);
    const normalizedDish = normalizeText(item.dishName);
    const historyScore = userHistory?.[item.restaurantId] || 0;

    if (cuisinePreferenceSet.has(normalizedCuisine)) {
      suggestions.set(`cuisine:${normalizedCuisine}`, {
        id: `cuisine:${normalizedCuisine}`,
        type: "cuisine",
        label: item.cuisine,
        reason: "Matches your saved cuisine preferences",
      });
      continue;
    }

    if (historyScore > 0) {
      suggestions.set(`restaurant:${item.restaurantId}`, {
        id: item.restaurantId,
        type: "restaurant",
        label: item.restaurantName,
        reason: "You picked this restaurant recently",
      });
      continue;
    }

    if (profile.dishStylePreferences.some((dish) => normalizeText(dish) === normalizedDish)) {
      suggestions.set(`dish:${item.dishId}`, {
        id: item.dishId,
        type: "dish",
        label: item.dishName,
        reason: "Matches your saved dish preferences",
      });
    }
  }

  return Array.from(suggestions.values()).slice(0, 3);
}

function similarity(a: RecommendationCandidate, b: RecommendationCandidate) {
  let score = 0;
  if (a.restaurantId && a.restaurantId === b.restaurantId) score += 0.45;
  if (a.cuisine && a.cuisine === b.cuisine) score += 0.3;
  if (derivePriceBand(a.price) === derivePriceBand(b.price)) score += 0.15;
  if (a.dishName && b.dishName && normalizeText(a.dishName) === normalizeText(b.dishName)) score += 0.1;
  return clamp(score, 0, 1);
}

export function runRecommendationRanker(
  context: RankerContext,
  catalog: RankerCatalogItem[],
  history: RankerHistorySnapshot,
) {
  const perUserScores: Array<{
    candidateId: string;
    userId: string;
    scores: Record<string, number>;
  }> = [];

  const scoredCandidates = catalog
    .filter((item) => item.approvalStatus !== "suspended")
    .filter((item) => {
      if (context.room.mode === "delivery" && !item.supportsDelivery) return false;
      if (context.room.mode === "dine_in" && !item.supportsDineIn) return false;
      if (context.room.budgetMax !== null && item.currentPrice > context.room.budgetMax) return false;
      if (context.room.targetLat !== null && context.room.targetLng !== null && item.latitude !== null && item.longitude !== null) {
        const km = distanceKm(context.room.targetLat, context.room.targetLng, item.latitude, item.longitude);
        if (context.room.mode === "delivery" && item.deliveryRadiusKm !== null && km > item.deliveryRadiusKm) return false;
      }
      return true;
    })
    .slice(0, appConfig.ranking.maxCandidates);

  const candidateScores = scoredCandidates.map((item) => {
    const candidateKey = `${item.restaurantId}:${item.dishId}`;
    const memberScores = context.members.map((member) => {
      const normalized = normalizePreference(member.preference, member.profile);
      const preferenceHit =
        normalized.explicitTokens.has(item.normalizedDishName) ||
        normalized.explicitTokens.has(normalizeText(item.cuisine)) ||
        normalized.explicitTokens.has(normalizeText(item.restaurantName));
      const favoriteHit =
        normalized.favoriteRestaurantIds.has(item.restaurantId) ||
        normalized.favoriteDishIds.has(item.dishId);
      const budgetScore = budgetFit(
        item.currentPrice,
        member.profile.preferredBudgetMin ?? context.room.budgetMin,
        normalized.budgetCap ?? context.room.budgetMax,
      );
      const historyCount = history.userRestaurantCounts[member.user.id]?.[item.restaurantId] || 0;
      const dishCount = history.userDishCounts[member.user.id]?.[item.dishId] || 0;
      const roomHistoryCount = history.roomRestaurantCounts[item.restaurantId] || 0;
      const vegetarianConflict =
        normalized.vegetarianOnly &&
        !item.tags.map((tag) => normalizeText(tag)).includes("vegetarian") &&
        !normalizeText(item.cuisine).includes("vegetarian");
      const blocked = normalized.blockedRestaurantIds.has(item.restaurantId);
      const invoiceConflict = normalized.requireInvoice && !item.invoiceSupported;
      const reliabilityScore = clamp(item.vendorReliabilityScore);
      const noveltyBase = member.profile.noveltyPreference === "explore" ? 0.9 : member.profile.noveltyPreference === "balanced" ? 0.6 : 0.35;
      const noveltyScore = clamp(historyCount === 0 ? noveltyBase : noveltyBase * 0.4);
      const cooldownPenalty = clamp(roomHistoryCount > 0 ? 0.5 : historyCount > 1 ? 0.35 : 0);
      const frictionPenalty = clamp(
        (context.room.mode === "delivery" ? (item.deliverySlaMins || 30) / 90 : 0.2) +
          ((item.supportsDelivery || item.supportsDineIn) ? 0 : 1),
        0,
        1,
      );
      const preferenceScore = preferenceHit || favoriteHit ? 1 : clamp((dishCount > 0 ? 0.65 : 0.25) + (normalized.explicitTokens.size === 0 ? 0.15 : 0), 0, 1);
      const frequencyScore = clamp(historyCount > 0 ? Math.min(historyCount / 3, 1) : 0.2);
      const familiarityScore = clamp((historyCount > 0 ? 0.7 : 0.2) + (dishCount > 0 ? 0.2 : 0), 0, 1);
      const contextScore = clamp(
        (context.room.mode === "delivery" ? Number(item.supportsDelivery) : 0.8) +
          (context.room.mealType === "lunch" ? 0.1 : 0),
        0,
        1,
      );
      const socialAffinityScore = clamp(
        context.members.filter((other) => {
          const otherTokens = normalizePreference(other.preference, other.profile).explicitTokens;
          return otherTokens.has(item.normalizedDishName) || otherTokens.has(normalizeText(item.cuisine));
        }).length / Math.max(context.members.length, 1),
        0,
        1,
      );

      const finalPersonalScore = blocked || vegetarianConflict || invoiceConflict
        ? 0
        : clamp(
            0.22 * preferenceScore +
              0.12 * frequencyScore +
              0.1 * familiarityScore +
              0.14 * contextScore +
              0.12 * budgetScore +
              0.1 * reliabilityScore +
              0.08 * socialAffinityScore +
              0.07 * noveltyScore -
              0.15 * cooldownPenalty -
              0.1 * frictionPenalty,
            0,
            1,
          );

      const weight =
        member.preference?.prefillAccepted ? 0.65 :
        member.participationStatus === "submitted" ? 1 :
        member.preference ? 0.65 : 0.3;

      const scoreRecord = {
        preferenceScore,
        frequencyScore,
        familiarityScore,
        contextScore,
        budgetScore,
        reliabilityScore,
        socialAffinityScore,
        noveltyScore,
        cooldownPenalty,
        frictionPenalty,
        finalPersonalScore,
        weight,
        veto: blocked || vegetarianConflict || invoiceConflict ? 1 : 0,
      };

      perUserScores.push({
        candidateId: candidateKey,
        userId: member.user.id,
        scores: scoreRecord,
      });

      return scoreRecord;
    });

    const weightedSum = memberScores.reduce((sum, entry) => sum + entry.finalPersonalScore * entry.weight, 0);
    const totalWeight = memberScores.reduce((sum, entry) => sum + entry.weight, 0) || 1;
    const weightedMean = weightedSum / totalWeight;
    const sortedPersonalScores = [...memberScores].map((entry) => entry.finalPersonalScore).sort((a, b) => a - b);
    const median = sortedPersonalScores[Math.floor(sortedPersonalScores.length / 2)] || 0;
    const mean = sortedPersonalScores.reduce((sum, value) => sum + value, 0) / Math.max(sortedPersonalScores.length, 1);
    const disagreementPenalty = clamp(
      Math.sqrt(sortedPersonalScores.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(sortedPersonalScores.length, 1)),
      0,
      1,
    );
    const vetoPenalty = clamp(memberScores.reduce((sum, entry) => sum + entry.veto, 0) / Math.max(memberScores.length, 1), 0, 1);
    const hasHardVeto = memberScores.some((entry) => entry.veto === 1);
    const groupScore = hasHardVeto
      ? 0
      : clamp(0.55 * weightedMean + 0.2 * median - 0.15 * disagreementPenalty - 0.1 * vetoPenalty, 0, 1);
    const feasibilityMultiplier = clamp(
      0.35 +
        0.25 * item.vendorReliabilityScore +
        0.2 * Number(context.room.mode !== "delivery" || item.supportsDelivery) +
        0.2 * Number(context.room.mode !== "dine_in" || item.supportsDineIn),
      0,
      1.2,
    );
    const shortlistBoost = hasHardVeto
      ? 0
      : context.shortlist.dishIds.includes(item.dishId)
        ? 0.1
        : context.shortlist.restaurantIds.includes(item.restaurantId)
          ? 0.06
          : 0;
    const finalScore = clamp(groupScore * feasibilityMultiplier + shortlistBoost, 0, 1);
    const participationRate = clamp(context.room.submissionCount / Math.max(context.room.participantCount, 1), 0, 1);
    const consensusStrength = clamp(1 - disagreementPenalty, 0, 1);
    const dataQuality = clamp(context.members.filter((member) => member.preference).length / Math.max(context.members.length, 1), 0, 1);
    const operationalCertainty = clamp(feasibilityMultiplier / 1.2, 0, 1);
    const confidence = clamp(
      0.4 * participationRate +
        0.3 * consensusStrength +
        0.2 * dataQuality +
        0.1 * operationalCertainty,
      0,
      1,
    );

    const reasons = [
      groupScore > 0.6 ? "Strong match across the group" : "Reasonable balance across group preferences",
      budgetFit(item.currentPrice, context.room.budgetMin, context.room.budgetMax) > 0.8 ? "Fits the room budget range" : "Budget fit is acceptable",
      item.vendorReliabilityScore > 0.75 ? "Vendor reliability is high" : "Operational reliability is acceptable",
    ];

    if ((history.roomRestaurantCounts[item.restaurantId] || 0) === 0) {
      reasons.push("This helps avoid repeating the latest room choices");
    }

    if (shortlistBoost > 0) {
      reasons.push("Shortlisted by the room before ranking");
    }

    if (hasHardVeto) {
      reasons.push("Rejected by at least one hard room constraint");
    }

    return {
      item,
      weightedMean,
      groupScore,
      feasibilityMultiplier,
      shortlistBoost,
      finalScore,
      confidence,
      disagreementPenalty,
      candidate: {
        candidateId: candidateKey,
        candidateType: "combined_option" as const,
        candidateRefId: item.dishId,
        title: `${item.dishName} at ${item.restaurantName}`,
        restaurantId: item.restaurantId,
        restaurantName: item.restaurantName,
        dishId: item.dishId,
        dishName: item.dishName,
        cuisine: item.cuisine,
        mode: context.room.mode,
        price: item.currentPrice,
        finalScore,
        confidence,
        selectedForVote: false,
        reasons,
        breakdown: {
          baseScore: groupScore,
          feasibilityMultiplier,
          disagreementPenalty,
          shortlistBoost,
          weightedMean,
        },
      } satisfies RecommendationCandidate,
    };
  });

  const reranked: RecommendationCandidate[] = [];
  const remaining = [...candidateScores].sort((a, b) => b.finalScore - a.finalScore);

  while (remaining.length > 0 && reranked.length < 5) {
    let bestIndex = 0;
    let bestScore = -1;

    for (let index = 0; index < remaining.length; index += 1) {
      const candidate = remaining[index].candidate;
      const similarityPenalty = reranked.length === 0
        ? 0
        : Math.max(...reranked.map((selected) => similarity(candidate, selected)));
      const mmrScore = appConfig.ranking.mmrBeta * candidate.finalScore - (1 - appConfig.ranking.mmrBeta) * similarityPenalty;
      if (mmrScore > bestScore) {
        bestScore = mmrScore;
        bestIndex = index;
      }
    }

    reranked.push(remaining.splice(bestIndex, 1)[0].candidate);
  }

  const topOptions = reranked.map((candidate, index) => ({
    ...candidate,
    selectedForVote: index < appConfig.ranking.topVoteOptions,
  }));

  const splitRecommended =
    appConfig.featureFlags.splitGroupEnabled &&
    context.room.participantCount >= 8 &&
    topOptions[0] &&
    topOptions[0].confidence < 0.55;

  if (splitRecommended && topOptions[0]) {
    topOptions[0].reasons = [...topOptions[0].reasons, "Consensus is weak, so split-group may be better for this room"];
  }

  return {
    topOptions,
    perUserScores,
    splitRecommended,
  };
}
