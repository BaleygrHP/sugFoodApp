import { randomUUID } from "crypto";

import { query, withTransaction } from "@/lib/db";
import type {
  FinalDecision,
  LunchReportSummary,
  RecommendationCandidate,
  RecommendationRunSummary,
  RoomDetail,
  RoomMember,
  RoomPreferenceSubmission,
  SessionUser,
  UserProfile,
  Vendor,
  VoteSummary,
} from "@/lib/server/types";
import { jsonParse, numberOrNull, safeDate } from "@/lib/server/utils";

type UserRow = {
  id: string;
  email: string | null;
  display_name: string;
  account_status: string;
  role: SessionUser["role"];
};

type UserProfileRow = {
  user_id: string;
  preferred_budget_min: string | null;
  preferred_budget_max: string | null;
  novelty_preference: UserProfile["noveltyPreference"];
  dining_mode_preference: UserProfile["diningModePreference"];
  work_lat: string | null;
  work_lng: string | null;
  restrictions_json: unknown;
  blocked_restaurant_ids_json: unknown;
  favorite_restaurant_ids_json: unknown;
  favorite_dish_ids_json: unknown;
  cuisine_preferences_json: unknown;
  dish_style_preferences_json: unknown;
  preference_version: number;
  updated_at: Date | string;
};

function mapUser(row: UserRow): SessionUser {
  return {
    id: row.id,
    email: row.email,
    displayName: row.display_name,
    accountStatus: row.account_status,
    role: row.role,
  };
}

function mapProfile(row: UserProfileRow): UserProfile {
  return {
    userId: row.user_id,
    preferredBudgetMin: numberOrNull(row.preferred_budget_min),
    preferredBudgetMax: numberOrNull(row.preferred_budget_max),
    noveltyPreference: row.novelty_preference,
    diningModePreference: row.dining_mode_preference,
    workLat: numberOrNull(row.work_lat),
    workLng: numberOrNull(row.work_lng),
    restrictions: jsonParse<string[]>(row.restrictions_json, []),
    blockedRestaurantIds: jsonParse<string[]>(row.blocked_restaurant_ids_json, []),
    favoriteRestaurantIds: jsonParse<string[]>(row.favorite_restaurant_ids_json, []),
    favoriteDishIds: jsonParse<string[]>(row.favorite_dish_ids_json, []),
    cuisinePreferences: jsonParse<string[]>(row.cuisine_preferences_json, []),
    dishStylePreferences: jsonParse<string[]>(row.dish_style_preferences_json, []),
    preferenceVersion: row.preference_version,
    updatedAt: safeDate(row.updated_at),
  };
}

export async function createGuestUser(displayName: string) {
  const result = await query<UserRow>(
    `
      INSERT INTO users (display_name, account_status, role)
      VALUES ($1, 'guest', 'guest')
      RETURNING id, email, display_name, account_status, role
    `,
    [displayName],
  );

  const user = mapUser(result.rows[0]);
  await ensureUserProfile(user.id);
  return user;
}

export async function updateUserAccount(
  userId: string,
  payload: Partial<{
    displayName: string;
    email: string | null;
    role: SessionUser["role"];
    accountStatus: string;
  }>,
) {
  const current = await query<UserRow>(
    `
      SELECT id, email, display_name, account_status, role
      FROM users
      WHERE id = $1
    `,
    [userId],
  );

  const row = current.rows[0];
  const result = await query<UserRow>(
    `
      UPDATE users
      SET
        display_name = $2,
        email = $3,
        role = $4,
        account_status = $5,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
      RETURNING id, email, display_name, account_status, role
    `,
    [
      userId,
      payload.displayName ?? row.display_name,
      payload.email === undefined ? row.email : payload.email,
      payload.role ?? row.role,
      payload.accountStatus ?? row.account_status,
    ],
  );

  return mapUser(result.rows[0]);
}

export async function getUserById(userId: string) {
  const result = await query<UserRow>(
    `
      SELECT id, email, display_name, account_status, role
      FROM users
      WHERE id = $1
    `,
    [userId],
  );

  return result.rows[0] ? mapUser(result.rows[0]) : null;
}

export async function ensureUserProfile(userId: string) {
  await query(
    `
      INSERT INTO user_profiles (user_id)
      VALUES ($1)
      ON CONFLICT (user_id) DO NOTHING
    `,
    [userId],
  );

  return getUserProfile(userId);
}

export async function getUserProfile(userId: string) {
  const result = await query<UserProfileRow>(
    `
      SELECT *
      FROM user_profiles
      WHERE user_id = $1
    `,
    [userId],
  );

  return result.rows[0] ? mapProfile(result.rows[0]) : null;
}

