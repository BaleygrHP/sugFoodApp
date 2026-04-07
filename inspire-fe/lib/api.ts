import { MenuItem, Restaurant } from "@/app/page";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.error || "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type UserRole = "guest" | "user" | "room_host" | "admin" | "ops_admin";
export type RoomStatus = "open" | "ranking" | "voting" | "decided" | "expired";
export type RoomMode = "dine_in" | "delivery" | "mixed";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack";

export interface SessionResponse {
  user: {
    id: string;
    displayName: string;
    email: string | null;
    role: UserRole;
    accountStatus: string;
  };
  session: {
    expiresAt: string;
  };
}

export interface UserProfile {
  userId: string;
  preferredBudgetMin: number | null;
  preferredBudgetMax: number | null;
  noveltyPreference: "familiar" | "balanced" | "explore";
  diningModePreference: RoomMode;
  workLat: number | null;
  workLng: number | null;
  restrictions: string[];
  blockedRestaurantIds: string[];
  favoriteRestaurantIds: string[];
  favoriteDishIds: string[];
  cuisinePreferences: string[];
  dishStylePreferences: string[];
  preferenceVersion: number;
  updatedAt: string;
}

export interface RoomMember {
  userId: string;
  displayName: string;
  role: "host" | "member";
  participationStatus: "joined" | "submitted" | "voted" | "skipped";
  joinedAt: string;
}

export interface RoomDetail {
  id: string;
  hostUserId: string | null;
  name: string;
  mealType: MealType;
  mode: RoomMode;
  locationLabel: string | null;
  targetLat: number | null;
  targetLng: number | null;
  groupSizeExpected: number;
  budgetMin: number | null;
  budgetMax: number | null;
  status: RoomStatus;
  expiresAt: string;
  createdAt: string;
  updatedAt: string;
  inviteToken: string | null;
  inviteUrl: string | null;
  participantCount: number;
  members: RoomMember[];
  submissionCount: number;
  latestRecommendationRunId: string | null;
  menuItems: Array<{
    menuItemId: number;
    menuItemName: string;
    price: number;
    restaurant: {
      id: string;
      name: string;
      cuisine: string;
      priceRange: string;
      image: string;
      distance: string;
      rating: number;
    };
    votes: number;
  }>;
}

export interface RoomPreferenceSubmission {
  freeTextInput: string;
  selectedSuggestions: string[];
  hardConstraints: {
    vegetarian?: boolean;
    budgetCap?: number | null;
    blockedRestaurantIds?: string[];
    requireInvoice?: boolean;
  };
  rankedChoices: string[];
  prefillAccepted: boolean;
  pass: boolean;
}

export interface PrefillSuggestion {
  id: string;
  type: "dish" | "restaurant" | "cuisine";
  label: string;
  reason: string;
}

export interface RecommendationCandidate {
  candidateId: string;
  candidateType: "dish" | "restaurant" | "combined_option";
  candidateRefId: string | null;
  title: string;
  restaurantId: string | null;
  restaurantName: string | null;
  dishId: string | null;
  dishName: string | null;
  cuisine: string | null;
  mode: RoomMode | null;
  price: number | null;
  finalScore: number;
  confidence: number;
  selectedForVote: boolean;
  reasons: string[];
}

export interface RecommendationRunSummary {
  runId: string;
  roomId: string;
  algorithmVersion: string;
  configVersion: string;
  status: "success" | "fallback" | "failed";
  topOptions: RecommendationCandidate[];
  generatedAt: string;
  requestContext: Record<string, unknown>;
}

export interface VoteSummary {
  roomId: string;
  runId: string | null;
  totalVotes: number;
  votes: Array<{
    candidateId: string;
    title: string;
    count: number;
    weightedScore: number;
  }>;
  myVote: string | null;
  closed: boolean;
}

export interface FinalDecision {
  id: string;
  roomId: string;
  recommendationRunId: string;
  decisionType: "dine_in" | "delivery" | "split_group" | "fallback";
  confidenceScore: number;
  decidedAt: string;
  selectedOption: RecommendationCandidate | null;
}

export interface Vendor {
  id: string;
  restaurantId: string;
  restaurantName: string;
  sourceSystem: string | null;
  externalRef: string | null;
  accountManager: string | null;
  activeContract: boolean;
  approvalStatus: "pending" | "approved" | "suspended";
  invoiceSupported: boolean;
  supportsDelivery: boolean;
  supportsDineIn: boolean;
  reliabilityScore: number;
  deliverySlaMins: number | null;
  notes: string | null;
  importedPayload: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface LunchReportSummary {
  totalRooms: number;
  decidedRooms: number;
  averageDecisionMinutes: number;
  totalVotes: number;
  totalMealHistoryRecords: number;
  averageBudget: number;
  topVendors: Array<{
    vendorId: string;
    restaurantName: string;
    ordersCount: number;
    reliabilityScore: number;
  }>;
}

export interface CreateRoomInput {
  name?: string;
  mealType?: MealType;
  mode?: RoomMode;
  locationLabel?: string | null;
  targetLat?: number | null;
  targetLng?: number | null;
  groupSizeExpected?: number;
  budgetMin?: number | null;
  budgetMax?: number | null;
  expiresInMinutes?: number;
}

export async function ensureGuestSession(displayName?: string) {
  return request<SessionResponse>("/api/v1/auth/guest", {
    method: "POST",
    body: JSON.stringify(displayName ? { displayName } : {}),
  });
}

export async function loginWithEmail(email: string, displayName?: string) {
  return request<{ user: SessionResponse["user"] }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, displayName }),
  });
}

export async function fetchCurrentUser() {
  return request<{ user: SessionResponse["user"]; profile: UserProfile }>("/api/v1/users/me");
}

