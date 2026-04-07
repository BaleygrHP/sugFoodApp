import { randomUUID } from "crypto";

import { query } from "@/lib/db";
import { appConfig } from "@/lib/server/config";
import { AppError, assert } from "@/lib/server/errors";
import {
  addRoomMember,
  createGuestUser,
  createRecommendationRun,
  createRoomRecord,
  ensureUserProfile,
  finalizeDecision,
  getFinalDecision,
  getHistorySnapshot,
  getLatestRecommendationRun,
  getLunchReportSummary,
  getOrCreateRoomInvite,
  getRankerMembers,
  getRoomDetail,
  getRoomInvite,
  getRoomPreference,
  getUserById,
  getUserProfile,
  listRecommendationCatalog,
  listVendors,
  saveRoomPreference,
  setBlockedRestaurant,
  submitVote,
  updateRoomStatus,
  updateUserAccount,
  updateUserProfile,
  upsertVendor,
  getVoteSummary,
} from "@/lib/server/repositories";
import { buildPrefillSuggestions, buildNormalizedPayload, runRecommendationRanker } from "@/lib/server/ranker";
import type {
  FinalDecision,
  RecommendationRunSummary,
  RoomDetail,
  RoomPreferenceSubmission,
  SessionUser,
  UserProfile,
  Vendor,
} from "@/lib/server/types";
import { buildDisplayName, clamp } from "@/lib/server/utils";

async function trackEvent(eventName: string, payload: { userId?: string | null; roomId?: string | null; data?: Record<string, unknown> }) {
  await query(
    `
      INSERT INTO analytics_events (event_name, user_id, room_id, payload_json, app_version)
      VALUES ($1, $2, $3, $4::jsonb, $5)
    `,
    [
      eventName,
      payload.userId || null,
      payload.roomId || null,
      JSON.stringify(payload.data || {}),
      "web-v1",
    ],
  );
}

async function mergeGuestIntoUser(guestUserId: string, targetUserId: string) {
  if (guestUserId === targetUserId) {
    return;
  }

  const [guestProfile, targetProfile] = await Promise.all([
    getUserProfile(guestUserId),
    ensureUserProfile(targetUserId),
  ]);

  if (guestProfile && targetProfile) {
    await updateUserProfile(targetUserId, {
      preferredBudgetMin: targetProfile.preferredBudgetMin ?? guestProfile.preferredBudgetMin,
      preferredBudgetMax: targetProfile.preferredBudgetMax ?? guestProfile.preferredBudgetMax,
      noveltyPreference: targetProfile.noveltyPreference ?? guestProfile.noveltyPreference,
      diningModePreference: targetProfile.diningModePreference ?? guestProfile.diningModePreference,
      workLat: targetProfile.workLat ?? guestProfile.workLat,
      workLng: targetProfile.workLng ?? guestProfile.workLng,
      restrictions: Array.from(new Set([...targetProfile.restrictions, ...guestProfile.restrictions])),
      blockedRestaurantIds: Array.from(new Set([...targetProfile.blockedRestaurantIds, ...guestProfile.blockedRestaurantIds])),
      favoriteRestaurantIds: Array.from(new Set([...targetProfile.favoriteRestaurantIds, ...guestProfile.favoriteRestaurantIds])),
      favoriteDishIds: Array.from(new Set([...targetProfile.favoriteDishIds, ...guestProfile.favoriteDishIds])),
      cuisinePreferences: Array.from(new Set([...targetProfile.cuisinePreferences, ...guestProfile.cuisinePreferences])),
      dishStylePreferences: Array.from(new Set([...targetProfile.dishStylePreferences, ...guestProfile.dishStylePreferences])),
    });
  }

  await query(
    `
      UPDATE meal_history
      SET user_id = $2
      WHERE user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE analytics_events
      SET user_id = $2
      WHERE user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE votes
      SET user_id = $2
      WHERE user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      DELETE FROM room_members rm
      USING room_members existing
      WHERE rm.user_id = $1
        AND existing.user_id = $2
        AND existing.room_id = rm.room_id
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE room_members
      SET user_id = $2
      WHERE user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      DELETE FROM room_preferences rp
      USING room_preferences existing
      WHERE rp.user_id = $1
        AND existing.user_id = $2
        AND existing.room_id = rp.room_id
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE room_preferences
      SET user_id = $2
      WHERE user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      DELETE FROM participants p
      USING participants existing
      WHERE p.id = $1
        AND existing.id = $2
        AND existing.room_id = p.room_id
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE participants
      SET id = $2
      WHERE id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      UPDATE rooms
      SET host_user_id = $2
      WHERE host_user_id = $1
    `,
    [guestUserId, targetUserId],
  );

  await query(
    `
      DELETE FROM user_profiles
      WHERE user_id = $1
    `,
    [guestUserId],
  );

  await query(
    `
      DELETE FROM users
      WHERE id = $1
    `,
    [guestUserId],
  );
}