export async function updateUserProfile(userId: string, payload: Partial<UserProfile>) {
  const current = (await ensureUserProfile(userId))!;
  const result = await query<UserProfileRow>(
    `
      UPDATE user_profiles
      SET
        preferred_budget_min = $2,
        preferred_budget_max = $3,
        novelty_preference = $4,
        dining_mode_preference = $5,
        work_lat = $6,
        work_lng = $7,
        restrictions_json = $8::jsonb,
        blocked_restaurant_ids_json = $9::jsonb,
        favorite_restaurant_ids_json = $10::jsonb,
        favorite_dish_ids_json = $11::jsonb,
        cuisine_preferences_json = $12::jsonb,
        dish_style_preferences_json = $13::jsonb,
        preference_version = $14,
        updated_at = CURRENT_TIMESTAMP
      WHERE user_id = $1
      RETURNING *
    `,
    [
      userId,
      payload.preferredBudgetMin ?? current.preferredBudgetMin,
      payload.preferredBudgetMax ?? current.preferredBudgetMax,
      payload.noveltyPreference ?? current.noveltyPreference,
      payload.diningModePreference ?? current.diningModePreference,
      payload.workLat ?? current.workLat,
      payload.workLng ?? current.workLng,
      JSON.stringify(payload.restrictions ?? current.restrictions),
      JSON.stringify(payload.blockedRestaurantIds ?? current.blockedRestaurantIds),
      JSON.stringify(payload.favoriteRestaurantIds ?? current.favoriteRestaurantIds),
      JSON.stringify(payload.favoriteDishIds ?? current.favoriteDishIds),
      JSON.stringify(payload.cuisinePreferences ?? current.cuisinePreferences),
      JSON.stringify(payload.dishStylePreferences ?? current.dishStylePreferences),
      payload.preferenceVersion ?? current.preferenceVersion,
    ],
  );

  return mapProfile(result.rows[0]);
}

export async function setBlockedRestaurant(userId: string, restaurantId: string, blocked: boolean) {
  const profile = (await ensureUserProfile(userId))!;
  const blockedIds = new Set(profile.blockedRestaurantIds);
  if (blocked) {
    blockedIds.add(restaurantId);
  } else {
    blockedIds.delete(restaurantId);
  }

  return updateUserProfile(userId, {
    blockedRestaurantIds: Array.from(blockedIds),
  });
}

export async function createRoomRecord(payload: {
  hostUserId: string;
  name: string;
  mealType: RoomDetail["mealType"];
  mode: RoomDetail["mode"];
  locationLabel: string | null;
  targetLat: number | null;
  targetLng: number | null;
  groupSizeExpected: number;
  budgetMin: number | null;
  budgetMax: number | null;
  expiresAt: Date;
}) {
  return withTransaction(async (client) => {
    const roomResult = await query<{ id: string }>(
      `
        INSERT INTO rooms (
          title,
          name,
          host_user_id,
          meal_type,
          mode,
          location_label,
          target_lat,
          target_lng,
          group_size_expected,
          budget_min,
          budget_max,
          status,
          expires_at,
          updated_at
        )
        VALUES ($1, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'open', $11, CURRENT_TIMESTAMP)
        RETURNING id
      `,
      [
        payload.name,
        payload.hostUserId,
        payload.mealType,
        payload.mode,
        payload.locationLabel,
        payload.targetLat,
        payload.targetLng,
        payload.groupSizeExpected,
        payload.budgetMin,
        payload.budgetMax,
        payload.expiresAt,
      ],
      client,
    );

    const roomId = roomResult.rows[0].id;

    await query(
      `
        INSERT INTO room_members (room_id, user_id, role, participation_status)
        VALUES ($1, $2, 'host', 'joined')
        ON CONFLICT (room_id, user_id) DO UPDATE SET role = 'host'
      `,
      [roomId, payload.hostUserId],
      client,
    );

    await query(
      `
        INSERT INTO participants (id, room_id, name)
        VALUES ($1, $2, 'Host')
        ON CONFLICT (id, room_id) DO NOTHING
      `,
      [payload.hostUserId, roomId],
      client,
    );

    return roomId;
  });
}

export async function getOrCreateRoomInvite(roomId: string, expiresAt: string) {
  const existing = await query<{ invite_token: string }>(
    `
      SELECT invite_token
      FROM room_invites
      WHERE room_id = $1
      ORDER BY created_at DESC
      LIMIT 1
    `,
    [roomId],
  );

  if (existing.rows[0]) {
    return existing.rows[0].invite_token;
  }

  const token = randomUUID().replace(/-/g, "");
  await query(
    `
      INSERT INTO room_invites (room_id, invite_token, expires_at)
      VALUES ($1, $2, $3)
    `,
    [roomId, token, expiresAt],
  );

  return token;
}

export async function getRoomInvite(roomId: string, inviteToken: string) {
  const result = await query<{ room_id: string; expires_at: Date | string }>(
    `
      SELECT room_id, expires_at
      FROM room_invites
      WHERE room_id = $1 AND invite_token = $2
    `,
    [roomId, inviteToken],
  );

  return result.rows[0] || null;
}

async function getRoomMembers(roomId: string): Promise<RoomMember[]> {
  const result = await query<{
    user_id: string;
    display_name: string;
    role: "host" | "member";
    participation_status: "joined" | "submitted" | "voted" | "skipped";
    joined_at: Date | string;
  }>(
    `
      SELECT
        rm.user_id,
        u.display_name,
        rm.role,
        rm.participation_status,
        rm.joined_at
      FROM room_members rm
      JOIN users u ON u.id = rm.user_id
      WHERE rm.room_id = $1
      ORDER BY rm.joined_at ASC
    `,
    [roomId],
  );

  return result.rows.map((row) => ({
    userId: row.user_id,
    displayName: row.display_name,
    role: row.role,
    participationStatus: row.participation_status,
    joinedAt: safeDate(row.joined_at),
  }));
}