export async function updateCurrentProfile(payload: Partial<UserProfile> & { displayName?: string }) {
  return request<UserProfile>("/api/v1/users/me/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function blockRestaurant(restaurantId: string) {
  return request<UserProfile>(`/api/v1/users/me/blocks/restaurants/${restaurantId}`, {
    method: "POST",
  });
}

export async function unblockRestaurant(restaurantId: string) {
  return request<UserProfile>(`/api/v1/users/me/blocks/restaurants/${restaurantId}`, {
    method: "DELETE",
  });
}

export async function createRoom(input?: CreateRoomInput | string, _legacyParticipantId?: string) {
  await ensureGuestSession();
  const payload = typeof input === "string" ? { name: input } : input || {};
  return request<RoomDetail>("/api/v1/rooms", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchRoom(roomId: string, inviteToken?: string | null) {
  const suffix = inviteToken ? `?token=${encodeURIComponent(inviteToken)}` : "";
  return request<RoomDetail>(`/api/v1/rooms/${roomId}${suffix}`);
}

export async function joinRoom(roomId: string, inviteToken?: string | null) {
  return request<RoomDetail>(`/api/v1/rooms/${roomId}/join`, {
    method: "POST",
    body: JSON.stringify({ inviteToken }),
  });
}

export async function fetchPrefill(roomId: string) {
  return request<PrefillSuggestion[]>(`/api/v1/rooms/${roomId}/prefill`);
}

export async function submitRoomPreference(roomId: string, payload: RoomPreferenceSubmission) {
  return request<RoomPreferenceSubmission>(`/api/v1/rooms/${roomId}/preferences`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function closeRoomSubmissions(roomId: string) {
  return request<RecommendationRunSummary>(`/api/v1/rooms/${roomId}/close-submission`, {
    method: "POST",
  });
}

export async function runRecommendations(roomId: string) {
  return request<RecommendationRunSummary>(`/api/v1/rooms/${roomId}/recommendations/run`, {
    method: "POST",
  });
}

export async function fetchLatestRecommendations(roomId: string) {
  return request<RecommendationRunSummary | null>(`/api/v1/rooms/${roomId}/recommendations/latest`);
}

export async function voteForCandidate(roomId: string, candidateId: string, voteValue = 1) {
  return request<VoteSummary>(`/api/v1/rooms/${roomId}/votes`, {
    method: "POST",
    body: JSON.stringify({ candidateId, voteValue }),
  });
}

export async function fetchVoteSummary(roomId: string) {
  return request<VoteSummary>(`/api/v1/rooms/${roomId}/votes/summary`);
}

export async function closeVote(roomId: string) {
  return request<FinalDecision | null>(`/api/v1/rooms/${roomId}/votes/close`, {
    method: "POST",
  });
}

export async function fetchDecision(roomId: string) {
  return request<FinalDecision | null>(`/api/v1/rooms/${roomId}/decision`);
}

export async function listAdminVendors() {
  return request<Vendor[]>("/api/v1/admin/vendors");
}

export async function createOrUpdateVendor(payload: Partial<Vendor> & { restaurantId: string }) {
  return request<Vendor>("/api/v1/admin/vendors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchLunchSummary() {
  return request<LunchReportSummary>("/api/v1/admin/reports/lunch-summary");
}

export async function fetchRestaurants(): Promise<Restaurant[]> {
  return request<Restaurant[]>("/api/restaurants");
}

export async function fetchRestaurant(id: string): Promise<Restaurant> {
  return request<Restaurant>(`/api/restaurants/${id}`);
}

export async function fetchRestaurantMenu(id: string): Promise<(MenuItem & { id: number })[]> {
  return request<(MenuItem & { id: number })[]>(`/api/restaurants/${id}/menu`);
}

export async function fetchSpotlightRestaurant(): Promise<Restaurant> {
  return request<Restaurant>("/api/restaurants/spotlight");
}

// Legacy compatibility helpers.
export async function addParticipantToRoom(roomId: string, _participantId?: string, _name?: string) {
  return joinRoom(roomId);
}

export async function addRestaurantToRoom(_roomId?: string, _restaurantId?: string): Promise<void> {
  return;
}

export async function addMenuItemToRoom(_roomId?: string, _menuItemId?: number): Promise<void> {
  return;
}

export async function voteForMenuItem(roomId: string, menuItemId: number, _participantId?: string): Promise<{ voteCounts: { [key: number]: number } }> {
  const summary = await voteForCandidate(roomId, String(menuItemId), 1);
  return {
    voteCounts: summary.votes.reduce<{ [key: number]: number }>((acc, vote, index) => {
      acc[index] = vote.count;
      return acc;
    }, {}),
  };
}

export async function fetchRoomVotes(roomId: string): Promise<{ voteCounts: { [key: number]: number }; participantVotes: { [key: string]: number[] } }> {
  const summary = await fetchVoteSummary(roomId);
  return {
    voteCounts: summary.votes.reduce<{ [key: number]: number }>((acc, vote, index) => {
      acc[index] = vote.count;
      return acc;
    }, {}),
    participantVotes: {},
  };
}

export async function closeRoom(roomId: string, _participantId?: string): Promise<{ success: boolean; winner: number | null }> {
  const decision = await closeVote(roomId);
  return {
    success: Boolean(decision),
    winner: decision ? 1 : null,
  };
}

export async function uploadImage(file: File): Promise<string> {
  const url = `${API_BASE_URL}/api/upload`;
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to upload image");
  }

  const data = await response.json();
  return data.url;
}

export interface CreateRestaurantData {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  cuisine?: string;
  menuItems?: Array<{ name: string; price: number }>;
  image?: string;
}

export async function createRestaurant(data: CreateRestaurantData): Promise<Restaurant> {
  return request<Restaurant>("/api/restaurants", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