export async function createGuestSession(displayName?: string) {
  const guest = await createGuestUser(displayName?.trim() || buildDisplayName("Guest", randomUUID()));
  await trackEvent("guest_session_created", { userId: guest.id });
  return guest;
}

export async function loginWithEmail(currentUser: SessionUser | null, payload: { email: string; displayName?: string }) {
  const normalizedEmail = payload.email.trim().toLowerCase();
  assert(normalizedEmail, "Email is required");
  const adminEmails = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  const resolvedRole: SessionUser["role"] = adminEmails.includes(normalizedEmail) ? "admin" : "user";

  const existing = await query<{
    id: string;
    email: string | null;
    display_name: string;
    account_status: string;
    role: SessionUser["role"];
  }>(
    `
      SELECT id, email, display_name, account_status, role
      FROM users
      WHERE email = $1
      LIMIT 1
    `,
    [normalizedEmail],
  );

  if (existing.rows[0]) {
    if (currentUser && currentUser.id !== existing.rows[0].id) {
      await mergeGuestIntoUser(currentUser.id, existing.rows[0].id);
    }

    const user = {
      id: existing.rows[0].id,
      email: existing.rows[0].email,
      displayName: existing.rows[0].display_name,
      accountStatus: existing.rows[0].account_status,
      role: existing.rows[0].role,
    } satisfies SessionUser;
    await trackEvent("user_login", { userId: user.id });
    return user;
  }

  const targetUser = currentUser
    ? await updateUserAccount(currentUser.id, {
        displayName: payload.displayName?.trim() || currentUser.displayName,
        email: normalizedEmail,
        role: resolvedRole,
        accountStatus: "active",
      })
    : await updateUserAccount(
        (await createGuestUser(payload.displayName?.trim() || buildDisplayName("User", randomUUID()))).id,
        {
          displayName: payload.displayName?.trim() || undefined,
          email: normalizedEmail,
          role: resolvedRole,
          accountStatus: "active",
        },
      );

  await trackEvent("user_login", { userId: targetUser.id });
  return targetUser;
}

export async function getMyProfile(userId: string) {
  const user = await getUserById(userId);
  const profile = await ensureUserProfile(userId);
  assert(user && profile, "User not found", 404, "not_found");
  return { user, profile };
}

export async function updateMyProfile(userId: string, payload: Partial<UserProfile> & { displayName?: string }) {
  if (payload.displayName) {
    await updateUserAccount(userId, { displayName: payload.displayName });
  }

  const profile = await updateUserProfile(userId, payload);
  await trackEvent("profile_updated", { userId, data: { preferenceVersion: profile.preferenceVersion } });
  return profile;
}

export async function blockRestaurantForUser(userId: string, restaurantId: string, blocked: boolean) {
  const profile = await setBlockedRestaurant(userId, restaurantId, blocked);
  await trackEvent(blocked ? "restaurant_blocked" : "restaurant_unblocked", {
    userId,
    data: { restaurantId },
  });
  return profile;
}