export async function getRoomDetail(roomId: string, inviteBaseUrl?: string): Promise<RoomDetail | null> {
  const roomResult = await query<{
    id: string;
    host_user_id: string | null;
    name: string | null;
    title: string | null;
    meal_type: RoomDetail["mealType"];
    mode: RoomDetail["mode"];
    location_label: string | null;
    target_lat: string | null;
    target_lng: string | null;
    group_size_expected: number;
    budget_min: string | null;
    budget_max: string | null;
    status: RoomDetail["status"];
    expires_at: Date | string;
    created_at: Date | string;
    updated_at: Date | string;
    latest_recommendation_run_id: string | null;
  }>(
    `
      SELECT
        r.*,
        (
          SELECT rr.id
          FROM recommendation_runs rr
          WHERE rr.room_id = r.id
          ORDER BY rr.started_at DESC
          LIMIT 1
        ) AS latest_recommendation_run_id
      FROM rooms r
      WHERE r.id = $1
    `,
    [roomId],
  );

  if (!roomResult.rows[0]) {
    return null;
  }

  const row = roomResult.rows[0];
  const members = await getRoomMembers(roomId);
  const submissionCountResult = await query<{ count: string }>(
    `
      SELECT COUNT(*) AS count
      FROM room_preferences
      WHERE room_id = $1
    `,
    [roomId],
  );

  const inviteToken = await getOrCreateRoomInvite(roomId, safeDate(row.expires_at));

  return {
    id: row.id,
    hostUserId: row.host_user_id,
    name: row.name || row.title || "Untitled room",
    mealType: row.meal_type,
    mode: row.mode,
    locationLabel: row.location_label,
    targetLat: numberOrNull(row.target_lat),
    targetLng: numberOrNull(row.target_lng),
    groupSizeExpected: row.group_size_expected,
    budgetMin: numberOrNull(row.budget_min),
    budgetMax: numberOrNull(row.budget_max),
    status: row.status,
    expiresAt: safeDate(row.expires_at),
    createdAt: safeDate(row.created_at),
    updatedAt: safeDate(row.updated_at),
    inviteToken,
    inviteUrl: inviteBaseUrl ? `${inviteBaseUrl}/voting/${roomId}?token=${inviteToken}` : null,
    participantCount: members.length,
    members,
    submissionCount: Number.parseInt(submissionCountResult.rows[0]?.count || "0", 10),
    latestRecommendationRunId: row.latest_recommendation_run_id,
    menuItems: [],
  };
}

export async function getRankerMembers(roomId: string) {
  const members = await query<{
    user_id: string;
    display_name: string;
    email: string | null;
    account_status: string;
    role: SessionUser["role"];
    room_role: "host" | "member";
    participation_status: "joined" | "submitted" | "voted" | "skipped";
    preferred_budget_min: string | null;
    preferred_budget_max: string | null;
    novelty_preference: UserProfile["noveltyPreference"] | null;
    dining_mode_preference: UserProfile["diningModePreference"] | null;
    work_lat: string | null;
    work_lng: string | null;
    restrictions_json: unknown;
    blocked_restaurant_ids_json: unknown;
    favorite_restaurant_ids_json: unknown;
    favorite_dish_ids_json: unknown;
    cuisine_preferences_json: unknown;
    dish_style_preferences_json: unknown;
    preference_version: number | null;
    profile_updated_at: Date | string | null;
  }>(
    `
      SELECT
        rm.user_id,
        u.display_name,
        u.email,
        u.account_status,
        u.role,
        rm.role AS room_role,
        rm.participation_status,
        up.preferred_budget_min,
        up.preferred_budget_max,
        up.novelty_preference,
        up.dining_mode_preference,
        up.work_lat,
        up.work_lng,
        up.restrictions_json,
        up.blocked_restaurant_ids_json,
        up.favorite_restaurant_ids_json,
        up.favorite_dish_ids_json,
        up.cuisine_preferences_json,
        up.dish_style_preferences_json,
        up.preference_version,
        up.updated_at AS profile_updated_at
      FROM room_members rm
      JOIN users u ON u.id = rm.user_id
      LEFT JOIN user_profiles up ON up.user_id = u.id
      WHERE rm.room_id = $1
      ORDER BY rm.joined_at ASC
    `,
    [roomId],
  );

  const preferences = await listRoomPreferences(roomId);
  const preferenceMap = new Map(preferences.map((entry) => [entry.userId, entry.preference]));

  return members.rows.map((row) => ({
    user: mapUser({
      id: row.user_id,
      email: row.email,
      display_name: row.display_name,
      account_status: row.account_status,
      role: row.role,
    }),
    profile: {
      userId: row.user_id,
      preferredBudgetMin: numberOrNull(row.preferred_budget_min),
      preferredBudgetMax: numberOrNull(row.preferred_budget_max),
      noveltyPreference: row.novelty_preference ?? "balanced",
      diningModePreference: row.dining_mode_preference ?? "mixed",
      workLat: numberOrNull(row.work_lat),
      workLng: numberOrNull(row.work_lng),
      restrictions: jsonParse<string[]>(row.restrictions_json, []),
      blockedRestaurantIds: jsonParse<string[]>(row.blocked_restaurant_ids_json, []),
      favoriteRestaurantIds: jsonParse<string[]>(row.favorite_restaurant_ids_json, []),
      favoriteDishIds: jsonParse<string[]>(row.favorite_dish_ids_json, []),
      cuisinePreferences: jsonParse<string[]>(row.cuisine_preferences_json, []),
      dishStylePreferences: jsonParse<string[]>(row.dish_style_preferences_json, []),
      preferenceVersion: row.preference_version ?? 1,
      updatedAt: safeDate(row.profile_updated_at),
    } satisfies UserProfile,
    preference: preferenceMap.get(row.user_id) ?? null,
    participationStatus: row.participation_status,
    roomRole: row.room_role,
  }));
}

