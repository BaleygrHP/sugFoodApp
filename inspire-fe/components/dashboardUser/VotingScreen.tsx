"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Clock, Copy, Crown, Link2, Loader2, Sparkles, Users } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import {
  closeRoomSubmissions,
  closeVote,
  ensureGuestSession,
  fetchCurrentUser,
  fetchLatestRecommendations,
  fetchPrefill,
  fetchRoom,
  fetchVoteSummary,
  joinRoom,
  submitRoomPreference,
  type PrefillSuggestion,
  type RecommendationRunSummary,
  type RoomDetail,
  type RoomPreferenceSubmission,
  type SessionResponse,
  type VoteSummary,
  voteForCandidate,
} from "@/lib/api";

interface VotingScreenProps {
  roomId: string;
}

const initialPreference: RoomPreferenceSubmission = {
  freeTextInput: "",
  selectedSuggestions: [],
  hardConstraints: {
    vegetarian: false,
    budgetCap: null,
    requireInvoice: false,
  },
  rankedChoices: [],
  prefillAccepted: false,
  pass: false,
};

export default function VotingScreen({ roomId }: VotingScreenProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inviteToken = searchParams.get("token");

  const [currentUser, setCurrentUser] = useState<SessionResponse["user"] | null>(null);
  const [room, setRoom] = useState<RoomDetail | null>(null);
  const [prefill, setPrefill] = useState<PrefillSuggestion[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationRunSummary | null>(null);
  const [voteSummary, setVoteSummary] = useState<VoteSummary | null>(null);
  const [preference, setPreference] = useState<RoomPreferenceSubmission>(initialPreference);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [running, setRunning] = useState(false);
  const [closingVote, setClosingVote] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        await ensureGuestSession();
        const me = await fetchCurrentUser();
        setCurrentUser(me.user);

        const joinedRoom = inviteToken ? await joinRoom(roomId, inviteToken) : await fetchRoom(roomId);
        setRoom(joinedRoom);
        localStorage.setItem("current_room_id", roomId);

        const [prefillData, recommendationData] = await Promise.all([
          fetchPrefill(roomId).catch(() => []),
          fetchLatestRecommendations(roomId).catch(() => null),
        ]);

        setPrefill(prefillData);
        setRecommendation(recommendationData);

        if (joinedRoom.status === "voting" || joinedRoom.status === "decided") {
          const votes = await fetchVoteSummary(roomId).catch(() => null);
          setVoteSummary(votes);
        }

        if (joinedRoom.status === "decided" || joinedRoom.status === "expired") {
          localStorage.removeItem("current_room_id");
          router.push(`/rating/${roomId}`);
        }
      } catch (error: any) {
        toast.error(error.message || "Failed to load room");
        router.push("/room");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [inviteToken, roomId, router]);

  useEffect(() => {
    if (!room || (room.status !== "ranking" && room.status !== "voting")) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const latestRoom = await fetchRoom(roomId, inviteToken);
        setRoom(latestRoom);

        if (latestRoom.status === "voting") {
          const [latestRecommendation, latestVotes] = await Promise.all([
            fetchLatestRecommendations(roomId).catch(() => null),
            fetchVoteSummary(roomId).catch(() => null),
          ]);
          setRecommendation(latestRecommendation);
          setVoteSummary(latestVotes);
        }

        if (latestRoom.status === "decided" || latestRoom.status === "expired") {
          localStorage.removeItem("current_room_id");
          router.push(`/rating/${roomId}`);
        }
      } catch (error) {
        console.error(error);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [inviteToken, room, roomId, router]);

  const isHost = room && currentUser ? room.hostUserId === currentUser.id : false;
  const participantsProgress = useMemo(() => {
    if (!room) return "0/0";
    return `${room.submissionCount}/${room.participantCount}`;
  }, [room]);

  const handlePrefillToggle = (item: PrefillSuggestion) => {
    setPreference((prev) => {
      const set = new Set(prev.selectedSuggestions);
      if (set.has(item.label)) {
        set.delete(item.label);
      } else {
        set.add(item.label);
      }

      return {
        ...prev,
        selectedSuggestions: Array.from(set),
        prefillAccepted: Array.from(set).length > 0,
      };
    });
  };

  const handleSubmitPreference = async () => {
    try {
      setSubmitting(true);
      await submitRoomPreference(roomId, preference);
      const latestRoom = await fetchRoom(roomId, inviteToken);
      setRoom(latestRoom);
      toast.success("Preference submitted");
    } catch (error: any) {
      toast.error(error.message || "Failed to submit preference");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseSubmissions = async () => {
    try {
      setRunning(true);
      const summary = await closeRoomSubmissions(roomId);
      setRecommendation(summary);
      const latestRoom = await fetchRoom(roomId, inviteToken);
      setRoom(latestRoom);
      const latestVotes = await fetchVoteSummary(roomId).catch(() => null);
      setVoteSummary(latestVotes);
      toast.success("Recommendations generated");
    } catch (error: any) {
      toast.error(error.message || "Failed to generate recommendations");
    } finally {
      setRunning(false);
    }
  };

  const handleVote = async (candidateId: string) => {
    try {
      const summary = await voteForCandidate(roomId, candidateId, 1);
      setVoteSummary(summary);
    } catch (error: any) {
      toast.error(error.message || "Failed to submit vote");
    }
  };

  const handleFinalize = async () => {
    try {
      setClosingVote(true);
      await closeVote(roomId);
      localStorage.removeItem("current_room_id");
      router.push(`/rating/${roomId}`);
    } catch (error: any) {
      toast.error(error.message || "Failed to finalize decision");
    } finally {
      setClosingVote(false);
    }
  };

  const handleCopyInvite = async () => {
    if (!room?.inviteUrl) return;
    await navigator.clipboard.writeText(room.inviteUrl);
    toast.success("Invite link copied");
  };

  if (loading || !room) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <div className="flex items-center gap-3 text-neutral-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading room...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => router.push("/home")}
              className="p-2 hover:bg-neutral-100 rounded-full transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="text-center">
              <h4>{room.name}</h4>
              <p className="text-xs text-neutral-500">
                {room.mealType} • {room.mode} • {room.locationLabel || "No location"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-neutral-500">Status</p>
              <p className="text-sm capitalize">{room.status}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <section className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-primary-green" />
                <span className="text-sm text-neutral-600">
                  {room.participantCount} participants • submissions {participantsProgress}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-600">
                <Clock className="w-4 h-4 text-primary-orange" />
                <span>Expires {new Date(room.expiresAt).toLocaleString()}</span>
              </div>
            </div>
            <button
              onClick={handleCopyInvite}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-neutral-100 hover:bg-neutral-200 rounded-full text-sm"
            >
              <Copy className="w-4 h-4" />
              Copy Invite Link
            </button>
          </div>

          <div className="mt-4 grid md:grid-cols-3 gap-3">
            {room.members.map((member) => (
              <div key={member.userId} className="rounded-2xl border border-neutral-200 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm">{member.displayName}</p>
                    <p className="text-xs text-neutral-500 capitalize">{member.role}</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 capitalize">
                    {member.participationStatus}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {room.status === "open" && (
          <section className="grid lg:grid-cols-[1.3fr_0.9fr] gap-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
              <div>
                <h4 className="mb-1">Submit your preference</h4>
                <p className="text-sm text-neutral-600">
                  Enter free text, accept smart prefills, and add hard constraints before the host closes submissions.
                </p>
              </div>

              <textarea
                value={preference.freeTextInput}
                onChange={(event) => setPreference((prev) => ({ ...prev, freeTextInput: event.target.value }))}
                placeholder="Examples: pho, bun bo, healthy, spicy, under 70k"
                rows={4}
                className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
              />

              {prefill.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-primary-orange" />
                    <p className="text-sm">Smart Prefill</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {prefill.map((item) => {
                      const selected = preference.selectedSuggestions.includes(item.label);
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handlePrefillToggle(item)}
                          className={`px-3 py-2 rounded-full text-sm transition-colors ${
                            selected
                              ? "bg-primary-orange text-white"
                              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                          }`}
                        >
                          {item.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="grid md:grid-cols-3 gap-4">
                <label className="flex items-center justify-between rounded-2xl border border-neutral-200 px-4 py-3">
                  <span className="text-sm">Vegetarian only</span>
                  <input
                    type="checkbox"
                    checked={Boolean(preference.hardConstraints.vegetarian)}
                    onChange={(event) =>
                      setPreference((prev) => ({
                        ...prev,
                        hardConstraints: {
                          ...prev.hardConstraints,
                          vegetarian: event.target.checked,
                        },
                      }))
                    }
                  />
                </label>

                <label className="flex items-center justify-between rounded-2xl border border-neutral-200 px-4 py-3">
                  <span className="text-sm">Require invoice</span>
                  <input
                    type="checkbox"
                    checked={Boolean(preference.hardConstraints.requireInvoice)}
                    onChange={(event) =>
                      setPreference((prev) => ({
                        ...prev,
                        hardConstraints: {
                          ...prev.hardConstraints,
                          requireInvoice: event.target.checked,
                        },
                      }))
                    }
                  />
                </label>

                <div className="rounded-2xl border border-neutral-200 px-4 py-3">
                  <label className="text-sm block mb-2">Budget cap (k VND)</label>
                  <input
                    type="number"
                    min={0}
                    value={preference.hardConstraints.budgetCap ?? ""}
                    onChange={(event) =>
                      setPreference((prev) => ({
                        ...prev,
                        hardConstraints: {
                          ...prev.hardConstraints,
                          budgetCap: event.target.value === "" ? null : Number(event.target.value),
                        },
                      }))
                    }
                    className="w-full border border-neutral-200 rounded-xl px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleSubmitPreference}
                  disabled={submitting}
                  className="px-5 py-3 bg-gradient-to-r from-primary-orange to-primary-green text-white rounded-full disabled:opacity-50"
                >
                  {submitting ? "Submitting..." : "Submit Preference"}
                </button>
                <button
                  type="button"
                  onClick={() => setPreference((prev) => ({ ...prev, pass: !prev.pass }))}
                  className={`px-5 py-3 rounded-full border ${
                    preference.pass ? "border-primary-green text-primary-green" : "border-neutral-300 text-neutral-700"
                  }`}
                >
                  {preference.pass ? "Marked as pass" : "No strong preference"}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-primary-orange" />
                <h4>Host Actions</h4>
              </div>
              <p className="text-sm text-neutral-600">
                Once enough people have submitted, close submissions to trigger candidate generation and group ranking.
              </p>
              <button
                type="button"
                onClick={handleCloseSubmissions}
                disabled={!isHost || running}
                className="w-full px-4 py-3 rounded-full bg-gradient-to-r from-primary-orange to-primary-green text-white disabled:opacity-50"
              >
                {running ? "Generating..." : "Close Submissions & Run Ranking"}
              </button>
              {!isHost && (
                <p className="text-xs text-neutral-500">
                  Only the host can move the room into ranking/voting.
                </p>
              )}
            </div>
          </section>
        )}

        {room.status === "ranking" && (
          <section className="bg-white rounded-2xl p-8 shadow-sm text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary-orange" />
            <h4 className="mb-2">Ranking candidates...</h4>
            <p className="text-neutral-600">
              The engine is normalizing inputs, filtering vendors, and building the top options for voting.
            </p>
          </section>
        )}

        {room.status === "voting" && recommendation && (
          <section className="space-y-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <Crown className="w-5 h-5 text-primary-orange" />
                <h4>Top ranked options</h4>
              </div>
              <div className="space-y-4">
                {recommendation.topOptions.map((candidate) => {
                  const voteCount = voteSummary?.votes.find((vote) => vote.candidateId === candidate.candidateId)?.count || 0;
                  const isSelected = voteSummary?.myVote === candidate.candidateId;
                  return (
                    <div key={candidate.candidateId} className="border border-neutral-200 rounded-2xl p-4">
                      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                        <div>
                          <h5 className="mb-1">{candidate.title}</h5>
                          <p className="text-sm text-neutral-600 mb-3">
                            {candidate.cuisine} • score {(candidate.finalScore * 100).toFixed(0)} • confidence {(candidate.confidence * 100).toFixed(0)}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {candidate.reasons.map((reason) => (
                              <span key={reason} className="px-3 py-1 bg-neutral-100 rounded-full text-xs text-neutral-600">
                                {reason}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="md:text-right">
                          <p className="text-sm text-neutral-500 mb-2">{voteCount} votes</p>
                          <button
                            onClick={() => handleVote(candidate.candidateId)}
                            className={`px-4 py-2 rounded-full text-sm ${
                              isSelected
                                ? "bg-primary-green text-white"
                                : "bg-primary-orange text-white"
                            }`}
                          >
                            {isSelected ? "Voted" : "Vote for this"}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {isHost && (
              <div className="bg-white rounded-2xl p-6 shadow-sm">
                <button
                  onClick={handleFinalize}
                  disabled={closingVote}
                  className="w-full px-4 py-3 rounded-full bg-gradient-to-r from-primary-orange to-primary-green text-white disabled:opacity-50"
                >
                  {closingVote ? "Finalizing..." : "Close Voting & Finalize Decision"}
                </button>
              </div>
            )}
          </section>
        )}

        {voteSummary?.myVote && (
          <div className="fixed bottom-6 right-6 bg-white shadow-lg rounded-full px-4 py-3 flex items-center gap-2 border border-neutral-200">
            <CheckCircle2 className="w-4 h-4 text-primary-green" />
            <span className="text-sm">Your vote has been recorded</span>
          </div>
        )}
      </main>
    </div>
  );
}