export async function createRoom(user: SessionUser, payload: Partial<{
  name: string;
  mealType: RoomDetail["mealType"];
  mode: RoomDetail["mode"];
  locationLabel: string | null;
  targetLat: number | null;
  targetLng: number | null;
  groupSizeExpected: number;
  budgetMin: number | null;
  budgetMax: number | null;
  expiresInMinutes: number;
}>) {
  if (user.role === "guest") {
    user = await updateUserAccount(user.id, { role: "room_host" });
  }

  const expiresAt = new Date();
  expiresAt.setMinutes(expiresAt.getMinutes() + (payload.expiresInMinutes || 30));

  const roomId = await createRoomRecord({
    hostUserId: user.id,
    name: payload.name?.trim() || "Team Lunch",
    mealType: payload.mealType || "lunch",
    mode: payload.mode || "mixed",
    locationLabel: payload.locationLabel ?? null,
    targetLat: payload.targetLat ?? null,
    targetLng: payload.targetLng ?? null,
    groupSizeExpected: payload.groupSizeExpected || 3,
    budgetMin: payload.budgetMin ?? null,
    budgetMax: payload.budgetMax ?? null,
    expiresAt,
  });

  await trackEvent("room_created", { userId: user.id, roomId });
  return getRoomDetail(roomId, appConfig.appUrl);
}

export async function joinRoom(user: SessionUser, roomId: string, inviteToken?: string | null) {
  const room = await getRoomDetail(roomId, appConfig.appUrl);
  assert(room, "Room not found", 404, "not_found");
  assert(room.status !== "expired" && room.status !== "decided", "Room is closed", 400, "room_closed");

  if (inviteToken) {
    const invite = await getRoomInvite(roomId, inviteToken);
    assert(invite, "Invalid invite token", 403, "invalid_invite");
  }

  await addRoomMember(roomId, user, room.hostUserId === user.id ? "host" : "member");
  await trackEvent("room_joined", { userId: user.id, roomId });
  return getRoomDetail(roomId, appConfig.appUrl);
}

export async function getRoomForViewer(user: SessionUser, roomId: string, inviteToken?: string | null) {
  const room = await getRoomDetail(roomId, appConfig.appUrl);
  assert(room, "Room not found", 404, "not_found");

  const isMember = room.members.some((member) => member.userId === user.id);
  if (!isMember) {
    return joinRoom(user, roomId, inviteToken);
  }

  return room;
}

export async function getPrefill(roomId: string, userId: string) {
  const profile = await ensureUserProfile(userId);
  const history = await getHistorySnapshot(roomId, [userId]);
  const catalog = await listRecommendationCatalog();
  const userHistory = history.userRestaurantCounts[userId] || {};
  const suggestions = buildPrefillSuggestions(profile!, catalog, userHistory);

  await trackEvent("prefill_shown", { userId, roomId, data: { count: suggestions.length } });
  return suggestions;
}

export async function submitPreference(user: SessionUser, roomId: string, preference: RoomPreferenceSubmission) {
  const room = await getRoomForViewer(user, roomId);
  assert(room.status === "open", "Room is no longer accepting submissions", 400, "room_closed");

  const catalog = await listRecommendationCatalog();
  const normalizedPayload = buildNormalizedPayload(preference, catalog);
  await saveRoomPreference(roomId, user.id, preference, normalizedPayload);

  await trackEvent("preference_submitted", {
    userId: user.id,
    roomId,
    data: { prefillAccepted: preference.prefillAccepted, pass: preference.pass },
  });

  return getRoomPreference(roomId, user.id);
}