export async function getHistorySnapshot(roomId: string, userIds: string[]) {
  const userHistory = await query<{
    user_id: string;
    restaurant_id: string | null;
    dish_id: string | null;
    count: string;
  }>(
    `
      SELECT
        user_id,
        restaurant_id,
        dish_id,
        COUNT(*) AS count
      FROM meal_history
      WHERE user_id = ANY($1)
      GROUP BY user_id, restaurant_id, dish_id
    `,
    [userIds],
  );

  const roomHistory = await query<{
    restaurant_id: string | null;
    count: string;
  }>(
    `
      SELECT
        restaurant_id,
        COUNT(*) AS count
      FROM meal_history
      WHERE room_id = $1
      GROUP BY restaurant_id
    `,
    [roomId],
  );

  const userRestaurantCounts: Record<string, Record<string, number>> = {};
  const userDishCounts: Record<string, Record<string, number>> = {};

  for (const row of userHistory.rows) {
    if (!userRestaurantCounts[row.user_id]) userRestaurantCounts[row.user_id] = {};
    if (!userDishCounts[row.user_id]) userDishCounts[row.user_id] = {};
    if (row.restaurant_id) userRestaurantCounts[row.user_id][row.restaurant_id] = Number.parseInt(row.count, 10);
    if (row.dish_id) userDishCounts[row.user_id][row.dish_id] = Number.parseInt(row.count, 10);
  }

  const roomRestaurantCounts: Record<string, number> = {};
  for (const row of roomHistory.rows) {
    if (row.restaurant_id) roomRestaurantCounts[row.restaurant_id] = Number.parseInt(row.count, 10);
  }

  return {
    userRestaurantCounts,
    userDishCounts,
    roomRestaurantCounts,
  };
}

export async function addRoomMember(roomId: string, user: SessionUser, role: "host" | "member" = "member") {
  await query(
    `
      INSERT INTO room_members (room_id, user_id, role, participation_status)
      VALUES ($1, $2, $3, 'joined')
      ON CONFLICT (room_id, user_id) DO UPDATE SET
        role = CASE WHEN room_members.role = 'host' THEN room_members.role ELSE EXCLUDED.role END
    `,
    [roomId, user.id, role],
  );

  await query(
    `
      INSERT INTO participants (id, room_id, name)
      VALUES ($1, $2, $3)
      ON CONFLICT (id, room_id) DO UPDATE SET name = EXCLUDED.name
    `,
    [user.id, roomId, user.displayName],
  );
}

export async function updateRoomStatus(roomId: string, status: RoomDetail["status"]) {
  await query(
    `
      UPDATE rooms
      SET status = $2, updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
    `,
    [roomId, status],
  );
}

export async function saveRoomPreference(roomId: string, userId: string, preference: RoomPreferenceSubmission, normalizedPayload: Record<string, unknown>) {
  await query(
    `
      INSERT INTO room_preferences (
        room_id,
        user_id,
        free_text_input,
        selected_suggestions_json,
        normalized_payload_json,
        hard_constraints_json,
        ranked_choices_json,
        prefill_accepted,
        passed,
        submitted_at
      )
      VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9, CURRENT_TIMESTAMP)
      ON CONFLICT (room_id, user_id) DO UPDATE SET
        free_text_input = EXCLUDED.free_text_input,
        selected_suggestions_json = EXCLUDED.selected_suggestions_json,
        normalized_payload_json = EXCLUDED.normalized_payload_json,
        hard_constraints_json = EXCLUDED.hard_constraints_json,
        ranked_choices_json = EXCLUDED.ranked_choices_json,
        prefill_accepted = EXCLUDED.prefill_accepted,
        passed = EXCLUDED.passed,
        submitted_at = CURRENT_TIMESTAMP
    `,
    [
      roomId,
      userId,
      preference.freeTextInput,
      JSON.stringify(preference.selectedSuggestions),
      JSON.stringify(normalizedPayload),
      JSON.stringify(preference.hardConstraints ?? {}),
      JSON.stringify(preference.rankedChoices ?? []),
      preference.prefillAccepted,
      preference.pass,
    ],
  );

  await query(
    `
      UPDATE room_members
      SET participation_status = 'submitted'
      WHERE room_id = $1 AND user_id = $2
    `,
    [roomId, userId],
  );
}

export async function getRoomPreference(roomId: string, userId: string): Promise<RoomPreferenceSubmission | null> {
  const result = await query<{
    free_text_input: string | null;
    selected_suggestions_json: unknown;
    hard_constraints_json: unknown;
    ranked_choices_json: unknown;
    prefill_accepted: boolean;
    passed: boolean;
  }>(
    `
      SELECT
        free_text_input,
        selected_suggestions_json,
        hard_constraints_json,
        ranked_choices_json,
        prefill_accepted,
        passed
      FROM room_preferences
      WHERE room_id = $1 AND user_id = $2
    `,
    [roomId, userId],
  );

  if (!result.rows[0]) {
    return null;
  }

  const row = result.rows[0];
  return {
    freeTextInput: row.free_text_input || "",
    selectedSuggestions: jsonParse<string[]>(row.selected_suggestions_json, []),
    hardConstraints: jsonParse<RoomPreferenceSubmission["hardConstraints"]>(row.hard_constraints_json, {}),
    rankedChoices: jsonParse<string[]>(row.ranked_choices_json, []),
    prefillAccepted: row.prefill_accepted,
    pass: row.passed,
  };
}

