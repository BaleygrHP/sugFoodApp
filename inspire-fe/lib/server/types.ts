export type UserRole = "guest" | "user" | "room_host" | "admin" | "ops_admin";
export type RoomStatus = "open" | "ranking" | "voting" | "decided" | "expired";
export type ParticipationStatus = "joined" | "submitted" | "voted" | "skipped";
export type RoomMode = "dine_in" | "delivery" | "mixed";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack";
export type NoveltyPreference = "familiar" | "balanced" | "explore";
export type DiningModePreference = "dine_in" | "delivery" | "mixed";
export type CandidateType = "dish" | "restaurant" | "combined_option";
export type RecommendationRunStatus = "success" | "fallback" | "failed";
export type DecisionType = "dine_in" | "delivery" | "split_group" | "fallback";
export type VendorApprovalStatus = "pending" | "approved" | "suspended";

export interface SessionUser {
  id: string;
  role: UserRole;
  accountStatus: string;
  displayName: string;
  email: string | null;
}

export interface UserProfile {
  userId: string;
  preferredBudgetMin: number | null;
  preferredBudgetMax: number | null;
  noveltyPreference: NoveltyPreference;
  diningModePreference: DiningModePreference;
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
  participationStatus: ParticipationStatus;
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
  candidateType: CandidateType;
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
  breakdown?: Record<string, number>;
}

export interface RecommendationRunSummary {
  runId: string;
  roomId: string;
  algorithmVersion: string;
  configVersion: string;
  status: RecommendationRunStatus;
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
  decisionType: DecisionType;
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
  approvalStatus: VendorApprovalStatus;
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

export interface RankerContext {
  room: RoomDetail;
  members: Array<{
    user: SessionUser;
    profile: UserProfile;
    preference: RoomPreferenceSubmission | null;
    participationStatus: ParticipationStatus;
  }>;
  exploreModeEnabled: boolean;
  requestContext: Record<string, unknown>;
}
