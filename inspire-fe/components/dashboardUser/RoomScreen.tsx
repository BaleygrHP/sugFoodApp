"use client";

import { useState } from "react";
import { ArrowRight, Link2, MapPin, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { createRoom, ensureGuestSession, type MealType, type RoomMode } from "@/lib/api";

export default function RoomScreen() {
  const [name, setName] = useState("Team Lunch");
  const [mealType, setMealType] = useState<MealType>("lunch");
  const [mode, setMode] = useState<RoomMode>("delivery");
  const [locationLabel, setLocationLabel] = useState("Office Tan Binh");
  const [groupSizeExpected, setGroupSizeExpected] = useState(8);
  const [budgetMin, setBudgetMin] = useState<number | "">(40);
  const [budgetMax, setBudgetMax] = useState<number | "">(80);
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  const handleCreateRoom = async (event: React.FormEvent) => {
    event.preventDefault();

    try {
      setCreating(true);
      await ensureGuestSession();
      const room = await createRoom({
        name,
        mealType,
        mode,
        locationLabel,
        groupSizeExpected,
        budgetMin: budgetMin === "" ? null : Number(budgetMin),
        budgetMax: budgetMax === "" ? null : Number(budgetMax),
      });
      localStorage.setItem("current_room_id", room.id);
      router.push(`/voting/${room.id}`);
    } catch (error: any) {
      toast.error(error.message || "Failed to create room");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-green via-primary-green-dark to-primary-orange p-4 flex items-center justify-center">
      <div className="w-full max-w-3xl">
        <div className="text-center mb-8 text-white">
          <h1 className="mb-2">Create Smart Decision Room</h1>
          <p className="text-white/90">
            Invite your group, collect preferences, then let the ranker propose the best meal options.
          </p>
        </div>

        <div className="bg-white rounded-3xl shadow-2xl p-8">
          <form onSubmit={handleCreateRoom} className="space-y-6">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm mb-2 text-neutral-700">Room Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                />
              </div>

              <div>
                <label className="block text-sm mb-2 text-neutral-700">Meal Type</label>
                <select
                  value={mealType}
                  onChange={(event) => setMealType(event.target.value as MealType)}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snack">Snack</option>
                </select>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm mb-2 text-neutral-700">Mode</label>
                <select
                  value={mode}
                  onChange={(event) => setMode(event.target.value as RoomMode)}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                >
                  <option value="delivery">Delivery</option>
                  <option value="dine_in">Dine-in</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>

              <div>
                <label className="block text-sm mb-2 text-neutral-700">Target Location</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400" />
                  <input
                    type="text"
                    value={locationLabel}
                    onChange={(event) => setLocationLabel(event.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                  />
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm mb-2 text-neutral-700">Expected Group Size</label>
                <div className="relative">
                  <Users className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400" />
                  <input
                    type="number"
                    min={2}
                    max={30}
                    value={groupSizeExpected}
                    onChange={(event) => setGroupSizeExpected(Number(event.target.value))}
                    className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm mb-2 text-neutral-700">Budget Min (k VND)</label>
                <input
                  type="number"
                  min={0}
                  value={budgetMin}
                  onChange={(event) => setBudgetMin(event.target.value === "" ? "" : Number(event.target.value))}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                />
              </div>

              <div>
                <label className="block text-sm mb-2 text-neutral-700">Budget Max (k VND)</label>
                <input
                  type="number"
                  min={0}
                  value={budgetMax}
                  onChange={(event) => setBudgetMax(event.target.value === "" ? "" : Number(event.target.value))}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange"
                />
              </div>
            </div>

            <div className="bg-neutral-50 rounded-2xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Link2 className="w-5 h-5 text-primary-orange mt-0.5" />
                <div>
                  <h5 className="text-sm mb-1">Invite flow</h5>
                  <p className="text-sm text-neutral-600">
                    After creating the room, the screen will show a signed invite link and participant submission status.
                  </p>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={creating}
              className="w-full bg-gradient-to-r from-primary-orange to-primary-green text-white py-3 rounded-full hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Room & Collect Preferences"}
              <ArrowRight className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