export async function listRoomPreferences(roomId: string) {
  const result = await query<{
    user_id: string;
    free_text_input: string | null;
    selected_suggestions_json: unknown;
    normalized_payload_json: unknown;
    hard_constraints_json: unknown;
    ranked_choices_json: unknown;
    prefill_accepted: boolean;
    passed: boolean;
  }>(
    `
      SELECT
        user_id,
        free_text_input,
        selected_suggestions_json,
        normalized_payload_json,
        hard_constraints_json,
        ranked_choices_json,
        prefill_accepted,
        passed
      FROM room_preferences
      WHERE room_id = $1
    `,
    [roomId],
  );

  return result.rows.map((row) => ({
    userId: row.user_id,
    preference: {
      freeTextInput: row.free_text_input || "",
      selectedSuggestions: jsonParse<string[]>(row.selected_suggestions_json, []),
      hardConstraints: jsonParse<RoomPreferenceSubmission["hardConstraints"]>(row.hard_constraints_json, {}),
      rankedChoices: jsonParse<string[]>(row.ranked_choices_json, []),
      prefillAccepted: row.prefill_accepted,
      pass: row.passed,
    } satisfies RoomPreferenceSubmission,
    normalizedPayload: jsonParse<Record<string, unknown>>(row.normalized_payload_json, {}),
  }));
}

export async function listRecommendationCatalog() {
  const result = await query<{
    restaurant_id: string;
    restaurant_name: string;
    restaurant_cuisine: string;
    service_mode: string;
    avg_price_min: string | null;
    avg_price_max: string | null;
    delivery_radius_km: string | null;
    reliability_score: string | null;
    supports_invoice: boolean;
    latitude: string | null;
    longitude: string | null;
    dish_id: string;
    dish_name: string;
    normalized_name: string;
    tags_json: unknown;
    current_price: string;
    vendor_id: string | null;
    approval_status: string | null;
    invoice_supported: boolean | null;
    supports_delivery: boolean | null;
    supports_dine_in: boolean | null;
    vendor_reliability_score: string | null;
    delivery_sla_mins: string | null;
  }>(
    `
      SELECT
        r.id AS restaurant_id,
        r.name AS restaurant_name,
        r.cuisine AS restaurant_cuisine,
        r.service_mode,
        r.avg_price_min,
        r.avg_price_max,
        r.delivery_radius_km,
        r.reliability_score,
        r.supports_invoice,
        r.latitude,
        r.longitude,
        d.id AS dish_id,
        d.name AS dish_name,
        d.normalized_name,
        d.tags_json,
        rd.current_price,
        v.id AS vendor_id,
        v.approval_status,
        v.invoice_supported,
        v.supports_delivery,
        v.supports_dine_in,
        v.reliability_score AS vendor_reliability_score,
        v.delivery_sla_mins
      FROM restaurant_dishes rd
      JOIN restaurants r ON r.id = rd.restaurant_id
      JOIN dishes d ON d.id = rd.dish_id
      LEFT JOIN vendors v ON v.restaurant_id = r.id
      WHERE rd.active = TRUE
        AND r.status = 'active'
        AND d.active = TRUE
      ORDER BY r.rating DESC, r.name ASC, d.name ASC
    `,
  );

  return result.rows.map((row) => ({
    restaurantId: row.restaurant_id,
    restaurantName: row.restaurant_name,
    cuisine: row.restaurant_cuisine,
    serviceMode: row.service_mode,
    avgPriceMin: numberOrNull(row.avg_price_min),
    avgPriceMax: numberOrNull(row.avg_price_max),
    deliveryRadiusKm: numberOrNull(row.delivery_radius_km),
    restaurantReliabilityScore: numberOrNull(row.reliability_score) ?? 0.8,
    supportsInvoice: row.supports_invoice,
    latitude: numberOrNull(row.latitude),
    longitude: numberOrNull(row.longitude),
    dishId: row.dish_id,
    dishName: row.dish_name,
    normalizedDishName: row.normalized_name,
    tags: jsonParse<string[]>(row.tags_json, []),
    currentPrice: numberOrNull(row.current_price) ?? 0,
    vendorId: row.vendor_id,
    approvalStatus: row.approval_status ?? "approved",
    invoiceSupported: row.invoice_supported ?? row.supports_invoice,
    supportsDelivery: row.supports_delivery ?? true,
    supportsDineIn: row.supports_dine_in ?? true,
    vendorReliabilityScore: numberOrNull(row.vendor_reliability_score) ?? numberOrNull(row.reliability_score) ?? 0.8,
    deliverySlaMins: numberOrNull(row.delivery_sla_mins),
  }));
}