async function runRoomRecommendation(roomId: string, requestedBy: SessionUser, requestContext: Record<string, unknown> = {}) {
  const room = await getRoomForViewer(requestedBy, roomId);
  await updateRoomStatus(roomId, "ranking");
  await trackEvent("recommendation_run_started", { userId: requestedBy.id, roomId });

  const members = await getRankerMembers(roomId);
  const catalog = await listRecommendationCatalog();
  const history = await getHistorySnapshot(roomId, members.map((member) => member.user.id));
  const rankerOutput = runRecommendationRanker(
    {
      room,
      members: members.map((member) => ({
        user: member.user,
        profile: member.profile,
        preference: member.preference,
        participationStatus: member.participationStatus,
      })),
      exploreModeEnabled: appConfig.featureFlags.exploreModeEnabled,
      requestContext,
    },
    catalog,
    history,
  );

  const candidateIdMap = new Map<string, string>();
  const candidates = rankerOutput.topOptions.map((candidate) => {
    const newId = randomUUID();
    candidateIdMap.set(candidate.candidateId, newId);
    return {
      ...candidate,
      candidateId: newId,
    };
  });

  const persisted = await createRecommendationRun({
    roomId,
    algorithmVersion: appConfig.ranking.algorithmVersion,
    configVersion: appConfig.ranking.configVersion,
    requestContext: {
      ...requestContext,
      splitRecommended: rankerOutput.splitRecommended,
    },
    status: "success",
    candidates,
    perUserScores: rankerOutput.perUserScores
      .filter((entry) => candidateIdMap.has(entry.candidateId))
      .map((entry) => ({
        ...entry,
        candidateId: candidateIdMap.get(entry.candidateId)!,
      })),
  });

  await trackEvent("recommendation_run_completed", {
    userId: requestedBy.id,
    roomId,
    data: { runId: persisted.runId, candidates: candidates.length },
  });

  return getLatestRecommendationRun(roomId);
}

export async function closeSubmissions(user: SessionUser, roomId: string) {
  const room = await getRoomForViewer(user, roomId);
  assert(room.hostUserId === user.id, "Only the room host can close submissions", 403, "forbidden");
  assert(room.status === "open", "Room is no longer open", 400, "room_closed");
  return runRoomRecommendation(roomId, user, {
    source: "close_submission",
  });
}

export async function runRecommendationsManually(user: SessionUser, roomId: string) {
  const room = await getRoomForViewer(user, roomId);
  assert(room.hostUserId === user.id || user.role === "admin" || user.role === "ops_admin", "Forbidden", 403, "forbidden");
  return runRoomRecommendation(roomId, user, {
    source: "manual",
  });
}

export async function getLatestRecommendations(user: SessionUser, roomId: string) {
  await getRoomForViewer(user, roomId);
  return getLatestRecommendationRun(roomId);
}

export async function submitRoomVote(user: SessionUser, roomId: string, candidateId: string, voteValue = 1) {
  const room = await getRoomForViewer(user, roomId);
  assert(room.status === "voting", "Room is not in voting state", 400, "room_not_voting");
  await submitVote(roomId, user.id, candidateId, voteValue);
  await trackEvent("vote_submitted", { userId: user.id, roomId, data: { candidateId, voteValue } });
  return getVoteSummary(roomId, user.id);
}

export async function getVotesSummary(user: SessionUser, roomId: string) {
  await getRoomForViewer(user, roomId);
  return getVoteSummary(roomId, user.id);
}

export async function closeVoteAndFinalize(user: SessionUser, roomId: string) {
  const room = await getRoomForViewer(user, roomId);
  assert(room.hostUserId === user.id || user.role === "admin" || user.role === "ops_admin", "Only the host can close voting", 403, "forbidden");
  assert(room.status === "voting", "Room is not currently voting", 400, "room_not_voting");

  const latestRun = await getLatestRecommendationRun(roomId);
  assert(latestRun, "No recommendation run found", 404, "not_found");

  const voteSummary = await getVoteSummary(roomId, user.id);
  const topOptions = latestRun.topOptions.filter((candidate) => candidate.selectedForVote || candidate.finalScore > 0);

  const winner = topOptions
    .map((candidate) => {
      const voteEntry = voteSummary.votes.find((vote) => vote.candidateId === candidate.candidateId);
      const voteBoost = voteSummary.totalVotes > 0 ? (voteEntry?.weightedScore || 0) / voteSummary.totalVotes : 0;
      return {
        candidate,
        combined: clamp(candidate.finalScore * 0.7 + voteBoost * 0.3, 0, 1),
      };
    })
    .sort((a, b) => b.combined - a.combined)[0];

  const decisionType: FinalDecision["decisionType"] =
    appConfig.featureFlags.splitGroupEnabled &&
    room.participantCount >= 8 &&
    (!winner || winner.combined < 0.45)
      ? "split_group"
      : room.mode === "delivery"
        ? "delivery"
        : "dine_in";

  const decision = await finalizeDecision(
    roomId,
    latestRun.runId,
    decisionType,
    winner?.candidate || latestRun.topOptions[0] || null,
    winner?.combined || latestRun.topOptions[0]?.confidence || 0,
  );

  await trackEvent("decision_finalized", {
    userId: user.id,
    roomId,
    data: {
      decisionId: decision.id,
      decisionType,
      selectedCandidateId: winner?.candidate.candidateId || null,
    },
  });

  return getFinalDecision(roomId);
}