export async function createRecommendationRun(payload: {
  roomId: string;
  algorithmVersion: string;
  configVersion: string;
  requestContext: Record<string, unknown>;
  status: RecommendationRunSummary["status"];
  candidates: RecommendationCandidate[];
  perUserScores: Array<{
    candidateId: string;
    userId: string;
    scores: Record<string, number>;
  }>;
}) {
  return withTransaction(async (client) => {
    const runResult = await query<{ id: string; started_at: Date | string }>(
      `
        INSERT INTO recommendation_runs (
          room_id,
          algorithm_version,
          config_version,
          request_context_json,
          status,
          completed_at
        )
        VALUES ($1, $2, $3, $4::jsonb, $5, CURRENT_TIMESTAMP)
        RETURNING id, started_at
      `,
      [
        payload.roomId,
        payload.algorithmVersion,
        payload.configVersion,
        JSON.stringify(payload.requestContext),
        payload.status,
      ],
      client,
    );

    const runId = runResult.rows[0].id;

    for (const candidate of payload.candidates) {
      await query(
        `
          INSERT INTO recommendation_candidates (
            id,
            recommendation_run_id,
            candidate_type,
            candidate_ref_id,
            composite_payload_json,
            base_score,
            final_score,
            confidence,
            rank_position,
            explanation_json,
            selected_for_vote
          )
          VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10::jsonb, $11)
        `,
        [
          candidate.candidateId,
          runId,
          candidate.candidateType,
          candidate.candidateRefId,
          JSON.stringify({
            title: candidate.title,
            restaurantId: candidate.restaurantId,
            restaurantName: candidate.restaurantName,
            dishId: candidate.dishId,
            dishName: candidate.dishName,
            cuisine: candidate.cuisine,
            mode: candidate.mode,
            price: candidate.price,
            breakdown: candidate.breakdown ?? {},
          }),
          candidate.breakdown?.baseScore ?? candidate.finalScore,
          candidate.finalScore,
          candidate.confidence,
          payload.candidates.findIndex((item) => item.candidateId === candidate.candidateId) + 1,
          JSON.stringify(candidate.reasons),
          candidate.selectedForVote,
        ],
        client,
      );
    }

    for (const scoreEntry of payload.perUserScores) {
      await query(
        `
          INSERT INTO recommendation_user_scores (
            recommendation_run_id,
            candidate_id,
            user_id,
            preference_score,
            frequency_score,
            familiarity_score,
            context_score,
            budget_score,
            reliability_score,
            social_affinity_score,
            novelty_score,
            cooldown_penalty,
            friction_penalty,
            final_personal_score
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        `,
        [
          runId,
          scoreEntry.candidateId,
          scoreEntry.userId,
          scoreEntry.scores.preferenceScore ?? 0,
          scoreEntry.scores.frequencyScore ?? 0,
          scoreEntry.scores.familiarityScore ?? 0,
          scoreEntry.scores.contextScore ?? 0,
          scoreEntry.scores.budgetScore ?? 0,
          scoreEntry.scores.reliabilityScore ?? 0,
          scoreEntry.scores.socialAffinityScore ?? 0,
          scoreEntry.scores.noveltyScore ?? 0,
          scoreEntry.scores.cooldownPenalty ?? 0,
          scoreEntry.scores.frictionPenalty ?? 0,
          scoreEntry.scores.finalPersonalScore ?? 0,
        ],
        client,
      );
    }

    await query(
      `
        UPDATE rooms
        SET status = 'voting', updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
      `,
      [payload.roomId],
      client,
    );

    return {
      runId,
      startedAt: safeDate(runResult.rows[0].started_at),
    };
  });
}

export async function getLatestRecommendationRun(roomId: string): Promise<RecommendationRunSummary | null> {
  const runResult = await query<{
    id: string;
    room_id: string;
    algorithm_version: string;
    config_version: string;
    status: RecommendationRunSummary["status"];
    request_context_json: unknown;
    started_at: Date | string;
  }>(
    `
      SELECT id, room_id, algorithm_version, config_version, status, request_context_json, started_at
      FROM recommendation_runs
      WHERE room_id = $1
      ORDER BY started_at DESC
      LIMIT 1
    `,
    [roomId],
  );

  if (!runResult.rows[0]) {
    return null;
  }

  const run = runResult.rows[0];
  const candidateResult = await query<{
    id: string;
    candidate_type: RecommendationCandidate["candidateType"];
    candidate_ref_id: string | null;
    composite_payload_json: unknown;
    final_score: string;
    confidence: string;
    selected_for_vote: boolean;
    explanation_json: unknown;
  }>(
    `
      SELECT
        id,
        candidate_type,
        candidate_ref_id,
        composite_payload_json,
        final_score,
        confidence,
        selected_for_vote,
        explanation_json
      FROM recommendation_candidates
      WHERE recommendation_run_id = $1
      ORDER BY rank_position ASC
    `,
    [run.id],
  );

  const topOptions: RecommendationCandidate[] = candidateResult.rows.map((row) => {
    const payload = jsonParse<Record<string, unknown>>(row.composite_payload_json, {});
    return {
      candidateId: row.id,
      candidateType: row.candidate_type,
      candidateRefId: row.candidate_ref_id,
      title: String(payload.title || "Untitled option"),
      restaurantId: typeof payload.restaurantId === "string" ? payload.restaurantId : null,
      restaurantName: typeof payload.restaurantName === "string" ? payload.restaurantName : null,
      dishId: typeof payload.dishId === "string" ? payload.dishId : null,
      dishName: typeof payload.dishName === "string" ? payload.dishName : null,
      cuisine: typeof payload.cuisine === "string" ? payload.cuisine : null,
      mode: (payload.mode as RecommendationCandidate["mode"]) ?? null,
      price: numberOrNull(payload.price),
      finalScore: numberOrNull(row.final_score) ?? 0,
      confidence: numberOrNull(row.confidence) ?? 0,
      selectedForVote: row.selected_for_vote,
      reasons: jsonParse<string[]>(row.explanation_json, []),
      breakdown: jsonParse<Record<string, number>>(payload.breakdown, {}),
    };
  });

  return {
    runId: run.id,
    roomId: run.room_id,
    algorithmVersion: run.algorithm_version,
    configVersion: run.config_version,
    status: run.status,
    topOptions,
    generatedAt: safeDate(run.started_at),
    requestContext: jsonParse<Record<string, unknown>>(run.request_context_json, {}),
  };
}

export async function submitVote(roomId: string, userId: string, candidateId: string, voteValue = 1) {
  await query(
    `
      DELETE FROM votes
      WHERE room_id = $1 AND user_id = $2 AND recommendation_candidate_id IS NOT NULL
    `,
    [roomId, userId],
  );

  await query(
    `
      INSERT INTO votes (room_id, user_id, recommendation_candidate_id, vote_value, created_at)
      VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
    `,
    [roomId, userId, candidateId, voteValue],
  );

  await query(
    `
      UPDATE room_members
      SET participation_status = 'voted'
      WHERE room_id = $1 AND user_id = $2
    `,
    [roomId, userId],
  );
}

export async function getVoteSummary(roomId: string, userId: string): Promise<VoteSummary> {
  const latestRun = await getLatestRecommendationRun(roomId);
  const roomResult = await query<{ status: string }>("SELECT status FROM rooms WHERE id = $1", [roomId]);

  const voteResult = await query<{
    recommendation_candidate_id: string;
    count: string;
    weighted_score: string;
    my_vote: boolean;
  }>(
    `
      SELECT
        recommendation_candidate_id,
        COUNT(*) AS count,
        COALESCE(SUM(vote_value), 0) AS weighted_score,
        BOOL_OR(user_id = $2) AS my_vote
      FROM votes
      WHERE room_id = $1
        AND recommendation_candidate_id IS NOT NULL
      GROUP BY recommendation_candidate_id
    `,
    [roomId, userId],
  );

  const candidateMap = new Map(
    (latestRun?.topOptions || []).map((candidate) => [candidate.candidateId, candidate]),
  );

  const votes = voteResult.rows.map((row) => ({
    candidateId: row.recommendation_candidate_id,
    title: candidateMap.get(row.recommendation_candidate_id)?.title || "Unknown option",
    count: Number.parseInt(row.count, 10),
    weightedScore: numberOrNull(row.weighted_score) ?? 0,
  }));

  const myVote = voteResult.rows.find((row) => row.my_vote)?.recommendation_candidate_id || null;

  return {
    roomId,
    runId: latestRun?.runId || null,
    totalVotes: votes.reduce((total, item) => total + item.count, 0),
    votes,
    myVote,
    closed: roomResult.rows[0]?.status === "decided" || roomResult.rows[0]?.status === "expired",
  };
}

export async function finalizeDecision(roomId: string, runId: string, decisionType: FinalDecision["decisionType"], selectedOption: RecommendationCandidate | null, confidenceScore: number) {
  return withTransaction(async (client) => {
    const result = await query<{
      id: string;
      decided_at: Date | string;
    }>(
      `
        INSERT INTO final_decisions (
          room_id,
          recommendation_run_id,
          decision_type,
          selected_payload_json,
          confidence_score
        )
        VALUES ($1, $2, $3, $4::jsonb, $5)
        RETURNING id, decided_at
      `,
      [
        roomId,
        runId,
        decisionType,
        JSON.stringify(selectedOption ?? {}),
        confidenceScore,
      ],
      client,
    );

    await query(
      `
        UPDATE rooms
        SET status = 'decided', updated_at = CURRENT_TIMESTAMP, closed_at = CURRENT_TIMESTAMP
        WHERE id = $1
      `,
      [roomId],
      client,
    );

    if (selectedOption) {
      const members = await query<{ user_id: string }>(
        `
          SELECT user_id
          FROM room_members
          WHERE room_id = $1
        `,
        [roomId],
        client,
      );

      for (const member of members.rows) {
        await query(
          `
            INSERT INTO meal_history (user_id, room_id, restaurant_id, dish_id, chosen_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
          `,
          [member.user_id, roomId, selectedOption.restaurantId, selectedOption.dishId],
          client,
        );
      }
    }

    return {
      id: result.rows[0].id,
      decidedAt: safeDate(result.rows[0].decided_at),
    };
  });
}

export async function getFinalDecision(roomId: string): Promise<FinalDecision | null> {
  const result = await query<{
    id: string;
    room_id: string;
    recommendation_run_id: string;
    decision_type: FinalDecision["decisionType"];
    selected_payload_json: unknown;
    confidence_score: string;
    decided_at: Date | string;
  }>(
    `
      SELECT *
      FROM final_decisions
      WHERE room_id = $1
      ORDER BY decided_at DESC
      LIMIT 1
    `,
    [roomId],
  );

  if (!result.rows[0]) {
    return null;
  }

  const row = result.rows[0];
  const option = jsonParse<RecommendationCandidate | null>(row.selected_payload_json, null);
  return {
    id: row.id,
    roomId: row.room_id,
    recommendationRunId: row.recommendation_run_id,
    decisionType: row.decision_type,
    confidenceScore: numberOrNull(row.confidence_score) ?? 0,
    decidedAt: safeDate(row.decided_at),
    selectedOption: option,
  };
}