export async function getDecision(user: SessionUser, roomId: string) {
  await getRoomForViewer(user, roomId);
  return getFinalDecision(roomId);
}

export async function listAdminVendors() {
  return listVendors();
}

export async function saveVendor(payload: Partial<Vendor> & { restaurantId: string }) {
  const vendor = await upsertVendor(payload);
  await trackEvent("vendor_upserted", {
    data: {
      restaurantId: payload.restaurantId,
      vendorId: vendor?.id || null,
    },
  });
  return vendor;
}

export async function getAdminLunchSummary() {
  return getLunchReportSummary();
}

export async function runProtectedJob(jobName: string) {
  switch (jobName) {
    case "expire-rooms": {
      const result = await query<{ id: string }>(
        `
          UPDATE rooms
          SET status = 'expired', updated_at = CURRENT_TIMESTAMP
          WHERE status IN ('open', 'ranking', 'voting')
            AND expires_at < CURRENT_TIMESTAMP
          RETURNING id
        `,
      );
      return { updatedRooms: result.rows.length };
    }
    case "recompute-vendor-metrics": {
      await query(
        `
          INSERT INTO vendor_metrics_daily (
            vendor_id,
            metric_date,
            orders_count,
            cancel_rate,
            avg_delivery_mins,
            complaint_rate,
            reliability_score
          )
          SELECT
            v.id,
            CURRENT_DATE,
            COUNT(mh.id),
            0,
            AVG(v.delivery_sla_mins),
            0,
            AVG(v.reliability_score)
          FROM vendors v
          LEFT JOIN meal_history mh ON mh.restaurant_id = v.restaurant_id
          GROUP BY v.id
          ON CONFLICT (vendor_id, metric_date) DO UPDATE SET
            orders_count = EXCLUDED.orders_count,
            avg_delivery_mins = EXCLUDED.avg_delivery_mins,
            reliability_score = EXCLUDED.reliability_score
        `,
      );
      return { ok: true };
    }
    case "aggregate-meal-history": {
      const count = await query<{ count: string }>("SELECT COUNT(*) AS count FROM meal_history");
      return { mealHistoryRecords: Number.parseInt(count.rows[0]?.count || "0", 10) };
    }
    case "precompute-profiles": {
      const users = await query<{ id: string }>("SELECT id FROM users");
      for (const user of users.rows) {
        await ensureUserProfile(user.id);
      }
      return { users: users.rows.length };
    }
    case "refresh-trending": {
      const popular = await query<{ restaurant_id: string | null; count: string }>(
        `
          SELECT restaurant_id, COUNT(*) AS count
          FROM meal_history
          GROUP BY restaurant_id
          ORDER BY count DESC
          LIMIT 10
        `,
      );
      return {
        topRestaurantIds: popular.rows.map((row) => row.restaurant_id).filter(Boolean),
      };
    }
    default:
      throw new AppError("Unknown job", 404, "not_found");
  }
}

export async function maybePromoteGuestForRoom(user: SessionUser, roomId: string) {
  const room = await getRoomDetail(roomId, appConfig.appUrl);
  if (!room) {
    return user;
  }

  if (room.hostUserId === user.id && user.role === "guest") {
    return updateUserAccount(user.id, { role: "room_host" });
  }

  return user;
}