export async function listVendors(): Promise<Vendor[]> {
  const result = await query<{
    id: string;
    restaurant_id: string;
    restaurant_name: string;
    source_system: string | null;
    external_ref: string | null;
    account_manager: string | null;
    active_contract: boolean;
    approval_status: Vendor["approvalStatus"];
    invoice_supported: boolean;
    supports_delivery: boolean;
    supports_dine_in: boolean;
    reliability_score: string;
    delivery_sla_mins: string | null;
    notes: string | null;
    imported_payload_json: unknown;
    created_at: Date | string;
    updated_at: Date | string;
  }>(
    `
      SELECT
        v.*,
        r.name AS restaurant_name
      FROM vendors v
      JOIN restaurants r ON r.id = v.restaurant_id
      ORDER BY r.name ASC
    `,
  );

  return result.rows.map((row) => ({
    id: row.id,
    restaurantId: row.restaurant_id,
    restaurantName: row.restaurant_name,
    sourceSystem: row.source_system,
    externalRef: row.external_ref,
    accountManager: row.account_manager,
    activeContract: row.active_contract,
    approvalStatus: row.approval_status,
    invoiceSupported: row.invoice_supported,
    supportsDelivery: row.supports_delivery,
    supportsDineIn: row.supports_dine_in,
    reliabilityScore: numberOrNull(row.reliability_score) ?? 0.8,
    deliverySlaMins: numberOrNull(row.delivery_sla_mins),
    notes: row.notes,
    importedPayload: jsonParse<Record<string, unknown> | null>(row.imported_payload_json, null),
    createdAt: safeDate(row.created_at),
    updatedAt: safeDate(row.updated_at),
  }));
}

export async function upsertVendor(payload: Partial<Vendor> & { restaurantId: string }) {
  const result = await query<{ id: string }>(
    `
      INSERT INTO vendors (
        restaurant_id,
        source_system,
        external_ref,
        account_manager,
        active_contract,
        approval_status,
        invoice_supported,
        supports_delivery,
        supports_dine_in,
        reliability_score,
        delivery_sla_mins,
        notes,
        imported_payload_json
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
      ON CONFLICT (restaurant_id) DO UPDATE SET
        source_system = EXCLUDED.source_system,
        external_ref = EXCLUDED.external_ref,
        account_manager = EXCLUDED.account_manager,
        active_contract = EXCLUDED.active_contract,
        approval_status = EXCLUDED.approval_status,
        invoice_supported = EXCLUDED.invoice_supported,
        supports_delivery = EXCLUDED.supports_delivery,
        supports_dine_in = EXCLUDED.supports_dine_in,
        reliability_score = EXCLUDED.reliability_score,
        delivery_sla_mins = EXCLUDED.delivery_sla_mins,
        notes = EXCLUDED.notes,
        imported_payload_json = EXCLUDED.imported_payload_json,
        updated_at = CURRENT_TIMESTAMP
      RETURNING id
    `,
    [
      payload.restaurantId,
      payload.sourceSystem ?? "third_party_import",
      payload.externalRef ?? null,
      payload.accountManager ?? null,
      payload.activeContract ?? true,
      payload.approvalStatus ?? "approved",
      payload.invoiceSupported ?? false,
      payload.supportsDelivery ?? true,
      payload.supportsDineIn ?? true,
      payload.reliabilityScore ?? 0.8,
      payload.deliverySlaMins ?? null,
      payload.notes ?? null,
      JSON.stringify(payload.importedPayload ?? {}),
    ],
  );

  const vendorId = result.rows[0].id;
  const vendors = await listVendors();
  return vendors.find((vendor) => vendor.id === vendorId) || null;
}

export async function getLunchReportSummary(): Promise<LunchReportSummary> {
  const roomStats = await query<{
    total_rooms: string;
    decided_rooms: string;
    average_decision_minutes: string | null;
    average_budget: string | null;
  }>(
    `
      SELECT
        COUNT(*) AS total_rooms,
        COUNT(*) FILTER (WHERE status = 'decided') AS decided_rooms,
        AVG(EXTRACT(EPOCH FROM (COALESCE(closed_at, updated_at) - created_at)) / 60.0) FILTER (WHERE status = 'decided') AS average_decision_minutes,
        AVG(COALESCE(budget_max, budget_min, 0)) AS average_budget
      FROM rooms
    `,
  );

  const voteStats = await query<{ total_votes: string }>(
    `
      SELECT COUNT(*) AS total_votes
      FROM votes
      WHERE recommendation_candidate_id IS NOT NULL
    `,
  );

  const mealStats = await query<{ total_meal_history_records: string }>(
    `
      SELECT COUNT(*) AS total_meal_history_records
      FROM meal_history
    `,
  );

  const topVendorsResult = await query<{
    vendor_id: string;
    restaurant_name: string;
    orders_count: string;
    reliability_score: string;
  }>(
    `
      SELECT
        v.id AS vendor_id,
        r.name AS restaurant_name,
        COUNT(mh.id) AS orders_count,
        v.reliability_score
      FROM vendors v
      JOIN restaurants r ON r.id = v.restaurant_id
      LEFT JOIN meal_history mh ON mh.restaurant_id = r.id
      GROUP BY v.id, r.name, v.reliability_score
      ORDER BY orders_count DESC, v.reliability_score DESC
      LIMIT 5
    `,
  );

  const roomRow = roomStats.rows[0];
  return {
    totalRooms: Number.parseInt(roomRow?.total_rooms || "0", 10),
    decidedRooms: Number.parseInt(roomRow?.decided_rooms || "0", 10),
    averageDecisionMinutes: numberOrNull(roomRow?.average_decision_minutes) ?? 0,
    totalVotes: Number.parseInt(voteStats.rows[0]?.total_votes || "0", 10),
    totalMealHistoryRecords: Number.parseInt(mealStats.rows[0]?.total_meal_history_records || "0", 10),
    averageBudget: numberOrNull(roomRow?.average_budget) ?? 0,
    topVendors: topVendorsResult.rows.map((row) => ({
      vendorId: row.vendor_id,
      restaurantName: row.restaurant_name,
      ordersCount: Number.parseInt(row.orders_count, 10),
      reliabilityScore: numberOrNull(row.reliability_score) ?? 0.8,
    })),
  };
}
